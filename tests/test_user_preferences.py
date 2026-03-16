"""Tests for user preferences (specs/user-preferences.md).

Covers: AC-001 through AC-012.
"""

import os
from datetime import timedelta

import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session

from app.config import get_settings
from app.database import get_session
from app.main import app
from app.models.user import User
from app.services.auth import ROLE_VIEWER, hash_password
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


def _setup(db_session: Session, role: str = ROLE_VIEWER) -> tuple:
    """Create a user and return (user, AsyncClient)."""
    from app.csrf import generate_csrf_token
    from tests.conftest import get_test_settings

    os.environ["SECRET_KEY"] = _TEST_SECRET
    os.environ["DEBUG"] = "true"
    os.environ["DEFAULT_API_KEY"] = "test-api-key"
    get_settings.cache_clear()

    user = User(
        username="prefuser",
        email="prefuser@test.local",
        password_hash=hash_password("TestPass1!"),
        role=role,
    )
    db_session.add(user)
    db_session.flush()

    def get_test_session():
        yield db_session

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_settings] = get_test_settings

    csrf = generate_csrf_token()
    jwt_token = _make_jwt(str(user.id), user.username, user.role)

    client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-CSRF-Token": csrf},
        cookies={"csrf_token": csrf, "access_token": jwt_token},
    )
    return user, client


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.clear()
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# AC-001: User model has preferences JSON column with default {}
# ---------------------------------------------------------------------------


class TestAC001PreferencesColumn:
    def test_ac001_user_has_preferences_field(self, db_session: Session):
        """User model has a preferences attribute."""
        user = User(
            username="ac001user",
            email="ac001@test.local",
            password_hash=hash_password("TestPass1!"),
            role=ROLE_VIEWER,
        )
        db_session.add(user)
        db_session.flush()

        assert hasattr(user, "preferences")

    def test_ac001_preferences_default_empty_dict(self, db_session: Session):
        """New users get empty dict as default preferences."""
        user = User(
            username="ac001def",
            email="ac001def@test.local",
            password_hash=hash_password("TestPass1!"),
            role=ROLE_VIEWER,
        )
        db_session.add(user)
        db_session.flush()
        db_session.refresh(user)

        prefs = user.preferences
        assert prefs is not None
        assert isinstance(prefs, dict)
        assert prefs == {}


# ---------------------------------------------------------------------------
# AC-002: Preferences stores theme with valid values
# ---------------------------------------------------------------------------


class TestAC002ThemeStorage:
    def test_ac002_store_theme_preference(self, db_session: Session):
        """Can store theme in preferences JSON."""
        user = User(
            username="ac002user",
            email="ac002@test.local",
            password_hash=hash_password("TestPass1!"),
            role=ROLE_VIEWER,
            preferences={"theme": "dark"},
        )
        db_session.add(user)
        db_session.flush()
        db_session.refresh(user)

        assert user.preferences["theme"] == "dark"


# ---------------------------------------------------------------------------
# AC-003: PATCH /api/v1/users/me/preferences merges partial JSON
# ---------------------------------------------------------------------------


