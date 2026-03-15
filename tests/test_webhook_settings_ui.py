"""Tests for webhook settings UI (HTMX endpoints).

Spec: specs/webhook-service.md — AC-007
"""

import os
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from uuid import uuid4

from app.config import get_settings
from app.csrf import generate_csrf_token
from app.database import get_session
from app.main import app
from app.models.webhook import WebhookEndpoint
from app.models.webhook_options import WebhookOptions
from tests.conftest import _make_test_jwt, _TEST_SECRET, get_test_settings


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
        create_webhook(
            name="Discord Alert", url="https://discord.com/api/webhooks/123/abc"
        )
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

    async def test_ac007_webhook_list_shows_enabled_toggle(
        self, client, create_webhook
    ):
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
        assert "discord" in html.lower() and (
            "require" in html.lower() or "matching" in html.lower()
        )

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

    async def test_ac007_update_webhook_success(
        self, client, create_webhook, db_session
    ):
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

    async def test_ac007_toggle_disables_webhook(
        self, client, create_webhook, db_session
    ):
        """POST /htmx/webhooks/{id}/toggle disables an enabled webhook."""
        wh = create_webhook(name="Toggle Off", enabled=True)
        response = await client.post(f"/htmx/webhooks/{wh.id}/toggle")
        assert response.status_code == 200

        db_session.refresh(wh)
        assert wh.enabled is False

    async def test_ac007_toggle_enables_webhook(
        self, client, create_webhook, db_session
    ):
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


# ---- Viewer-level client fixture for authorization tests ----


@pytest.fixture(scope="function")
def viewer_client(test_engine, db_session):
    """Create an async test client authenticated as a viewer-level user."""
    from app.models.user import User
    from app.services.auth import hash_password, ROLE_VIEWER

    os.environ["SECRET_KEY"] = _TEST_SECRET
    os.environ["DEBUG"] = "true"
    os.environ["DEFAULT_API_KEY"] = "test-api-key"
    get_settings.cache_clear()

    viewer_user = User(
        username="viewer",
        email="viewer@test.local",
        password_hash=hash_password("P1!aaaa"),
        role=ROLE_VIEWER,
    )
    db_session.add(viewer_user)
    db_session.flush()

    def get_test_session():
        yield db_session

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_settings] = get_test_settings

    csrf_token = generate_csrf_token()
    jwt_token = _make_test_jwt(
        user_id=str(viewer_user.id),
        username=viewer_user.username,
        role=viewer_user.role,
    )

    yield AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-CSRF-Token": csrf_token},
        cookies={"csrf_token": csrf_token, "access_token": jwt_token},
    )

    app.dependency_overrides.clear()
    get_settings.cache_clear()


class TestWebhookAuthorizationViewer:
    """Viewer-level users cannot create/update/delete/toggle/test webhooks."""

    async def test_create_webhook_forbidden_for_viewer(self, viewer_client):
        """POST /htmx/webhooks returns 403 for viewer role."""
        response = await viewer_client.post(
            "/htmx/webhooks",
            data={
                "name": "Blocked",
                "url": "https://example.com/hook",
                "webhook_type": "generic",
                "source_filters": "",
                "headers": "",
                "enabled": "on",
            },
        )
        assert response.status_code == 403

    async def test_update_webhook_forbidden_for_viewer(
        self, viewer_client, create_webhook
    ):
        """PUT /htmx/webhooks/{id} returns 403 for viewer role."""
        wh = create_webhook(name="View Only")
        response = await viewer_client.put(
            f"/htmx/webhooks/{wh.id}",
            data={
                "name": "Hacked",
                "url": "https://example.com/hook",
                "webhook_type": "generic",
                "source_filters": "",
                "headers": "",
                "enabled": "on",
            },
        )
        assert response.status_code == 403

    async def test_delete_webhook_forbidden_for_viewer(
        self, viewer_client, create_webhook
    ):
        """DELETE /htmx/webhooks/{id} returns 403 for viewer role."""
        wh = create_webhook(name="Protected")
        response = await viewer_client.delete(f"/htmx/webhooks/{wh.id}")
        assert response.status_code == 403

    async def test_toggle_webhook_forbidden_for_viewer(
        self, viewer_client, create_webhook
    ):
        """POST /htmx/webhooks/{id}/toggle returns 403 for viewer role."""
        wh = create_webhook(name="Toggle Block")
        response = await viewer_client.post(f"/htmx/webhooks/{wh.id}/toggle")
        assert response.status_code == 403

    async def test_test_webhook_forbidden_for_viewer(
        self, viewer_client, create_webhook
    ):
        """POST /htmx/webhooks/{id}/test returns 403 for viewer role."""
        wh = create_webhook(name="Test Block")
        response = await viewer_client.post(f"/htmx/webhooks/{wh.id}/test")
        assert response.status_code == 403


