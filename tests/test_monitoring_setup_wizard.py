"""Tests for Monitoring Setup Wizard.

Spec: specs/monitoring-setup-wizard.md
"""

import os
from datetime import timedelta

import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session, select

from app.config import get_settings
from app.database import get_session
from app.main import app
from app.models.sync_log import ApiKey
from app.models.user import User
from app.services.auth import ROLE_ADMIN, ROLE_OPERATOR, ROLE_VIEWER, hash_password
from app.utils import utc_now

_TEST_SECRET = "test-secret-key"
_TEST_ALGORITHM = "HS256"


def _make_jwt(user_id: str, username: str, role: str) -> str:
    now = utc_now()
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=30),
    }
    return pyjwt.encode(payload, _TEST_SECRET, algorithm=_TEST_ALGORITHM)


def _setup_overrides(db_session: Session):
    from tests.conftest import get_test_settings

    os.environ["SECRET_KEY"] = _TEST_SECRET
    os.environ["DEBUG"] = "true"
    os.environ["DEFAULT_API_KEY"] = "test-api-key"
    get_settings.cache_clear()

    def get_test_session():
        yield db_session

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_settings] = get_test_settings


def _cleanup():
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def _create_user(
    db_session: Session,
    username: str = "testadmin",
    role: str = ROLE_ADMIN,
) -> User:
    user = User(
        username=username,
        email=f"{username}@test.local",
        password_hash=hash_password("TestPass1!"),
        role=role,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _make_client(user: User) -> AsyncClient:
    from app.csrf import generate_csrf_token

    jwt_token = _make_jwt(str(user.id), user.username, user.role)
    csrf_token = generate_csrf_token()
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-CSRF-Token": csrf_token},
        cookies={"access_token": jwt_token, "csrf_token": csrf_token},
    )


# ---------------------------------------------------------------------------
# AC-001: Monitoring tab on Settings page
# ---------------------------------------------------------------------------


class TestAC001MonitoringTab:
    """AC-001: A new 'Monitoring' tab appears on the Settings page."""

    @pytest.mark.anyio
    async def test_ac001_settings_page_has_monitoring_tab(
        self, test_engine, db_session
    ):
        """Settings page contains a Monitoring tab link for admin users."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-tab", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.get("/settings")
        _cleanup()

        assert response.status_code == 200
        assert "Monitoring" in response.text

    @pytest.mark.anyio
    async def test_ac001_monitoring_tab_hidden_for_non_admin(
        self, test_engine, db_session
    ):
        """Non-admin users should not see the Monitoring tab."""
        _setup_overrides(db_session)
        operator = _create_user(db_session, "op-tab", ROLE_OPERATOR)
        async with _make_client(operator) as client:
            response = await client.get("/settings")
        _cleanup()

        assert response.status_code == 200
        # The monitoring tab should not appear for operators
        assert "monitoring-setup" not in response.text


# ---------------------------------------------------------------------------
# AC-002: Two sections in Monitoring tab
# ---------------------------------------------------------------------------


class TestAC002MonitoringSections:
    """AC-002: Monitoring tab has Rsync Client Setup and Synthetic Health Check."""

    @pytest.mark.anyio
    async def test_ac002_monitoring_partial_has_both_sections(
        self, test_engine, db_session
    ):
        """GET /htmx/monitoring-setup returns both sections."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-sec", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.get("/htmx/monitoring-setup")
        _cleanup()

        assert response.status_code == 200
        assert "Rsync Client Setup" in response.text
        assert "Synthetic Health Check" in response.text


# ---------------------------------------------------------------------------
# AC-003: Form fields with defaults
# ---------------------------------------------------------------------------


