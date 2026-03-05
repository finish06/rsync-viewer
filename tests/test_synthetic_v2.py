"""Tests for synthetic monitoring v0.2.0 (AC-013 through AC-018).

DB-backed config, runtime start/stop, result storage, and history dashboard.
"""

import os
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import select

from app.config import get_settings
from app.csrf import generate_csrf_token
from app.database import get_session
from app.main import app
from app.models.synthetic_check_config import SyntheticCheckConfig
from app.models.synthetic_check_result import SyntheticCheckResultRecord
from app.services.synthetic_check import (
    SyntheticCheckResult,
    get_check_history,
    get_db_config,
    get_uptime_percentage,
    save_db_config,
    store_check_result,
)
from app.utils import utc_now
from tests.conftest import get_test_settings


@pytest.fixture()
def _clean_synthetic_config(db_session):
    """Ensure no SyntheticCheckConfig rows exist before the test."""
    existing = db_session.exec(select(SyntheticCheckConfig)).all()
    for row in existing:
        db_session.delete(row)
    existing_results = db_session.exec(select(SyntheticCheckResultRecord)).all()
    for row in existing_results:
        db_session.delete(row)
    db_session.commit()


@pytest.fixture()
def admin_client(test_engine, db_session):
    """Admin-level test client for UI routes."""
    from app.models.user import User
    from app.services.auth import ROLE_ADMIN, hash_password

    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["DEBUG"] = "true"
    os.environ["DEFAULT_API_KEY"] = "test-api-key"
    get_settings.cache_clear()

    admin = User(
        username="synth-v2-admin",
        email="synth-v2-admin@test.local",
        password_hash=hash_password("TestPass1!"),
        role=ROLE_ADMIN,
    )
    db_session.add(admin)
    db_session.flush()

    def get_test_session_gen():
        yield db_session

    app.dependency_overrides[get_session] = get_test_session_gen
    app.dependency_overrides[get_settings] = get_test_settings

    now = utc_now()
    jwt_token = pyjwt.encode(
        {
            "sub": str(admin.id),
            "username": admin.username,
            "role": admin.role,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=30),
        },
        "test-secret-key",
        algorithm="HS256",
    )
    csrf_token = generate_csrf_token()

    yield AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-CSRF-Token": csrf_token},
        cookies={"access_token": jwt_token, "csrf_token": csrf_token},
    )

    app.dependency_overrides.clear()
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# AC-014: DB-backed config persistence
# ---------------------------------------------------------------------------


class TestDbConfig:
    """AC-014: Config persisted in DB, seeded from env vars."""

    @pytest.mark.usefixtures("_clean_synthetic_config")
    def test_ac014_get_db_config_seeds_from_env(self, db_session):
        """First call seeds a row from env vars."""
        config = get_db_config(db_session)
        assert config.id == 1
        assert isinstance(config.enabled, bool)
        assert config.interval_seconds > 0

    @pytest.mark.usefixtures("_clean_synthetic_config")
    def test_ac014_get_db_config_returns_existing(self, db_session):
        """Subsequent calls return the same row."""
        first = get_db_config(db_session)
        second = get_db_config(db_session)
        assert first.id == second.id

    @pytest.mark.usefixtures("_clean_synthetic_config")
    def test_ac014_save_db_config_persists(self, db_session):
        """save_db_config writes enabled/interval to DB."""
        get_db_config(db_session)  # seed
        updated = save_db_config(db_session, enabled=True, interval_seconds=120)
        assert updated.enabled is True
        assert updated.interval_seconds == 120

        # Re-read from DB
        reloaded = get_db_config(db_session)
        assert reloaded.enabled is True
        assert reloaded.interval_seconds == 120

    @pytest.mark.usefixtures("_clean_synthetic_config")
    def test_ac014_save_db_config_clamps_interval(self, db_session):
        """Interval below 30 is clamped to 30."""
        get_db_config(db_session)
        updated = save_db_config(db_session, enabled=True, interval_seconds=5)
        assert updated.interval_seconds == 30

    @pytest.mark.usefixtures("_clean_synthetic_config")
    def test_ac014_save_db_config_updates_timestamp(self, db_session):
        """updated_at changes on save."""
        config = get_db_config(db_session)
        original_ts = config.updated_at
        save_db_config(db_session, enabled=False, interval_seconds=300)
        reloaded = get_db_config(db_session)
        assert reloaded.updated_at >= original_ts


