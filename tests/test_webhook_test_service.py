"""Tests for app.services.webhook_test — payload builders, header builders, options loader.

Tests build_test_webhook_payload(), build_test_headers(), and get_webhook_options()
using mock objects for WebhookEndpoint and a SQLite in-memory DB for get_webhook_options().
"""

from dataclasses import dataclass, field
from uuid import uuid4

import pytest
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Session, SQLModel, create_engine

from app.services.webhook_test import (
    build_test_headers,
    build_test_webhook_payload,
    get_webhook_options,
)


# ---------- Lightweight stub for WebhookEndpoint ----------


@dataclass
class FakeWebhook:
    """Minimal stand-in for WebhookEndpoint (avoids SQLModel table registration issues)."""

    webhook_type: str = "generic"
    url: str = "https://example.com/hook"
    headers: dict | None = None
    name: str = "Test Hook"
    id: str = field(default_factory=lambda: str(uuid4()))


# ---------- build_test_webhook_payload ----------


class TestBuildTestWebhookPayload:
    def test_generic_payload(self):
        wh = FakeWebhook(webhook_type="generic")
        payload = build_test_webhook_payload(wh, {})
        assert payload["event"] == "test"
        assert "test notification" in payload["message"].lower()

    def test_discord_payload_default_options(self):
        wh = FakeWebhook(webhook_type="discord")
        payload = build_test_webhook_payload(wh, {})
        assert payload["username"] == "Rsync Viewer"
        assert len(payload["embeds"]) == 1
        assert payload["embeds"][0]["color"] == 16711680
        assert "avatar_url" not in payload

    def test_discord_payload_custom_options(self):
        wh = FakeWebhook(webhook_type="discord")
        options = {
            "color": 255,
            "username": "Custom Bot",
            "avatar_url": "https://example.com/avatar.png",
        }
        payload = build_test_webhook_payload(wh, options)
        assert payload["username"] == "Custom Bot"
        assert payload["embeds"][0]["color"] == 255
        assert payload["avatar_url"] == "https://example.com/avatar.png"

    def test_discord_payload_no_avatar_when_empty(self):
        wh = FakeWebhook(webhook_type="discord")
        payload = build_test_webhook_payload(wh, {"avatar_url": ""})
        assert "avatar_url" not in payload

    def test_unknown_type_returns_generic(self):
        wh = FakeWebhook(webhook_type="slack")
        payload = build_test_webhook_payload(wh, {})
        assert payload["event"] == "test"


# ---------- build_test_headers ----------


class TestBuildTestHeaders:
    def test_default_headers(self):
        wh = FakeWebhook(headers=None)
        headers = build_test_headers(wh)
        assert headers == {"Content-Type": "application/json"}

    def test_custom_headers_merged(self):
        wh = FakeWebhook(headers={"Authorization": "Bearer abc123"})
        headers = build_test_headers(wh)
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"] == "Bearer abc123"

    def test_custom_content_type_override(self):
        wh = FakeWebhook(headers={"Content-Type": "text/plain"})
        headers = build_test_headers(wh)
        # Custom headers override default
        assert headers["Content-Type"] == "text/plain"

    def test_empty_dict_headers(self):
        wh = FakeWebhook(headers={})
        headers = build_test_headers(wh)
        assert headers == {"Content-Type": "application/json"}


# ---------- get_webhook_options (requires DB) ----------


class TestGetWebhookOptions:
    @pytest.fixture(scope="class")
    def sqlite_engine(self):
        """SQLite engine with webhook tables created (JSONB -> JSON)."""
        # Import models to register them
        from app.models.webhook import WebhookEndpoint  # noqa: F401
        from app.models.webhook_options import WebhookOptions  # noqa: F401

        # Swap JSONB to JSON for SQLite compatibility
        for table in SQLModel.metadata.tables.values():
            for col in table.columns:
                if isinstance(col.type, JSONB):
                    col.type = JSON()

        engine = create_engine("sqlite://", echo=False)
        SQLModel.metadata.create_all(engine)
        return engine

    @pytest.fixture()
    def db_session(self, sqlite_engine):
        connection = sqlite_engine.connect()
        transaction = connection.begin()
        sess = Session(bind=connection)
        yield sess
        sess.close()
        transaction.rollback()
        connection.close()

    def test_returns_options_when_exists(self, db_session):
        from app.models.webhook import WebhookEndpoint
        from app.models.webhook_options import WebhookOptions

        wh = WebhookEndpoint(
            name="test", url="https://example.com", webhook_type="discord"
        )
        db_session.add(wh)
        db_session.flush()

        opts = WebhookOptions(
            webhook_endpoint_id=wh.id,
            options={"color": 255, "username": "Bot"},
        )
        db_session.add(opts)
        db_session.flush()

        result = get_webhook_options(db_session, wh.id)
        assert result == {"color": 255, "username": "Bot"}

    def test_returns_empty_dict_when_no_options(self, db_session):
        from app.models.webhook import WebhookEndpoint

        wh = WebhookEndpoint(
            name="bare", url="https://example.com", webhook_type="generic"
        )
        db_session.add(wh)
        db_session.flush()

        result = get_webhook_options(db_session, wh.id)
        assert result == {}

    def test_returns_empty_dict_for_nonexistent_webhook(self, db_session):
        result = get_webhook_options(db_session, uuid4())
        assert result == {}