class TestAC003FormFields:
    """AC-003: Form has required and optional fields with correct defaults."""

    @pytest.mark.anyio
    async def test_ac003_form_has_all_fields(self, test_engine, db_session):
        """Form contains source_name, rsync_source, cron_schedule, ssh_key_path, rsync_args."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-form", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.get("/htmx/monitoring-setup")
        _cleanup()

        html = response.text
        assert response.status_code == 200
        assert 'name="source_name"' in html
        assert 'name="rsync_source"' in html
        assert 'name="cron_schedule"' in html
        assert 'name="ssh_key_path"' in html
        assert 'name="rsync_args"' in html

    @pytest.mark.anyio
    async def test_ac003_form_has_default_values(self, test_engine, db_session):
        """Form fields have correct default values."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-defaults", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.get("/htmx/monitoring-setup")
        _cleanup()

        html = response.text
        assert "0 */6 * * *" in html  # cron default
        assert "~/.ssh/id_rsa" in html  # ssh key default
        assert "-avz --stats" in html  # rsync args default


# ---------------------------------------------------------------------------
# AC-004: Form validation
# ---------------------------------------------------------------------------


class TestAC004Validation:
    """AC-004: Validates required fields, shows inline errors."""

    @pytest.mark.anyio
    async def test_ac004_missing_source_name_shows_error(self, test_engine, db_session):
        """Missing source_name returns validation error."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-val1", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/monitoring-setup/generate",
                data={
                    "source_name": "",
                    "rsync_source": "user@host:/path",
                },
            )
        _cleanup()

        assert response.status_code in (200, 422)
        assert (
            "required" in response.text.lower()
            or "source name" in response.text.lower()
        )

    @pytest.mark.anyio
    async def test_ac004_missing_rsync_source_shows_error(
        self, test_engine, db_session
    ):
        """Missing rsync_source returns validation error."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-val2", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/monitoring-setup/generate",
                data={
                    "source_name": "my-server",
                    "rsync_source": "",
                },
            )
        _cleanup()

        assert response.status_code in (200, 422)
        assert (
            "required" in response.text.lower()
            or "rsync source" in response.text.lower()
        )

    @pytest.mark.anyio
    async def test_ac004_no_api_key_created_on_validation_failure(
        self, test_engine, db_session
    ):
        """No API key is created when validation fails."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-val3", ROLE_ADMIN)

        # Count keys before
        keys_before = len(
            db_session.exec(select(ApiKey).where(ApiKey.user_id == admin.id)).all()
        )

        async with _make_client(admin) as client:
            await client.post(
                "/htmx/monitoring-setup/generate",
                data={"source_name": "", "rsync_source": ""},
            )
        _cleanup()

        keys_after = len(
            db_session.exec(select(ApiKey).where(ApiKey.user_id == admin.id)).all()
        )
        assert keys_after == keys_before


# ---------------------------------------------------------------------------
# AC-005: Auto-provision API key
# ---------------------------------------------------------------------------


class TestAC005ApiKeyProvisioning:
    """AC-005: API key auto-provisioned with correct name, tied to current user."""

    @pytest.mark.anyio
    async def test_ac005_api_key_created_on_generate(self, test_engine, db_session):
        """A new API key is created with name rsync-client-{source_name}."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-key1", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/monitoring-setup/generate",
                data={
                    "source_name": "my-server",
                    "rsync_source": "backup@192.168.1.10:/data",
                },
            )
        _cleanup()

        assert response.status_code == 200
        # Check that an API key was created for this user
        keys = db_session.exec(
            select(ApiKey).where(
                ApiKey.user_id == admin.id,
                ApiKey.name == "rsync-client-my-server",
            )
        ).all()
        assert len(keys) == 1
        assert keys[0].is_active is True

    @pytest.mark.anyio
    async def test_ac005_duplicate_name_gets_suffix(self, test_engine, db_session):
        """Duplicate source name API key gets numeric suffix."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-dup", ROLE_ADMIN)
        async with _make_client(admin) as client:
            # First generation
            await client.post(
                "/htmx/monitoring-setup/generate",
                data={
                    "source_name": "dup-server",
                    "rsync_source": "user@host:/path",
                },
            )
            # Second generation with same name
            await client.post(
                "/htmx/monitoring-setup/generate",
                data={
                    "source_name": "dup-server",
                    "rsync_source": "user@host:/other",
                },
            )
        _cleanup()

        keys = db_session.exec(select(ApiKey).where(ApiKey.user_id == admin.id)).all()
        key_names = [k.name for k in keys]
        assert "rsync-client-dup-server" in key_names
        assert "rsync-client-dup-server-2" in key_names

    @pytest.mark.anyio
    async def test_ac005_source_name_sanitized(self, test_engine, db_session):
        """Source name with spaces/special chars is sanitized to kebab-case."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-san", ROLE_ADMIN)
        async with _make_client(admin) as client:
            await client.post(
                "/htmx/monitoring-setup/generate",
                data={
                    "source_name": "My Backup Server!",
                    "rsync_source": "user@host:/path",
                },
            )
        _cleanup()

        keys = db_session.exec(select(ApiKey).where(ApiKey.user_id == admin.id)).all()
        assert len(keys) == 1
        assert keys[0].name == "rsync-client-my-backup-server"