# ---------------------------------------------------------------------------
# AC-016: Check result storage
# ---------------------------------------------------------------------------


class TestCheckResultStorage:
    """AC-016: Check results stored in DB with auto-pruning."""

    @pytest.mark.usefixtures("_clean_synthetic_config")
    def test_ac016_store_check_result_inserts_row(self, db_session):
        """store_check_result creates a row in the DB."""
        outcome = SyntheticCheckResult(status="passing", latency_ms=42.5)
        store_check_result(db_session, outcome)

        rows = db_session.exec(select(SyntheticCheckResultRecord)).all()
        assert len(rows) == 1
        assert rows[0].status == "passing"
        assert rows[0].latency_ms == 42.5
        assert rows[0].error is None

    @pytest.mark.usefixtures("_clean_synthetic_config")
    def test_ac016_store_check_result_with_error(self, db_session):
        """Failing result stores error string."""
        outcome = SyntheticCheckResult(
            status="failing", latency_ms=100.0, error="connection refused"
        )
        store_check_result(db_session, outcome)

        rows = db_session.exec(select(SyntheticCheckResultRecord)).all()
        assert rows[0].error == "connection refused"

    @pytest.mark.usefixtures("_clean_synthetic_config")
    def test_ac016_prunes_at_100_rows(self, db_session):
        """Auto-prune keeps only the 100 newest rows."""
        from app.services.synthetic_check import MAX_RESULT_ROWS

        # Insert 105 rows
        for i in range(105):
            outcome = SyntheticCheckResult(status="passing", latency_ms=float(i))
            store_check_result(db_session, outcome)

        rows = db_session.exec(select(SyntheticCheckResultRecord)).all()
        assert len(rows) <= MAX_RESULT_ROWS

    @pytest.mark.usefixtures("_clean_synthetic_config")
    def test_ac016_get_check_history_returns_newest_first(self, db_session):
        """get_check_history returns results newest first."""
        for i in range(3):
            outcome = SyntheticCheckResult(status="passing", latency_ms=float(i))
            store_check_result(db_session, outcome)

        history = get_check_history(db_session, limit=10)
        assert len(history) == 3
        # Newest first
        assert history[0].latency_ms >= history[-1].latency_ms


# ---------------------------------------------------------------------------
# AC-016: Uptime percentage
# ---------------------------------------------------------------------------


class TestUptimePercentage:
    """AC-016/AC-017: Uptime calculation over time window."""

    @pytest.mark.usefixtures("_clean_synthetic_config")
    def test_ac016_uptime_none_when_no_data(self, db_session):
        """Returns None when no results exist."""
        assert get_uptime_percentage(db_session, hours=24) is None

    @pytest.mark.usefixtures("_clean_synthetic_config")
    def test_ac016_uptime_100_when_all_passing(self, db_session):
        """Returns 100.0 when all checks pass."""
        for _ in range(5):
            store_check_result(
                db_session, SyntheticCheckResult(status="passing", latency_ms=10.0)
            )
        assert get_uptime_percentage(db_session, hours=24) == 100.0

    @pytest.mark.usefixtures("_clean_synthetic_config")
    def test_ac016_uptime_calculates_ratio(self, db_session):
        """Uptime is pass/total ratio."""
        for _ in range(3):
            store_check_result(
                db_session, SyntheticCheckResult(status="passing", latency_ms=10.0)
            )
        store_check_result(
            db_session,
            SyntheticCheckResult(status="failing", latency_ms=10.0, error="err"),
        )
        uptime = get_uptime_percentage(db_session, hours=24)
        assert uptime == 75.0


# ---------------------------------------------------------------------------
# AC-013: Runtime start/stop
# ---------------------------------------------------------------------------


