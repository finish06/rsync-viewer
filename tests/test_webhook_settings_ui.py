"""Tests for webhook settings UI (HTMX endpoints).

Spec: specs/webhook-service.md — AC-007
"""

import pytest
from uuid import uuid4

from app.models.webhook import WebhookEndpoint
from app.models.webhook_options import WebhookOptions

pytestmark = pytest.mark.asyncio


@pytest.fixture
def create_webhook(db_session):
    """Factory fixture to create a WebhookEndpoint in the database."""

    def _create(
        name="Test Webhook",
        url="https://example.com/hook",
        webhook_type="generic",
        enabled=True,
        consecutive_failures=0,
        source_filters=None,
    ) -> WebhookEndpoint:
        wh = WebhookEndpoint(
            id=uuid4(),
            name=name,
            url=url,
            webhook_type=webhook_type,
            enabled=enabled,
            consecutive_failures=consecutive_failures,
            source_filters=source_filters,
        )
        db_session.add(wh)
        db_session.commit()
        db_session.refresh(wh)
        return wh

    return _create


class TestWebhookSettingsSection:
    """AC-007: Settings page has a webhook management section."""

    async def test_ac007_settings_page_has_webhooks_section(self, client):
        """Settings page contains the webhooks management area."""
        response = await client.get("/settings")
        assert response.status_code == 200
        html = response.text
        assert "Webhooks" in html
        assert "Add Webhook" in html
        assert "webhooks-list" in html

    async def test_ac007_settings_page_has_modal_container(self, client):
        """Settings page has a modal container for webhook forms."""
        response = await client.get("/settings")
        html = response.text
        assert "modal-container" in html


class TestWebhookList:
    """AC-007: Webhook list loads via HTMX."""

    async def test_ac007_empty_webhook_list(self, client):
        """Empty list shows a helpful message."""
        response = await client.get("/htmx/webhooks")
        assert response.status_code == 200
        html = response.text
        assert "No webhooks" in html or "no webhook" in html.lower()

    async def test_ac007_webhook_list_shows_entries(self, client, create_webhook):
        """Webhook list displays configured webhooks."""
        wh = create_webhook(name="Discord Alert", url="https://discord.com/api/webhooks/123/abc")
        response = await client.get("/htmx/webhooks")
        assert response.status_code == 200
        html = response.text
        assert "Discord Alert" in html
        assert "discord.com" in html

    async def test_ac007_webhook_list_shows_type_badge(self, client, create_webhook):
        """Webhook list shows type badge (generic/discord)."""
        create_webhook(name="My Discord", webhook_type="discord")
        response = await client.get("/htmx/webhooks")
        html = response.text
        assert "discord" in html.lower()

    async def test_ac007_webhook_list_shows_failure_count(self, client, create_webhook):
        """Webhook list shows consecutive failure count."""
        create_webhook(name="Failing Hook", consecutive_failures=5)
        response = await client.get("/htmx/webhooks")
        html = response.text
        assert "5" in html

    async def test_ac007_webhook_list_shows_enabled_toggle(self, client, create_webhook):
        """Webhook list has enable/disable toggle for each webhook."""
        create_webhook(name="Toggle Test")
        response = await client.get("/htmx/webhooks")
        html = response.text
        assert "toggle" in html.lower()


class TestWebhookAddForm:
    """AC-007: Add webhook form works."""

    async def test_ac007_add_form_returns_modal(self, client):
        """GET /htmx/webhooks/add returns the add form."""
        response = await client.get("/htmx/webhooks/add")
        assert response.status_code == 200
        html = response.text
        assert "Name" in html or "name" in html
        assert "URL" in html or "url" in html

    async def test_ac007_add_form_has_type_selector(self, client):
        """Add form has webhook type dropdown."""
        response = await client.get("/htmx/webhooks/add")
        html = response.text
        assert "generic" in html
        assert "discord" in html