# ---------------------------------------------------------------------------
# AC-006: Docker Compose snippet output
# ---------------------------------------------------------------------------


class TestAC006ComposeSnippet:
    """AC-006: Generated compose snippet is a complete services block."""

    @pytest.mark.anyio
    async def test_ac006_compose_snippet_returned(self, test_engine, db_session):
        """POST returns a Docker Compose snippet in the response."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-comp", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/monitoring-setup/generate",
                data={
                    "source_name": "test-compose",
                    "rsync_source": "backup@10.0.0.1:/backups",
                },
            )
        _cleanup()

        html = response.text
        assert response.status_code == 200
        assert "services:" in html
        assert "rsync-client-test-compose" in html
        assert "rsv_" in html  # API key prefix present


# ---------------------------------------------------------------------------
# AC-007: Hub URL and env vars in snippet
# ---------------------------------------------------------------------------


class TestAC007EnvVars:
    """AC-007: Snippet includes all required environment variables."""

    @pytest.mark.anyio
    async def test_ac007_snippet_has_all_env_vars(self, test_engine, db_session):
        """Generated snippet contains all required env vars."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-env", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/monitoring-setup/generate",
                data={
                    "source_name": "env-test",
                    "rsync_source": "myuser@myhost.local:/data/backup",
                    "cron_schedule": "0 2 * * *",
                    "rsync_args": "-avz --delete",
                },
            )
        _cleanup()

        html = response.text
        assert "REMOTE_HOST=myhost.local" in html
        assert "REMOTE_USER=myuser" in html
        assert "REMOTE_PATH=/data/backup" in html
        assert "RSYNC_VIEWER_URL=" in html
        assert "RSYNC_VIEWER_API_KEY=rsv_" in html
        assert "RSYNC_SOURCE_NAME=env-test" in html
        assert "CRON_SCHEDULE=0 2 * * *" in html
        assert "RSYNC_ARGS=-avz --delete" in html

    @pytest.mark.anyio
    async def test_ac007_rsync_source_parsed_correctly(self, test_engine, db_session):
        """Rsync source user@host:/path is parsed into separate env vars."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-parse", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/monitoring-setup/generate",
                data={
                    "source_name": "parse-test",
                    "rsync_source": "root@192.168.1.50:/mnt/storage",
                },
            )
        _cleanup()

        html = response.text
        assert "REMOTE_USER=root" in html
        assert "REMOTE_HOST=192.168.1.50" in html
        assert "REMOTE_PATH=/mnt/storage" in html

    @pytest.mark.anyio
    async def test_ac007_invalid_rsync_source_format(self, test_engine, db_session):
        """Invalid rsync source format shows validation hint."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-badfmt", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/monitoring-setup/generate",
                data={
                    "source_name": "bad-format",
                    "rsync_source": "just-a-path",
                },
            )
        _cleanup()

        # Should show a format validation error
        assert (
            "user@host:/path" in response.text.lower()
            or "format" in response.text.lower()
        )

    @pytest.mark.anyio
    async def test_ac007_hub_url_from_request(self, test_engine, db_session):
        """Hub URL in snippet is derived from the request."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-url", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/monitoring-setup/generate",
                data={
                    "source_name": "url-test",
                    "rsync_source": "user@host:/path",
                },
            )
        _cleanup()

        # The test client uses http://test as base_url
        assert "RSYNC_VIEWER_URL=http://" in response.text

    @pytest.mark.anyio
    async def test_ac007_hub_url_respects_forwarded_headers(
        self, test_engine, db_session
    ):
        """Hub URL uses X-Forwarded-Proto and X-Forwarded-Host when present."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-fwd", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/monitoring-setup/generate",
                data={
                    "source_name": "fwd-test",
                    "rsync_source": "user@host:/path",
                },
                headers={
                    **client.headers,
                    "X-Forwarded-Proto": "https",
                    "X-Forwarded-Host": "rsync.example.com",
                },
            )
        _cleanup()

        assert "RSYNC_VIEWER_URL=https://rsync.example.com" in response.text


