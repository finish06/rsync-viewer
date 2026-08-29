"""Tests for specs/insight-ui.md — C1 backend API.

Covers:
  AC-002: GET /api/v1/synthetic/status
  AC-003: GET /api/v1/synthetic/history
  AC-005: GET /api/v1/sources/health
"""

from datetime import timedelta

import pytest
from sqlmodel import Session, select

from app.models.monitor import SyncSourceMonitor
from app.models.synthetic_check_config import SyntheticCheckConfig
from app.models.synthetic_check_result import SyntheticCheckResultRecord
from app.models.user import User
from app.services.auth import ROLE_VIEWER, hash_password
from app.services.synthetic_check import SYNTHETIC_SOURCE_NAME
from app.utils import utc_now
from tests.test_rbac import _make_bearer_client, _make_unauth_client


@pytest.fixture
def clean_synthetic(db_session: Session):
    """Remove synthetic config/result rows so each test starts from nothing."""
    for model in (SyntheticCheckResultRecord, SyntheticCheckConfig):
        for row in db_session.exec(select(model)).all():
            db_session.delete(row)
    db_session.commit()


@pytest.fixture
def viewer_user(db_session: Session) -> User:
    user = User(
        username="insight_viewer",
        email="insight_viewer@test.com",
        password_hash=hash_password("ViewPass1!"),
        role=ROLE_VIEWER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _seed_results(db_session: Session, statuses: list[str], minutes_apart: int = 5):
    """Insert results oldest→newest; the last status is the most recent."""
    now = utc_now()
    rows = []
    for i, status in enumerate(statuses):
        row = SyntheticCheckResultRecord(
            checked_at=now - timedelta(minutes=minutes_apart * (len(statuses) - i)),
            status=status,
            latency_ms=100.0 + i,
            error=None if status == "passing" else f"boom {i}",
        )
        db_session.add(row)
        rows.append(row)
    db_session.commit()
    return rows


class TestAC002SyntheticStatus:
    @pytest.mark.usefixtures("clean_synthetic")
    async def test_ac002_status_disabled_when_no_data(self, client):
        resp = await client.get("/api/v1/synthetic/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["enabled"] is False
        assert body["status"] == "disabled"
        assert body["uptime_24h_pct"] is None
        assert body["checks_24h"] == 0

    @pytest.mark.usefixtures("clean_synthetic")
    async def test_ac002_status_reflects_config_and_results(self, client, db_session):
        db_session.add(SyntheticCheckConfig(id=1, enabled=True, interval_seconds=120))
        db_session.commit()
        rows = _seed_results(db_session, ["passing"] * 9 + ["failing"])

        resp = await client.get("/api/v1/synthetic/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["enabled"] is True
        assert body["interval_seconds"] == 120
        assert body["status"] == "failing"  # most recent result
        assert body["uptime_24h_pct"] == 90.0
        assert body["uptime_7d_pct"] == 90.0
        assert body["checks_24h"] == 10
        assert body["last_latency_ms"] == rows[-1].latency_ms
        assert body["last_check_at"] is not None

    async def test_ac002_requires_auth(self, db_session, viewer_user):
        assert (
            await _make_unauth_client(db_session).get("/api/v1/synthetic/status")
        ).status_code == 401
        assert (
            await _make_bearer_client(db_session, viewer_user).get(
                "/api/v1/synthetic/status"
            )
        ).status_code == 200


class TestAC003SyntheticHistory:
    @pytest.mark.usefixtures("clean_synthetic")
    async def test_ac003_history_newest_first_with_limit(self, client, db_session):
        _seed_results(
            db_session, ["passing", "failing", "passing", "passing", "failing"]
        )

        resp = await client.get("/api/v1/synthetic/history?limit=3")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 3
        assert items[0]["status"] == "failing"
        assert items[0]["error"] == "boom 4"
        checked = [i["checked_at"] for i in items]
        assert checked == sorted(checked, reverse=True)
        assert set(items[0]) == {"checked_at", "status", "latency_ms", "error"}

    @pytest.mark.usefixtures("clean_synthetic")
    async def test_ac003_history_default_and_bounds(self, client, db_session):
        _seed_results(db_session, ["passing"] * 3)
        assert len((await client.get("/api/v1/synthetic/history")).json()) == 3
        assert (
            await client.get("/api/v1/synthetic/history?limit=0")
        ).status_code == 422
        assert (
            await client.get("/api/v1/synthetic/history?limit=501")
        ).status_code == 422


class TestAC005SourcesHealth:
    async def test_ac005_health_per_source_with_daily_series(
        self, client, create_sync_log, db_session
    ):
        now = utc_now()
        create_sync_log(source_name="movies", bytes_received=1000, exit_code=0)
        create_sync_log(source_name="movies", bytes_received=500, exit_code=0)
        create_sync_log(
            source_name="nas",
            start_time=now - timedelta(days=1, minutes=5),
            end_time=now - timedelta(days=1),
            bytes_received=10,
            exit_code=0,
        )
        create_sync_log(source_name="nas", bytes_received=0, exit_code=12)
        create_sync_log(source_name="dry-only", is_dry_run=True)
        create_sync_log(source_name=SYNTHETIC_SOURCE_NAME)

        resp = await client.get("/api/v1/sources/health")
        assert resp.status_code == 200
        by_name = {s["source_name"]: s for s in resp.json()}
        assert set(by_name) == {"movies", "nas"}

        movies = by_name["movies"]
        assert movies["last_status"] == "ok"
        assert movies["last_exit_code"] == 0
        assert movies["consecutive_failures"] == 0
        assert movies["expected_interval_hours"] is None
        assert movies["is_stale"] is False
        assert len(movies["daily"]) == 14
        dates = [d["date"] for d in movies["daily"]]
        assert dates == sorted(dates)
        today = movies["daily"][-1]
        assert today["syncs"] == 2
        assert today["failures"] == 0
        assert today["bytes"] == 1500

        nas = by_name["nas"]
        assert nas["last_status"] == "failed"
        assert nas["last_exit_code"] == 12
        assert nas["consecutive_failures"] == 1
        assert nas["daily"][-1]["failures"] == 1
        assert nas["daily"][-2]["syncs"] == 1

    async def test_ac005_stale_from_monitor_and_never_synced(
        self, client, create_sync_log, db_session
    ):
        now = utc_now()
        create_sync_log(
            source_name="backup",
            start_time=now - timedelta(hours=3, minutes=5),
            end_time=now - timedelta(hours=3),
        )
        db_session.add(
            SyncSourceMonitor(
                source_name="backup",
                expected_interval_hours=1,
                grace_multiplier=1.5,
                last_sync_at=now - timedelta(hours=3),
            )
        )
        db_session.add(
            SyncSourceMonitor(source_name="ghost", expected_interval_hours=24)
        )
        db_session.commit()

        by_name = {
            s["source_name"]: s
            for s in (await client.get("/api/v1/sources/health")).json()
        }
        assert by_name["backup"]["is_stale"] is True
        assert by_name["backup"]["expected_interval_hours"] == 1
        assert by_name["ghost"]["last_status"] == "never"
        assert by_name["ghost"]["last_sync_at"] is None
        assert by_name["ghost"]["is_stale"] is False

    async def test_ac005_days_param_and_auth(
        self, db_session, viewer_user, create_sync_log
    ):
        create_sync_log(source_name="movies")
        assert (
            await _make_unauth_client(db_session).get("/api/v1/sources/health")
        ).status_code == 401
        resp = await _make_bearer_client(db_session, viewer_user).get(
            "/api/v1/sources/health?days=7"
        )
        assert resp.status_code == 200
        assert len(resp.json()[0]["daily"]) == 7
        assert (
            await _make_bearer_client(db_session, viewer_user).get(
                "/api/v1/sources/health?days=0"
            )
        ).status_code == 422