class TestWebhookCreate:
    """AC-007: Creating a webhook via HTMX."""

    async def test_ac007_create_webhook_success(self, client, db_session):
        """POST /htmx/webhooks creates a webhook and returns the updated list."""
        response = await client.post(
            "/htmx/webhooks",
            data={
                "name": "New Hook",
                "url": "https://example.com/hook",
                "webhook_type": "generic",
                "source_filters": "",
                "headers": "",
                "enabled": "on",
            },
        )
        assert response.status_code == 200
        html = response.text
        assert "New Hook" in html
        # Should trigger modal close
        assert response.headers.get("HX-Trigger") == "closeModal"

    async def test_ac007_create_webhook_validation_error(self, client):
        """POST /htmx/webhooks with missing name returns form with errors."""
        response = await client.post(
            "/htmx/webhooks",
            data={
                "name": "",
                "url": "https://example.com/hook",
                "webhook_type": "generic",
                "source_filters": "",
                "headers": "",
            },
        )
        assert response.status_code == 200
        html = response.text
        assert "required" in html.lower()

    async def test_ac007_create_discord_webhook_validates_url(self, client):
        """Discord webhooks require a Discord URL pattern."""
        response = await client.post(
            "/htmx/webhooks",
            data={
                "name": "Bad Discord",
                "url": "https://example.com/not-discord",
                "webhook_type": "discord",
                "source_filters": "",
                "headers": "",
                "enabled": "on",
            },
        )
        assert response.status_code == 200
        html = response.text
        assert "discord" in html.lower() and ("require" in html.lower() or "matching" in html.lower())

    async def test_ac007_create_discord_webhook_with_options(self, client, db_session):
        """Creating a Discord webhook saves Discord-specific options."""
        response = await client.post(
            "/htmx/webhooks",
            data={
                "name": "Discord Test",
                "url": "https://discord.com/api/webhooks/123/abc",
                "webhook_type": "discord",
                "source_filters": "",
                "headers": "",
                "enabled": "on",
                "discord_color": "#FF0045",
                "discord_username": "Bot Name",
                "discord_avatar_url": "",
                "discord_footer": "",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("HX-Trigger") == "closeModal"

        # Verify options were saved
        from sqlmodel import select
        wh = db_session.exec(
            select(WebhookEndpoint).where(WebhookEndpoint.name == "Discord Test")
        ).first()
        assert wh is not None

        opts = db_session.exec(
            select(WebhookOptions).where(WebhookOptions.webhook_endpoint_id == wh.id)
        ).first()
        assert opts is not None
        assert opts.options["username"] == "Bot Name"


class TestWebhookEdit:
    """AC-007: Editing a webhook via HTMX."""

    async def test_ac007_edit_form_prepopulated(self, client, create_webhook):
        """GET /htmx/webhooks/{id}/edit returns pre-filled form."""
        wh = create_webhook(name="Edit Me", url="https://example.com/old")
        response = await client.get(f"/htmx/webhooks/{wh.id}/edit")
        assert response.status_code == 200
        html = response.text
        assert "Edit Me" in html
        assert "https://example.com/old" in html

    async def test_ac007_edit_form_not_found(self, client):
        """GET /htmx/webhooks/{bad_id}/edit returns 404."""
        response = await client.get(f"/htmx/webhooks/{uuid4()}/edit")
        assert response.status_code == 404

    async def test_ac007_update_webhook_success(self, client, create_webhook, db_session):
        """PUT /htmx/webhooks/{id} updates the webhook."""
        wh = create_webhook(name="Old Name")
        response = await client.put(
            f"/htmx/webhooks/{wh.id}",
            data={
                "name": "New Name",
                "url": "https://example.com/updated",
                "webhook_type": "generic",
                "source_filters": "",
                "headers": "",
                "enabled": "on",
            },
        )
        assert response.status_code == 200
        html = response.text
        assert "New Name" in html
        assert response.headers.get("HX-Trigger") == "closeModal"


class TestWebhookDelete:
    """AC-007: Deleting a webhook via HTMX."""

    async def test_ac007_delete_webhook(self, client, create_webhook, db_session):
        """DELETE /htmx/webhooks/{id} removes the webhook."""
        wh = create_webhook(name="Delete Me")
        response = await client.delete(f"/htmx/webhooks/{wh.id}")
        assert response.status_code == 200
        html = response.text
        assert "Delete Me" not in html

    async def test_ac007_delete_webhook_not_found(self, client):
        """DELETE /htmx/webhooks/{bad_id} returns 404."""
        response = await client.delete(f"/htmx/webhooks/{uuid4()}")
        assert response.status_code == 404


class TestWebhookToggle:
    """AC-007: Enable/disable toggle via HTMX."""

    async def test_ac007_toggle_disables_webhook(self, client, create_webhook, db_session):
        """POST /htmx/webhooks/{id}/toggle disables an enabled webhook."""
        wh = create_webhook(name="Toggle Off", enabled=True)
        response = await client.post(f"/htmx/webhooks/{wh.id}/toggle")
        assert response.status_code == 200

        db_session.refresh(wh)
        assert wh.enabled is False

    async def test_ac007_toggle_enables_webhook(self, client, create_webhook, db_session):
        """POST /htmx/webhooks/{id}/toggle enables a disabled webhook."""
        wh = create_webhook(name="Toggle On", enabled=False)
        response = await client.post(f"/htmx/webhooks/{wh.id}/toggle")
        assert response.status_code == 200

        db_session.refresh(wh)
        assert wh.enabled is True


class TestWebhookTest:
    """AC-007: Test webhook button sends a test notification."""

    async def test_ac007_test_webhook_returns_result(self, client, create_webhook):
        """POST /htmx/webhooks/{id}/test returns an inline result."""
        wh = create_webhook(name="Test Hook", url="https://httpbin.org/post")
        response = await client.post(f"/htmx/webhooks/{wh.id}/test")
        assert response.status_code == 200
        # Should return some result HTML (success or failure)
        html = response.text
        assert len(html) > 0