# ---------------------------------------------------------------------------
# AC-008: Raw key shown once
# ---------------------------------------------------------------------------


class TestAC008KeyShownOnce:
    """AC-008: Raw API key shown only in the generate response."""

    @pytest.mark.anyio
    async def test_ac008_key_not_shown_on_get(self, test_engine, db_session):
        """GET /htmx/monitoring-setup does not show any raw API keys."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-once", ROLE_ADMIN)
        async with _make_client(admin) as client:
            # First generate a key
            await client.post(
                "/htmx/monitoring-setup/generate",
                data={
                    "source_name": "once-test",
                    "rsync_source": "user@host:/path",
                },
            )
            # Then re-load the form
            response = await client.get("/htmx/monitoring-setup")
        _cleanup()

        assert "rsv_" not in response.text


# ---------------------------------------------------------------------------
# AC-009: Synthetic Health Check in Monitoring tab
# ---------------------------------------------------------------------------


class TestAC009SyntheticSection:
    """AC-009: Synthetic Health Check section in Monitoring tab."""

    @pytest.mark.anyio
    async def test_ac009_synthetic_section_present(self, test_engine, db_session):
        """Monitoring tab includes synthetic monitoring controls."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-syn", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.get("/htmx/monitoring-setup")
        _cleanup()

        html = response.text
        assert response.status_code == 200
        # Should include the synthetic settings (either inline or via hx-get reference)
        assert "synthetic" in html.lower()


# ---------------------------------------------------------------------------
# AC-010: Changelog moved to own tab
# ---------------------------------------------------------------------------


class TestAC010ChangelogTab:
    """AC-010: Changelog moved from right column to its own tab."""

    @pytest.mark.anyio
    async def test_ac010_settings_page_has_changelog_tab(self, test_engine, db_session):
        """Settings page has a Changelog tab."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-cl", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.get("/settings")
        _cleanup()

        html = response.text
        assert response.status_code == 200
        # Changelog should appear as a tab, not inline in the settings grid
        assert "Changelog" in html

    @pytest.mark.anyio
    async def test_ac010_changelog_not_in_settings_grid(self, test_engine, db_session):
        """Changelog is no longer in the two-column settings grid."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-cl2", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.get("/settings")
        _cleanup()

        html = response.text
        # Changelog should be in its own tab, not inside the settings-grid.
        # Verify changelog-list appears after the changelog tab marker,
        # which itself comes after the settings-grid section.
        grid_start = html.find('class="settings-grid"')
        changelog_tab = html.find('data-tab-content="changelog"')
        changelog_list = html.find('id="changelog-list"')
        assert changelog_list > 0
        assert changelog_tab > 0
        assert changelog_list > changelog_tab, (
            "changelog-list should be inside changelog tab"
        )
        assert grid_start < changelog_tab, (
            "settings-grid should come before changelog tab"
        )


