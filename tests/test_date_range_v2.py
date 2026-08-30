"""Tests for Date Range Quick Select v0.2.0 — Analytics + Notifications tabs.

Spec: specs/date-range-quick-select.md (AC-011 through AC-020)
"""

from datetime import timedelta
from uuid import uuid4

import pytest

from app.models.failure_event import FailureEvent
from app.models.notification_log import NotificationLog
from app.models.webhook import WebhookEndpoint
from app.utils import utc_now


# --- Fixtures ---


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
def create_notification(db_session, create_webhook):
    """Factory fixture to create a NotificationLog with related records."""

    def _create(
        source_name="test-source",
        status="success",
        created_at=None,
        webhook=None,
    ):
        if webhook is None:
            webhook = create_webhook(name=f"WH-{uuid4().hex[:6]}")
        fe = FailureEvent(
            id=uuid4(),
            source_name=source_name,
            failure_type="exit_code",
            detected_at=created_at or utc_now(),
            notified=True,
            details="Exit code 1",
        )
        db_session.add(fe)
        db_session.commit()
        db_session.refresh(fe)

        log = NotificationLog(
            id=uuid4(),
            failure_event_id=fe.id,
            webhook_endpoint_id=webhook.id,
            status=status,
            http_status_code=200 if status == "success" else 500,
            attempt_number=1,
            created_at=created_at or utc_now(),
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)
        return log, webhook, fe

    return _create


# === Analytics Tab Tests (AC-011 through AC-014) ===


class TestNotificationsQuickSelect:
    """AC-015: Notifications tab displays quick-select buttons."""

    async def test_ac015_notifications_has_quick_select_buttons(self, client):
        """AC-015: Notifications partial contains quick-select buttons."""
        response = await client.get("/htmx/notifications")
        assert response.status_code == 200
        html = response.text
        assert "quick-select" in html
        assert "Last 7 Days" in html
        assert "Last 30 Days" in html
        assert "Max" in html
        assert "Custom" in html

    async def test_ac020_notifications_uses_correct_css_classes(self, client):
        """AC-020: Notifications quick-select uses .quick-select-btn class."""
        response = await client.get("/htmx/notifications")
        html = response.text
        assert "quick-select-btn" in html


class TestNotificationsDateFiltering:
    """AC-016: Notifications endpoint accepts date_from and date_to."""

    @staticmethod
    def _table_body(html: str) -> str:
        """Extract the table body from the HTML response for assertion checks.

        Source names appear in the filter dropdowns too, so we need to check
        only the table body to verify date filtering works correctly.
        """
        start = html.find("<tbody>")
        end = html.find("</tbody>")
        if start == -1 or end == -1:
            return html
        return html[start : end + len("</tbody>")]

    async def test_ac016_filter_by_date_from(self, client, create_notification):
        """AC-016: date_from filters out older notifications."""
        now = utc_now()
        wh = None

        # Create a recent notification (3 days ago)
        log_recent, wh, _ = create_notification(
            source_name="recent-src",
            created_at=now - timedelta(days=3),
        )

        # Create an old notification (14 days ago)
        log_old, _, _ = create_notification(
            source_name="old-src",
            created_at=now - timedelta(days=14),
            webhook=wh,
        )

        date_from = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        response = await client.get(f"/htmx/notifications?date_from={date_from}")
        assert response.status_code == 200
        tbody = self._table_body(response.text)
        assert "recent-src" in tbody
        assert "old-src" not in tbody

    async def test_ac016_filter_by_date_to(self, client, create_notification):
        """AC-016: date_to filters out newer notifications."""
        now = utc_now()
        wh = None

        # Create a recent notification (1 day ago)
        log_recent, wh, _ = create_notification(
            source_name="new-src",
            created_at=now - timedelta(days=1),
        )

        # Create an older notification (10 days ago)
        log_old, _, _ = create_notification(
            source_name="older-src",
            created_at=now - timedelta(days=10),
            webhook=wh,
        )

        date_to = (now - timedelta(days=5)).strftime("%Y-%m-%d")
        response = await client.get(f"/htmx/notifications?date_to={date_to}")
        assert response.status_code == 200
        tbody = self._table_body(response.text)
        assert "older-src" in tbody
        assert "new-src" not in tbody

    async def test_ac016_filter_by_date_range(self, client, create_notification):
        """AC-016: date_from + date_to together scope the results."""
        now = utc_now()
        wh = None

        # Create notification in the target range (10 days ago)
        log_mid, wh, _ = create_notification(
            source_name="mid-src",
            created_at=now - timedelta(days=10),
        )

        # Create notification too old (25 days ago)
        log_old, _, _ = create_notification(
            source_name="ancient-src",
            created_at=now - timedelta(days=25),
            webhook=wh,
        )

        # Create notification too new (1 day ago)
        log_new, _, _ = create_notification(
            source_name="fresh-src",
            created_at=now - timedelta(days=1),
            webhook=wh,
        )

        date_from = (now - timedelta(days=15)).strftime("%Y-%m-%d")
        date_to = (now - timedelta(days=5)).strftime("%Y-%m-%d")
        response = await client.get(
            f"/htmx/notifications?date_from={date_from}&date_to={date_to}"
        )
        assert response.status_code == 200
        tbody = self._table_body(response.text)
        assert "mid-src" in tbody
        assert "ancient-src" not in tbody
        assert "fresh-src" not in tbody

    async def test_ac016_combined_with_status_filter(self, client, create_notification):
        """AC-016: Date range combined with status filter (AND logic)."""
        now = utc_now()
        wh = None

        # Recent success
        _, wh, _ = create_notification(
            source_name="ok-src",
            status="success",
            created_at=now - timedelta(days=3),
        )

        # Recent failure
        create_notification(
            source_name="fail-src",
            status="failed",
            created_at=now - timedelta(days=3),
            webhook=wh,
        )

        date_from = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        response = await client.get(
            f"/htmx/notifications?date_from={date_from}&status=failed"
        )
        assert response.status_code == 200
        tbody = self._table_body(response.text)
        assert "fail-src" in tbody
        assert "ok-src" not in tbody

    async def test_ac016_invalid_date_ignored(self, client):
        """AC-016 edge case: Invalid date format is ignored gracefully."""
        response = await client.get("/htmx/notifications?date_from=not-a-date")
        assert response.status_code == 200