class TestWebhookCreateValidation:
    """Validation edge cases during webhook creation."""

    async def test_create_missing_url(self, client):
        """POST /htmx/webhooks with missing URL returns form with error."""
        response = await client.post(
            "/htmx/webhooks",
            data={
                "name": "No URL",
                "url": "",
                "webhook_type": "generic",
                "source_filters": "",
                "headers": "",
                "enabled": "on",
            },
        )
        assert response.status_code == 200
        html = response.text
        assert "required" in html.lower()

    async def test_create_invalid_json_headers(self, client):
        """POST /htmx/webhooks with invalid JSON headers returns form with error."""
        response = await client.post(
            "/htmx/webhooks",
            data={
                "name": "Bad Headers",
                "url": "https://example.com/hook",
                "webhook_type": "generic",
                "source_filters": "",
                "headers": "{not valid json",
                "enabled": "on",
            },
        )
        assert response.status_code == 200
        html = response.text
        assert "json" in html.lower()

    async def test_create_discord_url_validation_with_url_present(self, client):
        """Discord webhook with non-discord URL triggers URL-specific error."""
        response = await client.post(
            "/htmx/webhooks",
            data={
                "name": "Bad Discord URL",
                "url": "https://not-discord.com/hook",
                "webhook_type": "discord",
                "source_filters": "",
                "headers": "",
                "enabled": "on",
            },
        )
        assert response.status_code == 200
        html = response.text
        assert "discord" in html.lower()