# ---------------------------------------------------------------------------
# AC-011: HTMX lazy-load
# ---------------------------------------------------------------------------


class TestAC011HtmxLazyLoad:
    """AC-011: Monitoring tab content lazy-loads via HTMX."""

    @pytest.mark.anyio
    async def test_ac011_monitoring_tab_uses_htmx_load(self, test_engine, db_session):
        """Settings page has hx-get for monitoring-setup partial."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-htmx", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.get("/settings")
        _cleanup()

        html = response.text
        assert "/htmx/monitoring-setup" in html


# ---------------------------------------------------------------------------
# AC-012: Push/pull sync mode
# ---------------------------------------------------------------------------


class TestAC012SyncMode:
    """AC-012: Compose snippet supports pull and push sync modes."""

    @pytest.mark.anyio
    async def test_ac012_pull_mode_default(self, test_engine, db_session):
        """Default sync mode is pull with rw volume mount."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-pull", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/monitoring-setup/generate",
                data={
                    "source_name": "pull-test",
                    "rsync_source": "user@host:/path",
                    "sync_mode": "pull",
                },
            )
        _cleanup()

        html = response.text
        assert "SYNC_MODE=pull" in html
        # Pull mode: data volume should NOT be read-only
        assert "./data:/data" in html
        assert "./data:/data:ro" not in html

    @pytest.mark.anyio
    async def test_ac012_push_mode(self, test_engine, db_session):
        """Push mode sets SYNC_MODE=push and data volume to :ro."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-push", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/monitoring-setup/generate",
                data={
                    "source_name": "push-test",
                    "rsync_source": "user@host:/path",
                    "sync_mode": "push",
                },
            )
        _cleanup()

        html = response.text
        assert "SYNC_MODE=push" in html
        assert "./data:/data:ro" in html

    @pytest.mark.anyio
    async def test_ac012_form_has_sync_mode_selector(self, test_engine, db_session):
        """Form contains sync mode radio/select options."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-mode", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.get("/htmx/monitoring-setup")
        _cleanup()

        html = response.text
        assert 'name="sync_mode"' in html


# ---------------------------------------------------------------------------
# AC-013: Instructional text
# ---------------------------------------------------------------------------


class TestAC013InstructionalText:
    """AC-013: Form includes instructional text about rsync client."""

    @pytest.mark.anyio
    async def test_ac013_instructional_text_present(self, test_engine, db_session):
        """Monitoring tab includes explanatory text about the rsync client."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-info", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.get("/htmx/monitoring-setup")
        _cleanup()

        html = response.text.lower()
        # Should have some explanatory text about what the rsync client does
        assert "rsync" in html
        assert "docker" in html or "container" in html or "compose" in html


# ---------------------------------------------------------------------------
# Access control tests
# ---------------------------------------------------------------------------


class TestMonitoringAccessControl:
    """Non-admin users cannot access monitoring setup endpoints."""

    @pytest.mark.anyio
    async def test_operator_cannot_get_monitoring_setup(self, test_engine, db_session):
        _setup_overrides(db_session)
        operator = _create_user(db_session, "op-mon", ROLE_OPERATOR)
        async with _make_client(operator) as client:
            response = await client.get("/htmx/monitoring-setup")
        _cleanup()

        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_operator_cannot_post_generate(self, test_engine, db_session):
        _setup_overrides(db_session)
        operator = _create_user(db_session, "op-gen", ROLE_OPERATOR)
        async with _make_client(operator) as client:
            response = await client.post(
                "/htmx/monitoring-setup/generate",
                data={
                    "source_name": "test",
                    "rsync_source": "user@host:/path",
                },
            )
        _cleanup()

        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_viewer_cannot_access_monitoring(self, test_engine, db_session):
        _setup_overrides(db_session)
        viewer = _create_user(db_session, "view-mon", ROLE_VIEWER)
        async with _make_client(viewer) as client:
            response = await client.get("/htmx/monitoring-setup")
        _cleanup()

        assert response.status_code == 403