class TestNotificationsDatePagination:
    """AC-019: Date range persists through pagination."""

    async def test_ac019_pagination_includes_date_params(
        self, client, create_notification
    ):
        """AC-019: Prev/next pagination links include date_from and date_to."""
        now = utc_now()
        wh = None

        # Create 25 notifications within range
        for i in range(25):
            if wh is None:
                _, wh, _ = create_notification(
                    source_name="paginate-src",
                    created_at=now - timedelta(hours=i),
                )
            else:
                create_notification(
                    source_name="paginate-src",
                    created_at=now - timedelta(hours=i),
                    webhook=wh,
                )

        date_from = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        response = await client.get(
            f"/htmx/notifications?date_from={date_from}&limit=20"
        )
        assert response.status_code == 200
        html = response.text
        # The "Next" pagination link should include date_from
        assert f"date_from={date_from}" in html


class TestAC011BackwardCursorProbe:
    """AC-011: backward `has_next` uses the same filters as the page query."""

    @pytest.mark.asyncio
    async def test_ac011_backward_has_next_respects_start_date(
        self, client, create_sync_log
    ):
        base = utc_now() - timedelta(days=3)
        for i in range(6):  # day-1 rows: outside the window, older than it
            create_sync_log(
                source_name="probe-src",
                start_time=base + timedelta(minutes=i),
                end_time=base + timedelta(minutes=i + 1),
            )
        day2 = [
            create_sync_log(
                source_name="probe-src",
                start_time=base + timedelta(days=1, minutes=i),
                end_time=base + timedelta(days=1, minutes=i + 1),
            )
            for i in range(6)
        ]
        start = (base + timedelta(days=1)).isoformat()

        # Backward from the window start shows the oldest in-window rows.
        response = await client.get(
            "/api/v1/sync-logs?limit=3&direction=backward"
            f"&start_date={start}&source_name=probe-src"
        )
        assert response.status_code == 200
        body = response.json()
        assert [i["id"] for i in body["items"]] == [
            str(log.id) for log in (day2[2], day2[1], day2[0])
        ]
        # Six day-1 rows are older than this page but filtered out — the
        # probe must respect start_date and report nothing further.
        assert body["pagination"]["has_next"] is False

    @pytest.mark.asyncio
    async def test_ac011_backward_has_next_respects_synthetic_filter(
        self, client, create_sync_log
    ):
        from app.services.synthetic_check import SYNTHETIC_SOURCE_NAME

        base = utc_now() - timedelta(hours=10)
        for i in range(4):
            create_sync_log(
                source_name=SYNTHETIC_SOURCE_NAME,
                start_time=base + timedelta(minutes=i),
                end_time=base + timedelta(minutes=i + 1),
            )
        for i in range(4):
            create_sync_log(
                source_name="probe-real",
                start_time=base + timedelta(hours=1, minutes=i),
                end_time=base + timedelta(hours=1, minutes=i + 1),
            )

        response = await client.get(
            "/api/v1/sync-logs?limit=2&direction=backward&synthetic=hide"
        )
        body = response.json()
        assert len(body["items"]) == 2
        assert all(i["source_name"] == "probe-real" for i in body["items"])
        # Only synthetic rows are older; hidden, so has_next must be False.
        assert body["pagination"]["has_next"] is False