class TestRuntimeStartStop:
    """AC-013: start/stop without app restart."""

    @pytest.fixture(autouse=True)
    def _reset_globals(self):
        """Reset module-level globals before each test."""
        import app.services.synthetic_check as sc_module

        sc_module._background_task = None
        sc_module._shutdown_event = None
        sc_module._state = sc_module.SyntheticCheckState()
        yield
        # Cleanup after
        sc_module._background_task = None
        sc_module._shutdown_event = None
        sc_module._state = sc_module.SyntheticCheckState()

    @pytest.mark.anyio
    async def test_ac013_start_creates_task_when_enabled(self):
        """start_synthetic_monitoring creates a background task when enabled."""
        import asyncio
        from contextlib import contextmanager
        from unittest.mock import MagicMock

        from app.models.synthetic_check_config import SyntheticCheckConfig
        from app.services import synthetic_check as sc_module

        mock_config = SyntheticCheckConfig(
            id=1, enabled=True, interval_seconds=300, api_key="test-key"
        )

        # Mock Session context manager
        mock_session = MagicMock()

        @contextmanager
        def mock_session_cm(engine):
            yield mock_session

        async def _noop(**kwargs):
            return

        with (
            patch(
                "app.services.synthetic_check.get_db_config", return_value=mock_config
            ),
            patch(
                "app.services.synthetic_check.synthetic_check_background_task", _noop
            ),
            patch("sqlmodel.Session", mock_session_cm),
        ):
            await sc_module.start_synthetic_monitoring("fake-engine")

        assert sc_module._background_task is not None

        # Cleanup
        await asyncio.sleep(0.05)
        await sc_module.stop_synthetic_monitoring()

    @pytest.mark.anyio
    async def test_ac013_stop_clears_state(self):
        """stop_synthetic_monitoring clears task and state."""
        from app.services import synthetic_check as sc_module

        sc_module._state.enabled = True
        await sc_module.stop_synthetic_monitoring()
        assert sc_module._background_task is None
        assert sc_module._shutdown_event is None
        assert sc_module._state.enabled is False

    @pytest.mark.anyio
    async def test_ac013_start_does_nothing_when_disabled(self):
        """start_synthetic_monitoring is a no-op when DB config disabled."""
        from contextlib import contextmanager
        from unittest.mock import MagicMock

        from app.models.synthetic_check_config import SyntheticCheckConfig
        from app.services import synthetic_check as sc_module

        mock_config = SyntheticCheckConfig(id=1, enabled=False, interval_seconds=300)

        mock_session = MagicMock()

        @contextmanager
        def mock_session_cm(engine):
            yield mock_session

        with (
            patch(
                "app.services.synthetic_check.get_db_config", return_value=mock_config
            ),
            patch("sqlmodel.Session", mock_session_cm),
        ):
            await sc_module.start_synthetic_monitoring("fake-engine")

        assert sc_module._background_task is None
        assert sc_module._state.enabled is False

    @pytest.mark.anyio
    @pytest.mark.usefixtures("_clean_synthetic_config")
    async def test_ac013_settings_post_enables_task(self, admin_client, db_session):
        """POST /htmx/synthetic-settings with enabled=on starts the task."""
        mock_start = AsyncMock()
        with patch(
            "app.services.synthetic_check.start_synthetic_monitoring", mock_start
        ):
            response = await admin_client.post(
                "/htmx/synthetic-settings",
                data={"enabled": "on", "interval": "120"},
            )
        assert response.status_code == 200
        mock_start.assert_called_once()

    @pytest.mark.anyio
    @pytest.mark.usefixtures("_clean_synthetic_config")
    async def test_ac013_settings_post_disables_task(self, admin_client, db_session):
        """POST /htmx/synthetic-settings without enabled stops the task."""
        mock_stop = AsyncMock()
        with patch("app.services.synthetic_check.stop_synthetic_monitoring", mock_stop):
            response = await admin_client.post(
                "/htmx/synthetic-settings",
                data={"interval": "300"},
            )
        assert response.status_code == 200
        mock_stop.assert_called_once()

    @pytest.mark.anyio
    @pytest.mark.usefixtures("_clean_synthetic_config")
    async def test_ac013_settings_post_writes_db(self, admin_client, db_session):
        """POST /htmx/synthetic-settings persists config to DB."""
        with patch(
            "app.services.synthetic_check.start_synthetic_monitoring", AsyncMock()
        ):
            response = await admin_client.post(
                "/htmx/synthetic-settings",
                data={"enabled": "on", "interval": "180"},
            )
        assert response.status_code == 200

        config = get_db_config(db_session)
        assert config.enabled is True
        assert config.interval_seconds == 180


# ---------------------------------------------------------------------------
# AC-015: Lifespan reads DB config
# ---------------------------------------------------------------------------