class TestWebhookCreateDiscordOptions:
    """Discord-specific options during creation."""

    async def test_create_discord_invalid_hex_color_defaults(self, client, db_session):
        """Invalid hex color falls back to default color integer."""
        from sqlmodel import select

        response = await client.post(
            "/htmx/webhooks",
            data={
                "name": "Bad Color",
                "url": "https://discord.com/api/webhooks/123/abc",
                "webhook_type": "discord",
                "source_filters": "",
                "headers": "",
                "enabled": "on",
                "discord_color": "not-a-hex",
                "discord_username": "Bot",
                "discord_avatar_url": "",
                "discord_footer": "",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("HX-Trigger") == "closeModal"

        wh = db_session.exec(
            select(WebhookEndpoint).where(WebhookEndpoint.name == "Bad Color")
        ).first()
        opts = db_session.exec(
            select(WebhookOptions).where(WebhookOptions.webhook_endpoint_id == wh.id)
        ).first()
        assert opts is not None
        # Default fallback: 16711749 == 0xFF0045
        assert opts.options["color"] == 16711749

    async def test_create_discord_with_avatar_url(self, client, db_session):
        """Discord webhook saves avatar_url option when provided."""
        from sqlmodel import select

        response = await client.post(
            "/htmx/webhooks",
            data={
                "name": "Avatar Hook",
                "url": "https://discord.com/api/webhooks/456/def",
                "webhook_type": "discord",
                "source_filters": "",
                "headers": "",
                "enabled": "on",
                "discord_color": "#00FF00",
                "discord_username": "Bot",
                "discord_avatar_url": "https://example.com/avatar.png",
                "discord_footer": "",
            },
        )
        assert response.status_code == 200

        wh = db_session.exec(
            select(WebhookEndpoint).where(WebhookEndpoint.name == "Avatar Hook")
        ).first()
        opts = db_session.exec(
            select(WebhookOptions).where(WebhookOptions.webhook_endpoint_id == wh.id)
        ).first()
        assert opts.options["avatar_url"] == "https://example.com/avatar.png"

    async def test_create_discord_with_footer(self, client, db_session):
        """Discord webhook saves footer option when provided."""
        from sqlmodel import select

        response = await client.post(
            "/htmx/webhooks",
            data={
                "name": "Footer Hook",
                "url": "https://discord.com/api/webhooks/789/ghi",
                "webhook_type": "discord",
                "source_filters": "",
                "headers": "",
                "enabled": "on",
                "discord_color": "#0000FF",
                "discord_username": "Bot",
                "discord_avatar_url": "",
                "discord_footer": "Powered by Rsync Viewer",
            },
        )
        assert response.status_code == 200

        wh = db_session.exec(
            select(WebhookEndpoint).where(WebhookEndpoint.name == "Footer Hook")
        ).first()
        opts = db_session.exec(
            select(WebhookOptions).where(WebhookOptions.webhook_endpoint_id == wh.id)
        ).first()
        assert opts.options["footer"] == "Powered by Rsync Viewer"


class TestWebhookUpdateNotFound:
    """Update to non-existent webhook."""

    async def test_update_webhook_not_found(self, client):
        """PUT /htmx/webhooks/{bad_id} returns 404."""
        response = await client.put(
            f"/htmx/webhooks/{uuid4()}",
            data={
                "name": "Ghost",
                "url": "https://example.com/hook",
                "webhook_type": "generic",
                "source_filters": "",
                "headers": "",
                "enabled": "on",
            },
        )
        assert response.status_code == 404


class TestWebhookUpdateValidation:
    """Validation edge cases during webhook update."""

    async def test_update_missing_name(self, client, create_webhook):
        """PUT with missing name returns form with error."""
        wh = create_webhook(name="Has Name")
        response = await client.put(
            f"/htmx/webhooks/{wh.id}",
            data={
                "name": "",
                "url": "https://example.com/hook",
                "webhook_type": "generic",
                "source_filters": "",
                "headers": "",
                "enabled": "on",
            },
        )
        assert response.status_code == 200
        html = response.text
        assert "required" in html.lower()

    async def test_update_missing_url(self, client, create_webhook):
        """PUT with missing URL returns form with error."""
        wh = create_webhook(name="Has URL")
        response = await client.put(
            f"/htmx/webhooks/{wh.id}",
            data={
                "name": "Has URL",
                "url": "",
                "webhook_type": "generic",
                "source_filters": "",
                "headers": "",
                "enabled": "on",
            },
        )
        assert response.status_code == 200
        html = response.text
        assert "required" in html.lower()

    async def test_update_discord_url_validation(self, client, create_webhook):
        """PUT with discord type and non-discord URL returns error."""
        wh = create_webhook(name="Discord Update")
        response = await client.put(
            f"/htmx/webhooks/{wh.id}",
            data={
                "name": "Discord Update",
                "url": "https://not-discord.com/hook",
                "webhook_type": "discord",
                "source_filters": "",
                "headers": "",
                "enabled": "on",
            },
        )
        assert response.status_code == 200
        html = response.text
        assert "discord" in html.lower()

    async def test_update_invalid_json_headers(self, client, create_webhook):
        """PUT with invalid JSON headers returns form with error."""
        wh = create_webhook(name="Bad Headers Update")
        response = await client.put(
            f"/htmx/webhooks/{wh.id}",
            data={
                "name": "Bad Headers Update",
                "url": "https://example.com/hook",
                "webhook_type": "generic",
                "source_filters": "",
                "headers": "{{invalid json",
                "enabled": "on",
            },
        )
        assert response.status_code == 200
        html = response.text
        assert "json" in html.lower()

    async def test_update_validation_rerenders_form_with_options(
        self, client, create_webhook, db_session
    ):
        """Validation error on update re-renders the form with existing options."""
        wh = create_webhook(
            name="Discord With Opts",
            url="https://discord.com/api/webhooks/111/aaa",
            webhook_type="discord",
        )
        # Add options row
        opts = WebhookOptions(
            webhook_endpoint_id=wh.id,
            options={"color": 255, "username": "TestBot"},
        )
        db_session.add(opts)
        db_session.commit()

        # Submit with empty name to trigger validation error
        response = await client.put(
            f"/htmx/webhooks/{wh.id}",
            data={
                "name": "",
                "url": "https://discord.com/api/webhooks/111/aaa",
                "webhook_type": "discord",
                "source_filters": "",
                "headers": "",
                "enabled": "on",
            },
        )
        assert response.status_code == 200
        html = response.text
        assert "required" in html.lower()


class TestWebhookUpdateDiscordOptions:
    """Update Discord-specific options."""

    async def test_update_discord_options_existing(
        self, client, create_webhook, db_session
    ):
        """Update an existing Discord webhook's options."""
        from sqlmodel import select

        wh = create_webhook(
            name="Discord Existing",
            url="https://discord.com/api/webhooks/222/bbb",
            webhook_type="discord",
        )
        opts = WebhookOptions(
            webhook_endpoint_id=wh.id,
            options={"color": 255, "username": "OldBot"},
        )
        db_session.add(opts)
        db_session.commit()

        response = await client.put(
            f"/htmx/webhooks/{wh.id}",
            data={
                "name": "Discord Existing",
                "url": "https://discord.com/api/webhooks/222/bbb",
                "webhook_type": "discord",
                "source_filters": "",
                "headers": "",
                "enabled": "on",
                "discord_color": "#00FF00",
                "discord_username": "NewBot",
                "discord_avatar_url": "https://example.com/new.png",
                "discord_footer": "New Footer",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("HX-Trigger") == "closeModal"

        db_session.expire_all()
        updated_opts = db_session.exec(
            select(WebhookOptions).where(WebhookOptions.webhook_endpoint_id == wh.id)
        ).first()
        assert updated_opts.options["username"] == "NewBot"
        assert updated_opts.options["avatar_url"] == "https://example.com/new.png"
        assert updated_opts.options["footer"] == "New Footer"

    async def test_update_generic_to_discord_creates_options(
        self, client, create_webhook, db_session
    ):
        """Switching from generic to discord creates new options row."""
        from sqlmodel import select

        wh = create_webhook(
            name="Was Generic",
            url="https://example.com/hook",
            webhook_type="generic",
        )

        response = await client.put(
            f"/htmx/webhooks/{wh.id}",
            data={
                "name": "Now Discord",
                "url": "https://discord.com/api/webhooks/333/ccc",
                "webhook_type": "discord",
                "source_filters": "",
                "headers": "",
                "enabled": "on",
                "discord_color": "#FF0000",
                "discord_username": "SwitchedBot",
                "discord_avatar_url": "",
                "discord_footer": "",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("HX-Trigger") == "closeModal"

        new_opts = db_session.exec(
            select(WebhookOptions).where(WebhookOptions.webhook_endpoint_id == wh.id)
        ).first()
        assert new_opts is not None
        assert new_opts.options["username"] == "SwitchedBot"

    async def test_update_discord_invalid_color_defaults(
        self, client, create_webhook, db_session
    ):
        """Invalid hex color on update falls back to default."""
        from sqlmodel import select

        wh = create_webhook(
            name="Bad Color Update",
            url="https://discord.com/api/webhooks/444/ddd",
            webhook_type="discord",
        )

        response = await client.put(
            f"/htmx/webhooks/{wh.id}",
            data={
                "name": "Bad Color Update",
                "url": "https://discord.com/api/webhooks/444/ddd",
                "webhook_type": "discord",
                "source_filters": "",
                "headers": "",
                "enabled": "on",
                "discord_color": "zzzzz",
                "discord_username": "Bot",
                "discord_avatar_url": "",
                "discord_footer": "",
            },
        )
        assert response.status_code == 200

        db_session.expire_all()
        opts = db_session.exec(
            select(WebhookOptions).where(WebhookOptions.webhook_endpoint_id == wh.id)
        ).first()
        assert opts.options["color"] == 16711749


class TestWebhookUpdateTypeSwitch:
    """Switching webhook type from Discord to generic deletes options."""

    async def test_switch_discord_to_generic_deletes_options(
        self, client, create_webhook, db_session
    ):
        """Switching from discord to generic removes the options row."""
        from sqlmodel import select

        wh = create_webhook(
            name="Was Discord",
            url="https://discord.com/api/webhooks/555/eee",
            webhook_type="discord",
        )
        opts = WebhookOptions(
            webhook_endpoint_id=wh.id,
            options={"color": 255, "username": "OldBot"},
        )
        db_session.add(opts)
        db_session.commit()

        response = await client.put(
            f"/htmx/webhooks/{wh.id}",
            data={
                "name": "Now Generic",
                "url": "https://example.com/hook",
                "webhook_type": "generic",
                "source_filters": "",
                "headers": "",
                "enabled": "on",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("HX-Trigger") == "closeModal"

        db_session.expire_all()
        remaining = db_session.exec(
            select(WebhookOptions).where(WebhookOptions.webhook_endpoint_id == wh.id)
        ).first()
        assert remaining is None


class TestWebhookTestErrors:
    """Error handling during test webhook send."""

    async def test_test_webhook_network_error(self, client, create_webhook):
        """Network error during test send returns failure HTML."""
        wh = create_webhook(name="Net Error Hook", url="https://example.com/hook")
        with patch(
            "app.routes.webhooks.send_test_webhook",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            response = await client.post(f"/htmx/webhooks/{wh.id}/test")
        assert response.status_code == 200
        html = response.text
        assert "test-failure" in html
        assert "Failed" in html

    async def test_test_webhook_non_success_status(self, client, create_webhook):
        """Non-2xx response from webhook target returns failure HTML."""
        wh = create_webhook(name="Bad Status Hook", url="https://example.com/hook")
        mock_response = AsyncMock()
        mock_response.status_code = 500
        with patch(
            "app.routes.webhooks.send_test_webhook",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            response = await client.post(f"/htmx/webhooks/{wh.id}/test")
        assert response.status_code == 200
        html = response.text
        assert "test-failure" in html
        assert "500" in html
