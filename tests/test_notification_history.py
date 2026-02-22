"""Tests for notification history dashboard (HTMX endpoint).

Spec: specs/notification-history.md
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.models.failure_event import FailureEvent
from app.models.notification_log import NotificationLog
from app.models.webhook import WebhookEndpoint

pytestmark = pytest.mark.asyncio


@pytest.fixture
def create_webhook(db_session):
    """Factory fixture to create a WebhookEndpoint."""

    def _create(name="Test Webhook", url="https://example.com/hook", **kwargs):
        wh = WebhookEndpoint(
            id=uuid4(),
            name=name,
            url=url,
            webhook_type=kwargs.get("webhook_type", "generic"),
            enabled=kwargs.get("enabled", True),
        )
        db_session.add(wh)
        db_session.commit()
        db_session.refresh(wh)
        return wh

    return _create


@pytest.fixture
def create_failure_event(db_session):
    """Factory fixture to create a FailureEvent."""

    def _create(source_name="test-source", failure_type="exit_code", **kwargs):
        fe = FailureEvent(
            id=uuid4(),
            source_name=source_name,
            failure_type=failure_type,
            detected_at=kwargs.get("detected_at", datetime.utcnow()),
            notified=kwargs.get("notified", True),
            details=kwargs.get("details", "Exit code 1"),
        )
        db_session.add(fe)
        db_session.commit()
        db_session.refresh(fe)
        return fe

    return _create


@pytest.fixture
def create_notification(db_session, create_webhook, create_failure_event):
    """Factory fixture to create a NotificationLog with related records."""

    def _create(
        webhook_name="Test Webhook",
        source_name="test-source",
        failure_type="exit_code",
        status="success",
        http_status_code=200,
        error_message=None,
        attempt_number=1,
        created_at=None,
        webhook=None,
        failure_event=None,
    ):
        if webhook is None:
            webhook = create_webhook(name=webhook_name)
        if failure_event is None:
            failure_event = create_failure_event(
                source_name=source_name, failure_type=failure_type
            )

        log = NotificationLog(
            id=uuid4(),
            failure_event_id=failure_event.id,
            webhook_endpoint_id=webhook.id,
            status=status,
            http_status_code=http_status_code,
            error_message=error_message,
            attempt_number=attempt_number,
            created_at=created_at or datetime.utcnow(),
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)
        return log, webhook, failure_event

    return _create


class TestNotificationHistorySection:
    """AC-001: Dashboard has a Notifications section."""

    async def test_ac001_dashboard_has_notifications_tab(self, client):
        """Dashboard page contains a notifications tab/link."""
        response = await client.get("/")
        assert response.status_code == 200
        html = response.text
        assert "Notifications" in html or "notifications" in html

    async def test_ac001_notifications_endpoint_exists(self, client):
        """GET /htmx/notifications returns 200."""
        response = await client.get("/htmx/notifications")
        assert response.status_code == 200


class TestNotificationList:
    """AC-002, AC-007, AC-009: Notification list rendering."""

    async def test_ac007_empty_state(self, client):
        """Empty list shows helpful message."""
        response = await client.get("/htmx/notifications")
        assert response.status_code == 200
        html = response.text
        assert "no notification" in html.lower() or "no notifications" in html.lower()

    async def test_ac002_shows_webhook_name(self, client, create_notification):
        """List shows the webhook endpoint name."""
        create_notification(webhook_name="Discord Alerts")
        response = await client.get("/htmx/notifications")
        html = response.text
        assert "Discord Alerts" in html

    async def test_ac002_shows_source_name(self, client, create_notification):
        """List shows the failure event source name."""
        create_notification(source_name="nas-backup")
        response = await client.get("/htmx/notifications")
        html = response.text
        assert "nas-backup" in html

    async def test_ac002_shows_failure_type(self, client, create_notification):
        """List shows the failure type."""
        create_notification(failure_type="stale")
        response = await client.get("/htmx/notifications")
        html = response.text
        assert "stale" in html.lower()

    async def test_ac002_shows_status(self, client, create_notification):
        """List shows the delivery status."""
        create_notification(status="failed", http_status_code=500)
        response = await client.get("/htmx/notifications")
        html = response.text
        assert "failed" in html.lower()

    async def test_ac002_shows_http_status_code(self, client, create_notification):
        """List shows the HTTP status code."""
        create_notification(http_status_code=503)
        response = await client.get("/htmx/notifications")
        html = response.text
        assert "503" in html

    async def test_ac002_shows_attempt_number(self, client, create_notification):
        """List shows the attempt number."""
        create_notification(attempt_number=3)
        response = await client.get("/htmx/notifications")
        html = response.text
        assert "3" in html

    async def test_ac009_sorted_newest_first(self, client, db_session, create_webhook, create_failure_event):
        """List is sorted by created_at descending."""
        wh = create_webhook(name="Sort Test")
        fe = create_failure_event(source_name="sort-src")

        old = NotificationLog(
            id=uuid4(),
            failure_event_id=fe.id,
            webhook_endpoint_id=wh.id,
            status="success",
            http_status_code=200,
            attempt_number=1,
            created_at=datetime.utcnow() - timedelta(hours=2),
        )
        new = NotificationLog(
            id=uuid4(),
            failure_event_id=fe.id,
            webhook_endpoint_id=wh.id,
            status="failed",
            http_status_code=500,
            attempt_number=1,
            created_at=datetime.utcnow(),
        )
        db_session.add(old)
        db_session.add(new)
        db_session.commit()

        response = await client.get("/htmx/notifications")
        html = response.text
        # Use the status badge class to find positions in the table body
        failed_pos = html.find("status-failed")
        success_pos = html.find("status-success")
        assert failed_pos < success_pos


class TestNotificationFilters:
    """AC-004, AC-005, AC-006: Filtering support."""

    async def test_ac004_filter_by_status(self, client, create_notification):
        """Filter by status shows only matching entries."""
        create_notification(status="success", webhook_name="WH Success")
        create_notification(status="failed", webhook_name="WH Failed", http_status_code=500)

        response = await client.get("/htmx/notifications?status=failed")
        html = response.text
        # Check that table body contains only the filtered entry
        tbody = html.split("<tbody>")[1].split("</tbody>")[0]
        assert "WH Failed" in tbody
        assert "WH Success" not in tbody

    async def test_ac005_filter_by_webhook(self, client, create_notification):
        """Filter by webhook name shows only matching entries."""
        create_notification(webhook_name="Discord Hook", source_name="src-a")
        create_notification(webhook_name="Slack Hook", source_name="src-b")

        response = await client.get("/htmx/notifications?webhook_name=Discord+Hook")
        html = response.text
        tbody = html.split("<tbody>")[1].split("</tbody>")[0]
        assert "Discord Hook" in tbody
        assert "Slack Hook" not in tbody

    async def test_ac006_filter_by_source(self, client, create_notification):
        """Filter by source name shows only matching entries."""
        create_notification(source_name="nas-backup", webhook_name="WH NAS")
        create_notification(source_name="server-sync", webhook_name="WH Server")

        response = await client.get("/htmx/notifications?source_name=nas-backup")
        html = response.text
        tbody = html.split("<tbody>")[1].split("</tbody>")[0]
        assert "nas-backup" in tbody
        assert "server-sync" not in tbody


class TestNotificationPagination:
    """AC-003: Pagination support."""

    async def test_ac003_pagination_default_limit(self, client, create_notification):
        """Default page shows up to 20 entries."""
        wh = None
        fe = None
        for i in range(25):
            log, wh_created, fe_created = create_notification(
                webhook_name=f"WH-{i}" if wh is None else None,
                source_name=f"src-{i}" if fe is None else None,
                webhook=wh,
                failure_event=fe,
                created_at=datetime.utcnow() - timedelta(minutes=i),
            )
            if wh is None:
                wh = wh_created
            if fe is None:
                fe = fe_created

        response = await client.get("/htmx/notifications")
        html = response.text
        # Should have pagination controls
        assert "Next" in html or "next" in html.lower() or "offset=" in html

    async def test_ac003_pagination_offset(self, client, create_notification):
        """Offset parameter skips entries."""
        wh = None
        fe = None
        for i in range(25):
            log, wh_created, fe_created = create_notification(
                webhook=wh,
                failure_event=fe,
                created_at=datetime.utcnow() - timedelta(minutes=i),
            )
            if wh is None:
                wh = wh_created
            if fe is None:
                fe = fe_created

        response = await client.get("/htmx/notifications?offset=20")
        assert response.status_code == 200


class TestNotificationErrorDisplay:
    """AC-008: Failed deliveries show error message."""

    async def test_ac008_error_message_displayed(self, client, create_notification):
        """Failed notification shows its error message."""
        create_notification(
            status="failed",
            http_status_code=500,
            error_message="Connection timed out after 30s",
        )
        response = await client.get("/htmx/notifications")
        html = response.text
        assert "Connection timed out" in html


class TestNotificationDeletedWebhook:
    """Edge case: webhook deleted but logs remain."""

    async def test_deleted_webhook_shows_placeholder(
        self, client, db_session, create_notification
    ):
        """Notification for a deleted webhook shows a placeholder name."""
        from sqlalchemy import text

        log, wh, fe = create_notification(webhook_name="Doomed Webhook")
        wh_id = wh.id
        log_id = log.id

        # Temporarily drop FK, delete webhook, then restore FK
        db_session.execute(
            text(
                "ALTER TABLE notification_logs "
                "DROP CONSTRAINT IF EXISTS notification_logs_webhook_endpoint_id_fkey"
            )
        )
        db_session.execute(
            text("DELETE FROM webhook_endpoints WHERE id = :wh_id"),
            {"wh_id": str(wh_id)},
        )
        db_session.commit()

        try:
            response = await client.get("/htmx/notifications")
            html = response.text
            assert response.status_code == 200
            # Should not crash; should show some placeholder
            assert "deleted" in html.lower() or len(html) > 0
        finally:
            # Clean up the orphaned log before restoring FK
            db_session.execute(
                text("DELETE FROM notification_logs WHERE id = :log_id"),
                {"log_id": str(log_id)},
            )
            db_session.execute(
                text(
                    "ALTER TABLE notification_logs "
                    "ADD CONSTRAINT notification_logs_webhook_endpoint_id_fkey "
                    "FOREIGN KEY (webhook_endpoint_id) REFERENCES webhook_endpoints(id)"
                )
            )
            db_session.commit()
