"""Tests for app/services/monitoring_setup.py.

Behaviour originally specified by specs/monitoring-setup-wizard.md
(AC-005 key provisioning, AC-007 env vars / hub URL) and now exercised
through the JSON API (specs/settings-ui.md AC-008) and this service.
"""

from unittest.mock import MagicMock

import pytest
from sqlmodel import select

from app.models.sync_log import ApiKey
from app.models.user import User
from app.services.auth import ROLE_ADMIN, hash_password
from app.services.monitoring_setup import (
    detect_hub_url,
    generate_compose_snippet,
    parse_rsync_source,
    provision_client,
    sanitize_source_name,
    unique_key_name,
)


@pytest.fixture()
def admin(db_session):
    user = User(
        username="wizard-admin",
        email="wizard-admin@test.local",
        password_hash=hash_password("TestPass1!"),
        role=ROLE_ADMIN,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _provision(db_session, admin, **overrides):
    kwargs = dict(
        user_id=admin.id,
        hub_url="http://test",
        source_name="my-server",
        rsync_source="backup@192.168.1.10:/data",
        cron_schedule="0 */6 * * *",
        ssh_key_path="~/.ssh/id_rsa",
        rsync_args="-avz --stats",
        sync_mode="pull",
    )
    kwargs.update(overrides)
    return provision_client(db_session, **kwargs)


class TestSanitizeAndParse:
    def test_ac005_source_name_sanitized(self):
        assert sanitize_source_name("My Backup Server!") == "my-backup-server"
        assert sanitize_source_name("  nas_01  ") == "nas-01"

    def test_ac007_rsync_source_parsed(self):
        assert parse_rsync_source("root@192.168.1.50:/mnt/storage") == (
            "root",
            "192.168.1.50",
            "/mnt/storage",
        )

    def test_ac007_invalid_rsync_source(self):
        assert parse_rsync_source("just-a-path") is None
        assert parse_rsync_source("user@host") is None


class TestHubUrl:
    def _request(self, headers, client_host="127.0.0.1"):
        request = MagicMock()
        request.headers = headers
        request.url.scheme = "http"
        request.client.host = client_host
        return request

    def test_ac007_hub_url_from_request(self):
        request = self._request({"host": "hub.local:8000"})
        assert detect_hub_url(request) == "http://hub.local:8000"

    def test_ac007_forwarded_honoured_from_trusted_proxy(self):
        # Default FORWARDED_ALLOW_IPS trusts loopback only.
        request = self._request(
            {
                "host": "internal:8000",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "rsync.example.com",
            },
            client_host="127.0.0.1",
        )
        assert detect_hub_url(request) == "https://rsync.example.com"

    def test_ac006_forwarded_ignored_from_untrusted_client(self):
        request = self._request(
            {
                "host": "internal:8000",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "evil.example.com",
            },
            client_host="203.0.113.9",
        )
        assert detect_hub_url(request) == "http://internal:8000"


class TestComposeSnippet:
    def test_ac007_snippet_has_all_env_vars(self):
        snippet = generate_compose_snippet(
            source_name="env-test",
            remote_user="myuser",
            remote_host="myhost.local",
            remote_path="/data/backup",
            hub_url="https://hub",
            api_key="rsv_abc",
            cron_schedule="0 2 * * *",
            rsync_args="-avz --delete",
            sync_mode="pull",
            ssh_key_path="~/.ssh/id_rsa",
        )
        for line in (
            "services:",
            "rsync-client-env-test:",
            "REMOTE_HOST=myhost.local",
            "REMOTE_USER=myuser",
            "REMOTE_PATH=/data/backup",
            "RSYNC_VIEWER_URL=https://hub",
            "RSYNC_VIEWER_API_KEY=rsv_abc",
            "RSYNC_SOURCE_NAME=env-test",
            "CRON_SCHEDULE=0 2 * * *",
            "RSYNC_ARGS=-avz --delete",
            "SYNC_MODE=pull",
            "./data:/data\n",
        ):
            assert line in snippet

    def test_ac012_push_mode_mounts_data_read_only(self):
        snippet = generate_compose_snippet(
            source_name="s",
            remote_user="u",
            remote_host="h",
            remote_path="/p",
            hub_url="http://hub",
            api_key="rsv_k",
            cron_schedule="* * * * *",
            rsync_args="-a",
            sync_mode="push",
            ssh_key_path="/k",
        )
        assert "SYNC_MODE=push" in snippet
        assert "./data:/data:ro" in snippet


class TestProvisionClient:
    def test_ac005_api_key_created_on_generate(self, db_session, admin):
        result = _provision(db_session, admin)
        keys = db_session.exec(
            select(ApiKey).where(
                ApiKey.user_id == admin.id, ApiKey.name == "rsync-client-my-server"
            )
        ).all()
        assert len(keys) == 1
        assert keys[0].is_active is True
        assert result.key_name == "rsync-client-my-server"
        assert result.api_key.startswith("rsv_")
        assert f"RSYNC_VIEWER_API_KEY={result.api_key}" in result.snippet

    def test_ac005_duplicate_name_gets_suffix(self, db_session, admin):
        _provision(db_session, admin, source_name="dup-server")
        second = _provision(
            db_session, admin, source_name="dup-server", rsync_source="u@h:/other"
        )
        assert second.key_name == "rsync-client-dup-server-2"
        assert unique_key_name(db_session, admin.id, "rsync-client-dup-server") == (
            "rsync-client-dup-server-3"
        )

    def test_ac005_source_name_sanitized_in_key(self, db_session, admin):
        result = _provision(db_session, admin, source_name="My Backup Server!")
        assert result.source_name == "my-backup-server"
        assert result.key_name == "rsync-client-my-backup-server"

    def test_ac007_invalid_rsync_source_raises_before_creating_key(
        self, db_session, admin
    ):
        with pytest.raises(ValueError, match="user@host:/path"):
            _provision(db_session, admin, rsync_source="just-a-path")
        assert (
            db_session.exec(select(ApiKey).where(ApiKey.user_id == admin.id)).all()
            == []
        )
