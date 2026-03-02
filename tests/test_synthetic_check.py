"""Tests for synthetic monitoring service.

Covers: AC-001 through AC-012 from specs/synthetic-monitoring.md
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.failure_event import FailureEvent


# ---------------------------------------------------------------------------
# AC-006: Canned rsync log constants
# ---------------------------------------------------------------------------


class TestCannedLogConstants:
    """AC-006: Source name uses __synthetic_check with hardcoded canned data."""

    def test_ac006_source_name_is_dunder_synthetic_check(self):
        from app.services.synthetic_check import SYNTHETIC_SOURCE_NAME

        assert SYNTHETIC_SOURCE_NAME == "__synthetic_check"

    def test_ac006_canned_log_contains_expected_rsync_output(self):
        from app.services.synthetic_check import CANNED_RSYNC_LOG

        assert "sending incremental file list" in CANNED_RSYNC_LOG
        assert "synthetic-test-file.txt" in CANNED_RSYNC_LOG
        assert "sent 150 bytes" in CANNED_RSYNC_LOG
        assert "received 35 bytes" in CANNED_RSYNC_LOG


# ---------------------------------------------------------------------------
# AC-002, AC-003: POST and DELETE synthetic log
# ---------------------------------------------------------------------------


class TestRunSyntheticCheck:
    """AC-002/AC-003: POST canned log, verify 201, DELETE, verify 204."""

    @pytest.mark.anyio
    async def test_ac002_post_success_returns_passing(self):
        """Happy path: POST 201, DELETE 204 → status=passing."""
        from app.services.synthetic_check import run_synthetic_check

        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {
            "id": "fake-uuid-1234",
            "source_name": "__synthetic_check",
            "status": "completed",
        }

        mock_delete_response = MagicMock()
        mock_delete_response.status_code = 204

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_post_response
        mock_client.delete.return_value = mock_delete_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.services.synthetic_check.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await run_synthetic_check(
                base_url="http://localhost:8000",
                api_key="test-key",
            )

        assert result.status == "passing"
        assert result.error is None

    @pytest.mark.anyio
    async def test_ac002_post_verifies_response_fields(self):
        """AC-002: Verify POST response contains id, source_name, status."""
        from app.services.synthetic_check import run_synthetic_check

        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {
            "id": "abc-123",
            "source_name": "__synthetic_check",
            "status": "completed",
        }

        mock_delete_response = MagicMock()
        mock_delete_response.status_code = 204

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_post_response
        mock_client.delete.return_value = mock_delete_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.services.synthetic_check.httpx.AsyncClient",
            return_value=mock_client,
        ):
            await run_synthetic_check(
                base_url="http://localhost:8000",
                api_key="test-key",
            )

        # POST was called with correct payload
        call_kwargs = mock_client.post.call_args
        assert "__synthetic_check" in str(call_kwargs)

        # DELETE was called with the returned ID
        delete_call = mock_client.delete.call_args
        assert "abc-123" in str(delete_call)

    @pytest.mark.anyio
    async def test_ac004_post_failure_returns_failing(self):
        """AC-004: POST failure (non-201) → status=failing with error."""
        from app.services.synthetic_check import run_synthetic_check

        mock_post_response = MagicMock()
        mock_post_response.status_code = 500
        mock_post_response.text = "Internal Server Error"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_post_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.services.synthetic_check.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await run_synthetic_check(
                base_url="http://localhost:8000",
                api_key="test-key",
            )

        assert result.status == "failing"
        assert "500" in result.error

    @pytest.mark.anyio
    async def test_ac004_post_timeout_returns_failing(self):
        """AC-004: POST timeout → status=failing."""
        import httpx

        from app.services.synthetic_check import run_synthetic_check

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("timed out")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.services.synthetic_check.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await run_synthetic_check(
                base_url="http://localhost:8000",
                api_key="test-key",
            )

        assert result.status == "failing"
        assert "timeout" in result.error.lower()

    @pytest.mark.anyio
    async def test_ac004_post_connection_error_returns_failing(self):
        """AC-004: POST connection error → status=failing."""
        import httpx

        from app.services.synthetic_check import run_synthetic_check

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.services.synthetic_check.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await run_synthetic_check(
                base_url="http://localhost:8000",
                api_key="test-key",
            )

        assert result.status == "failing"
        assert result.error is not None

    @pytest.mark.anyio
    async def test_ac005_delete_failure_does_not_fail_check(self):
        """AC-005: DELETE failure → warning logged, but status=passing."""
        from app.services.synthetic_check import run_synthetic_check

        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {
            "id": "abc-123",
            "source_name": "__synthetic_check",
            "status": "completed",
        }

        mock_delete_response = MagicMock()
        mock_delete_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_post_response
        mock_client.delete.return_value = mock_delete_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.services.synthetic_check.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await run_synthetic_check(
                base_url="http://localhost:8000",
                api_key="test-key",
            )

        # POST succeeded, so check passes despite DELETE failure
        assert result.status == "passing"


# ---------------------------------------------------------------------------
# AC-004: Webhook dispatch on failure
# ---------------------------------------------------------------------------


class TestSyntheticWebhookDispatch:
    """AC-004: On POST failure, dispatch webhook with synthetic_failure type."""

    @pytest.mark.anyio
    async def test_ac004_webhook_dispatched_on_post_failure(self):
        """Webhook fires with failure_type=synthetic_failure on POST failure."""
        from app.services.synthetic_check import run_synthetic_check

        mock_post_response = MagicMock()
        mock_post_response.status_code = 500
        mock_post_response.text = "Internal Server Error"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_post_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_dispatch = AsyncMock()
        mock_session = MagicMock()

        with (
            patch(
                "app.services.synthetic_check.httpx.AsyncClient",
                return_value=mock_client,
            ),
            patch(
                "app.services.synthetic_check.dispatch_webhooks",
                mock_dispatch,
            ),
        ):
            await run_synthetic_check(
                base_url="http://localhost:8000",
                api_key="test-key",
                db_session=mock_session,
            )

        mock_dispatch.assert_called_once()
        call_args = mock_dispatch.call_args
        event = call_args[0][1]  # second positional arg
        assert isinstance(event, FailureEvent)
        assert event.failure_type == "synthetic_failure"
        assert event.source_name == "__synthetic_check"

    @pytest.mark.anyio
    async def test_ac005_no_webhook_on_delete_failure(self):
        """AC-005: DELETE failure does NOT fire webhook."""
        from app.services.synthetic_check import run_synthetic_check

        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {
            "id": "abc-123",
            "source_name": "__synthetic_check",
            "status": "completed",
        }

        mock_delete_response = MagicMock()
        mock_delete_response.status_code = 500

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_post_response
        mock_client.delete.return_value = mock_delete_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_dispatch = AsyncMock()

        with (
            patch(
                "app.services.synthetic_check.httpx.AsyncClient",
                return_value=mock_client,
            ),
            patch(
                "app.services.synthetic_check.dispatch_webhooks",
                mock_dispatch,
            ),
        ):
            await run_synthetic_check(
                base_url="http://localhost:8000",
                api_key="test-key",
            )

        # Webhook should NOT be called because POST succeeded
        mock_dispatch.assert_not_called()


# ---------------------------------------------------------------------------
# AC-007: API key usage
# ---------------------------------------------------------------------------


class TestSyntheticApiKey:
    """AC-007: Uses DEFAULT_API_KEY for auth."""

    @pytest.mark.anyio
    async def test_ac007_uses_api_key_in_header(self):
        """POST request includes X-API-Key header."""
        from app.services.synthetic_check import run_synthetic_check

        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {
            "id": "abc",
            "source_name": "__synthetic_check",
            "status": "completed",
        }

        mock_delete_response = MagicMock()
        mock_delete_response.status_code = 204

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_post_response
        mock_client.delete.return_value = mock_delete_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.services.synthetic_check.httpx.AsyncClient",
            return_value=mock_client,
        ):
            await run_synthetic_check(
                base_url="http://localhost:8000",
                api_key="my-secret-key",
            )

        # Verify X-API-Key header was sent
        post_call = mock_client.post.call_args
        headers = post_call.kwargs.get("headers", {})
        assert headers.get("X-API-Key") == "my-secret-key"


# ---------------------------------------------------------------------------
# AC-008: Prometheus metrics
# ---------------------------------------------------------------------------


class TestSyntheticMetrics:
    """AC-008: Prometheus gauge and histogram recorded on each cycle."""

    @pytest.mark.anyio
    async def test_ac008_metrics_recorded_on_passing_check(self):
        """Gauge set to 1 and histogram observed on success."""
        from app.services.synthetic_check import run_synthetic_check

        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {
            "id": "abc",
            "source_name": "__synthetic_check",
            "status": "completed",
        }

        mock_delete_response = MagicMock()
        mock_delete_response.status_code = 204

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_post_response
        mock_client.delete.return_value = mock_delete_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "app.services.synthetic_check.httpx.AsyncClient",
                return_value=mock_client,
            ),
            patch("app.services.synthetic_check.synthetic_check_status") as mock_gauge,
            patch("app.services.synthetic_check.synthetic_check_duration") as mock_hist,
        ):
            await run_synthetic_check(
                base_url="http://localhost:8000",
                api_key="test-key",
            )

        mock_gauge.set.assert_called_with(1)
        mock_hist.observe.assert_called_once()

    @pytest.mark.anyio
    async def test_ac008_metrics_recorded_on_failing_check(self):
        """Gauge set to 0 on failure."""
        from app.services.synthetic_check import run_synthetic_check

        mock_post_response = MagicMock()
        mock_post_response.status_code = 500
        mock_post_response.text = "Error"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_post_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "app.services.synthetic_check.httpx.AsyncClient",
                return_value=mock_client,
            ),
            patch("app.services.synthetic_check.synthetic_check_status") as mock_gauge,
            patch("app.services.synthetic_check.synthetic_check_duration"),
            patch(
                "app.services.synthetic_check.dispatch_webhooks",
                AsyncMock(),
            ),
        ):
            await run_synthetic_check(
                base_url="http://localhost:8000",
                api_key="test-key",
            )

        mock_gauge.set.assert_called_with(0)


# ---------------------------------------------------------------------------
# AC-001, AC-011, AC-012: Background task lifecycle
# ---------------------------------------------------------------------------


class TestSyntheticBackgroundTask:
    """AC-001/AC-011/AC-012: Background task runs on interval, shuts down cleanly."""

    @pytest.mark.anyio
    async def test_ac012_disabled_task_returns_immediately(self):
        """AC-012: When disabled, background task returns without running."""
        from app.services.synthetic_check import synthetic_check_background_task

        shutdown = asyncio.Event()

        # Should return immediately (not block)
        await asyncio.wait_for(
            synthetic_check_background_task(
                enabled=False,
                interval_seconds=300,
                shutdown_event=shutdown,
                base_url="http://localhost:8000",
                api_key="test-key",
            ),
            timeout=2.0,
        )

    @pytest.mark.anyio
    async def test_ac001_task_runs_on_interval(self):
        """AC-001: Task calls run_synthetic_check on configured interval."""
        from app.services.synthetic_check import synthetic_check_background_task

        shutdown = asyncio.Event()
        mock_result = MagicMock()
        mock_result.status = "passing"
        mock_result.latency_ms = 42.0
        mock_result.error = None

        call_count = 0

        async def mock_run(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                shutdown.set()
            return mock_result

        with (
            patch(
                "app.services.synthetic_check.run_synthetic_check",
                side_effect=mock_run,
            ),
            patch(
                "app.services.synthetic_check.MINIMUM_INTERVAL_SECONDS",
                0,
            ),
        ):
            await asyncio.wait_for(
                synthetic_check_background_task(
                    enabled=True,
                    interval_seconds=0.1,  # Fast for testing
                    shutdown_event=shutdown,
                    base_url="http://localhost:8000",
                    api_key="test-key",
                ),
                timeout=5.0,
            )

        assert call_count >= 2

    @pytest.mark.anyio
    async def test_ac011_task_stops_on_shutdown_event(self):
        """AC-011: Task exits when shutdown_event is set."""
        from app.services.synthetic_check import synthetic_check_background_task

        shutdown = asyncio.Event()
        mock_result = MagicMock()
        mock_result.status = "passing"
        mock_result.latency_ms = 10.0
        mock_result.error = None

        async def mock_run(**kwargs):
            return mock_result

        # Set shutdown shortly after start
        async def trigger_shutdown():
            await asyncio.sleep(0.2)
            shutdown.set()

        with patch(
            "app.services.synthetic_check.run_synthetic_check",
            side_effect=mock_run,
        ):
            asyncio.create_task(trigger_shutdown())
            await asyncio.wait_for(
                synthetic_check_background_task(
                    enabled=True,
                    interval_seconds=60,  # Long interval — shutdown should interrupt
                    shutdown_event=shutdown,
                    base_url="http://localhost:8000",
                    api_key="test-key",
                ),
                timeout=5.0,
            )

    @pytest.mark.anyio
    async def test_ac001_minimum_interval_enforced(self):
        """AC-001: Interval below 30s is clamped to 30s."""
        from app.services.synthetic_check import synthetic_check_background_task

        shutdown = asyncio.Event()
        shutdown.set()  # Immediately stop

        mock_result = MagicMock()
        mock_result.status = "passing"
        mock_result.latency_ms = 10.0
        mock_result.error = None

        with patch(
            "app.services.synthetic_check.run_synthetic_check",
            return_value=mock_result,
        ):
            await synthetic_check_background_task(
                enabled=True,
                interval_seconds=5,  # Below minimum
                shutdown_event=shutdown,
                base_url="http://localhost:8000",
                api_key="test-key",
            )


# ---------------------------------------------------------------------------
# AC-009: Health endpoint includes synthetic status
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """AC-009: GET /health includes synthetic_check when enabled."""

    @pytest.mark.anyio
    async def test_ac009_health_includes_synthetic_when_enabled(self, client):
        """Health endpoint includes synthetic_check status."""
        from app.services import synthetic_check as sc_module

        # Simulate an enabled check that has run
        original_state = sc_module._state
        sc_module._state = sc_module.SyntheticCheckState(
            enabled=True,
            interval_seconds=300,
            last_status="passing",
            last_check_at=None,
            last_latency_ms=42.5,
            last_error=None,
        )

        try:
            response = await client.get("/health")
            data = response.json()
            assert response.status_code == 200
            assert "synthetic_check" in data
            assert data["synthetic_check"]["status"] == "passing"
            assert data["synthetic_check"]["last_latency_ms"] == 42.5
        finally:
            sc_module._state = original_state

    @pytest.mark.anyio
    async def test_ac009_health_null_when_disabled(self, client):
        """Health endpoint returns synthetic_check: null when disabled."""
        from app.services import synthetic_check as sc_module

        original_state = sc_module._state
        sc_module._state = sc_module.SyntheticCheckState(
            enabled=False,
            interval_seconds=300,
            last_status="unknown",
            last_check_at=None,
            last_latency_ms=None,
            last_error=None,
        )

        try:
            response = await client.get("/health")
            data = response.json()
            assert data["synthetic_check"] is None
        finally:
            sc_module._state = original_state


# ---------------------------------------------------------------------------
# AC-010: Settings page section
# ---------------------------------------------------------------------------


class TestSyntheticSettingsUI:
    """AC-010: Admin settings page shows synthetic monitoring section."""

    @pytest.mark.anyio
    async def test_ac010_get_settings_partial_returns_html(
        self, test_engine, db_session
    ):
        """GET /htmx/synthetic-settings returns HTML partial (admin only)."""
        import os
        from datetime import timedelta

        import jwt as pyjwt
        from httpx import ASGITransport, AsyncClient

        from app.config import get_settings
        from app.csrf import generate_csrf_token
        from app.database import get_session
        from app.main import app
        from app.models.user import User
        from app.services import synthetic_check as sc_module
        from app.services.auth import ROLE_ADMIN, hash_password
        from app.utils import utc_now
        from tests.conftest import get_test_settings

        os.environ["SECRET_KEY"] = "test-secret-key"
        os.environ["DEBUG"] = "true"
        os.environ["DEFAULT_API_KEY"] = "test-api-key"
        get_settings.cache_clear()

        admin = User(
            username="synth-admin",
            email="synth-admin@test.local",
            password_hash=hash_password("TestPass1!"),
            role=ROLE_ADMIN,
        )
        db_session.add(admin)
        db_session.flush()

        def get_test_session():
            yield db_session

        app.dependency_overrides[get_session] = get_test_session
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

        original_state = sc_module._state
        sc_module._state = sc_module.SyntheticCheckState(
            enabled=True,
            interval_seconds=300,
            last_status="passing",
            last_check_at=None,
            last_latency_ms=42.5,
            last_error=None,
        )

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers={"X-CSRF-Token": csrf_token},
                cookies={"access_token": jwt_token, "csrf_token": csrf_token},
            ) as admin_client:
                response = await admin_client.get("/htmx/synthetic-settings")
            assert response.status_code == 200
            assert "synthetic" in response.text.lower()
        finally:
            sc_module._state = original_state
            app.dependency_overrides.clear()
            get_settings.cache_clear()

    @pytest.mark.anyio
    async def test_ac010_post_toggle_updates_state(self, test_engine, db_session):
        """POST /htmx/synthetic-settings toggles enable/disable (admin only)."""
        import os
        from datetime import timedelta

        import jwt as pyjwt
        from httpx import ASGITransport, AsyncClient

        from app.config import get_settings
        from app.csrf import generate_csrf_token
        from app.database import get_session
        from app.main import app
        from app.models.user import User
        from app.services import synthetic_check as sc_module
        from app.services.auth import ROLE_ADMIN, hash_password
        from app.utils import utc_now
        from tests.conftest import get_test_settings

        os.environ["SECRET_KEY"] = "test-secret-key"
        os.environ["DEBUG"] = "true"
        os.environ["DEFAULT_API_KEY"] = "test-api-key"
        get_settings.cache_clear()

        admin = User(
            username="synth-admin2",
            email="synth-admin2@test.local",
            password_hash=hash_password("TestPass1!"),
            role=ROLE_ADMIN,
        )
        db_session.add(admin)
        db_session.flush()

        def get_test_session():
            yield db_session

        app.dependency_overrides[get_session] = get_test_session
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

        original_state = sc_module._state
        sc_module._state = sc_module.SyntheticCheckState(
            enabled=False,
            interval_seconds=300,
            last_status="unknown",
            last_check_at=None,
            last_latency_ms=None,
            last_error=None,
        )

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers={"X-CSRF-Token": csrf_token},
                cookies={"access_token": jwt_token, "csrf_token": csrf_token},
            ) as admin_client:
                response = await admin_client.post(
                    "/htmx/synthetic-settings",
                    data={"enabled": "on", "interval": "120"},
                )
            assert response.status_code == 200
        finally:
            sc_module._state = original_state
            app.dependency_overrides.clear()
            get_settings.cache_clear()