class TestLifespanDbConfig:
    """AC-015: Lifespan reads DB config, env vars are bootstrap defaults only."""

    @pytest.mark.anyio
    async def test_ac015_lifespan_calls_start_synthetic(self):
        """Lifespan calls start_synthetic_monitoring (which reads DB)."""
        with (
            patch(
                "app.main.start_synthetic_monitoring", new_callable=AsyncMock
            ) as mock_start,
            patch("app.main.stop_synthetic_monitoring", new_callable=AsyncMock),
        ):
            async with app.router.lifespan_context(app):
                mock_start.assert_called_once()

    @pytest.mark.anyio
    async def test_ac015_lifespan_calls_stop_on_shutdown(self):
        """Lifespan calls stop_synthetic_monitoring on shutdown."""
        with (
            patch("app.main.start_synthetic_monitoring", new_callable=AsyncMock),
            patch(
                "app.main.stop_synthetic_monitoring", new_callable=AsyncMock
            ) as mock_stop,
        ):
            async with app.router.lifespan_context(app):
                pass
            mock_stop.assert_called_once()


# ---------------------------------------------------------------------------
# AC-017: History route
# ---------------------------------------------------------------------------


class TestHistoryRoute:
    """AC-017: Admin history route returns HTML with timeline and uptime."""

    @pytest.mark.anyio
    @pytest.mark.usefixtures("_clean_synthetic_config")
    async def test_ac017_history_returns_html(self, admin_client, db_session):
        """GET /htmx/synthetic-history returns HTML."""
        response = await admin_client.get("/htmx/synthetic-history")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.anyio
    @pytest.mark.usefixtures("_clean_synthetic_config")
    async def test_ac017_history_shows_results(self, admin_client, db_session):
        """History shows check results when they exist."""
        store_check_result(
            db_session, SyntheticCheckResult(status="passing", latency_ms=25.0)
        )
        store_check_result(
            db_session,
            SyntheticCheckResult(status="failing", latency_ms=100.0, error="timeout"),
        )

        response = await admin_client.get("/htmx/synthetic-history")
        assert response.status_code == 200
        text = response.text
        assert "Pass" in text or "passing" in text.lower()
        assert "Fail" in text or "failing" in text.lower()

    @pytest.mark.anyio
    @pytest.mark.usefixtures("_clean_synthetic_config")
    async def test_ac017_history_shows_uptime(self, admin_client, db_session):
        """History shows uptime percentage."""
        for _ in range(4):
            store_check_result(
                db_session, SyntheticCheckResult(status="passing", latency_ms=10.0)
            )
        store_check_result(
            db_session,
            SyntheticCheckResult(status="failing", latency_ms=10.0, error="err"),
        )

        response = await admin_client.get("/htmx/synthetic-history")
        assert response.status_code == 200
        assert "80.0%" in response.text

    @pytest.mark.anyio
    @pytest.mark.usefixtures("_clean_synthetic_config")
    async def test_ac017_history_empty_state(self, admin_client, db_session):
        """History shows empty state message when no results."""
        response = await admin_client.get("/htmx/synthetic-history")
        assert response.status_code == 200
        assert "No check history" in response.text

    @pytest.mark.anyio
    async def test_ac017_history_requires_admin(self, client):
        """Non-admin gets 403 on history route."""
        response = await client.get("/htmx/synthetic-history")
        assert response.status_code == 403

    @pytest.mark.anyio
    @pytest.mark.usefixtures("_clean_synthetic_config")
    async def test_ac017_monitoring_setup_includes_history_section(
        self, admin_client, db_session
    ):
        """Monitoring setup page includes check history section."""
        response = await admin_client.get("/htmx/monitoring-setup")
        assert response.status_code == 200
        assert "Check History" in response.text


# ---------------------------------------------------------------------------
# AC-018: Auto-refresh
# ---------------------------------------------------------------------------


class TestAutoRefresh:
    """AC-018: History container auto-refreshes every 60s."""

    @pytest.mark.anyio
    @pytest.mark.usefixtures("_clean_synthetic_config")
    async def test_ac018_history_has_auto_refresh_trigger(
        self, admin_client, db_session
    ):
        """Response HTML contains hx-trigger='every 60s'."""
        response = await admin_client.get("/htmx/synthetic-history")
        assert response.status_code == 200
        assert 'hx-trigger="every 60s"' in response.text

    @pytest.mark.anyio
    @pytest.mark.usefixtures("_clean_synthetic_config")
    async def test_ac018_history_targets_itself(self, admin_client, db_session):
        """Response container targets itself for swap."""
        response = await admin_client.get("/htmx/synthetic-history")
        assert response.status_code == 200
        assert "synthetic-history-container" in response.text