class TestAC003PatchPreferences:
    @pytest.mark.asyncio
    async def test_ac003_patch_sets_theme(self, db_session: Session):
        """PATCH merges theme into preferences."""
        user, client = _setup(db_session)
        async with client:
            resp = await client.patch(
                "/api/v1/users/me/preferences",
                json={"theme": "dark"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["theme"] == "dark"

    @pytest.mark.asyncio
    async def test_ac003_patch_merges_not_replaces(self, db_session: Session):
        """PATCH merges into existing preferences, doesn't replace."""
        user, client = _setup(db_session)
        user.preferences = {"theme": "light"}
        db_session.flush()

        async with client:
            resp = await client.patch(
                "/api/v1/users/me/preferences",
                json={"theme": "dark"},
            )
        assert resp.status_code == 200
        assert resp.json()["theme"] == "dark"

    @pytest.mark.asyncio
    async def test_ac003_empty_patch_returns_current(self, db_session: Session):
        """Empty PATCH body returns current preferences unchanged."""
        user, client = _setup(db_session)
        user.preferences = {"theme": "dark"}
        db_session.flush()

        async with client:
            resp = await client.patch(
                "/api/v1/users/me/preferences",
                json={},
            )
        assert resp.status_code == 200
        assert resp.json()["theme"] == "dark"


# ---------------------------------------------------------------------------
# AC-004: GET /api/v1/users/me/preferences returns full preferences
# ---------------------------------------------------------------------------


class TestAC004GetPreferences:
    @pytest.mark.asyncio
    async def test_ac004_get_returns_preferences(self, db_session: Session):
        """GET returns user's full preferences object."""
        user, client = _setup(db_session)
        user.preferences = {"theme": "dark"}
        db_session.flush()

        async with client:
            resp = await client.get("/api/v1/users/me/preferences")
        assert resp.status_code == 200
        assert resp.json() == {"theme": "dark"}

    @pytest.mark.asyncio
    async def test_ac004_get_returns_empty_for_new_user(self, db_session: Session):
        """GET returns {} for user with no preferences set."""
        user, client = _setup(db_session)
        async with client:
            resp = await client.get("/api/v1/users/me/preferences")
        assert resp.status_code == 200
        assert resp.json() == {}


# ---------------------------------------------------------------------------
# AC-005: Server injects theme into base.html <head>
# ---------------------------------------------------------------------------


class TestAC005ServerInjection:
    @pytest.mark.asyncio
    async def test_ac005_base_html_contains_user_theme(self, db_session: Session):
        """Dashboard page injects __USER_THEME__ for logged-in user with theme pref."""
        user, client = _setup(db_session)
        user.preferences = {"theme": "dark"}
        db_session.flush()

        async with client:
            resp = await client.get("/")
        assert resp.status_code == 200
        body = resp.text
        assert "__USER_THEME__" in body
        assert "dark" in body


# ---------------------------------------------------------------------------
# AC-006: Server theme overrides localStorage
# ---------------------------------------------------------------------------


class TestAC006ServerOverridesLocalStorage:
    @pytest.mark.asyncio
    async def test_ac006_server_theme_set_before_localstorage(
        self, db_session: Session
    ):
        """The inline script reads __USER_THEME__ before localStorage."""
        user, client = _setup(db_session)
        user.preferences = {"theme": "light"}
        db_session.flush()

        async with client:
            resp = await client.get("/")
        body = resp.text
        # __USER_THEME__ should appear before localStorage.getItem in the script
        theme_pos = body.find("__USER_THEME__")
        local_pos = body.find("localStorage.getItem")
        assert theme_pos > 0
        assert local_pos > 0
        assert theme_pos < local_pos


# ---------------------------------------------------------------------------
# AC-009: Unauthenticated users use localStorage only
# ---------------------------------------------------------------------------


class TestAC009UnauthLocalStorageOnly:
    @pytest.mark.asyncio
    async def test_ac009_login_page_no_user_theme(self, db_session: Session):
        """Login page (unauthenticated) does not inject __USER_THEME__."""
        from tests.conftest import get_test_settings

        os.environ["SECRET_KEY"] = _TEST_SECRET
        os.environ["DEBUG"] = "true"
        get_settings.cache_clear()

        def get_test_session():
            yield db_session

        app.dependency_overrides[get_session] = get_test_session
        app.dependency_overrides[get_settings] = get_test_settings

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/login")
        assert resp.status_code == 200
        assert "__USER_THEME__" not in resp.text


# ---------------------------------------------------------------------------
# AC-010: Preferences API requires authentication
# ---------------------------------------------------------------------------


class TestAC010AuthRequired:
    @pytest.mark.asyncio
    async def test_ac010_get_preferences_requires_auth(
        self, db_session: Session, unauth_client: AsyncClient
    ):
        """GET /api/v1/users/me/preferences returns 401 without auth."""
        resp = await unauth_client.get("/api/v1/users/me/preferences")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_ac010_patch_preferences_requires_auth(
        self, db_session: Session, unauth_client: AsyncClient
    ):
        """PATCH /api/v1/users/me/preferences returns 401 without auth."""
        resp = await unauth_client.patch(
            "/api/v1/users/me/preferences",
            json={"theme": "dark"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_ac010_any_role_can_access(self, db_session: Session):
        """Viewer role (lowest) can access preferences endpoints."""
        user, client = _setup(db_session, role=ROLE_VIEWER)
        async with client:
            resp = await client.get("/api/v1/users/me/preferences")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# AC-011: Invalid preference values return 422
# ---------------------------------------------------------------------------


class TestAC011Validation:
    @pytest.mark.asyncio
    async def test_ac011_invalid_theme_value_rejected(self, db_session: Session):
        """Theme value 'rainbow' returns 422."""
        user, client = _setup(db_session)
        async with client:
            resp = await client.patch(
                "/api/v1/users/me/preferences",
                json={"theme": "rainbow"},
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_ac011_unknown_keys_ignored(self, db_session: Session):
        """Unknown keys in PATCH body are silently dropped."""
        user, client = _setup(db_session)
        async with client:
            resp = await client.patch(
                "/api/v1/users/me/preferences",
                json={"theme": "dark", "unknown_key": "value"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "unknown_key" not in data
        assert data["theme"] == "dark"


# ---------------------------------------------------------------------------
# AC-012: Alembic migration adds the preferences column
# ---------------------------------------------------------------------------


class TestAC012AlembicMigration:
    def test_ac012_migration_file_exists(self):
        """An Alembic migration for preferences exists."""
        import glob

        migrations = glob.glob("alembic/versions/*preferences*.py")
        assert len(migrations) >= 1, "No Alembic migration for preferences found"
