"""Tests for user registration — AC-001, AC-002, AC-005, AC-015."""

import pytest
from httpx import AsyncClient
from sqlmodel import Session, select

from app.models.user import User
from app.services.auth import (
    ROLE_ADMIN,
    ROLE_OPERATOR,
    ROLE_VIEWER,
    hash_password,
    has_permission,
    role_at_least,
    verify_password,
)


class TestPasswordHashing:
    """AC-002: Passwords are hashed with bcrypt before storage."""

    def test_ac002_hash_password_returns_bcrypt_hash(self):
        """Hash should be a bcrypt string, not plaintext."""
        hashed = hash_password("SecurePass123!")
        assert hashed != "SecurePass123!"
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_ac002_verify_password_correct(self):
        """Correct password should verify."""
        hashed = hash_password("SecurePass123!")
        assert verify_password("SecurePass123!", hashed) is True

    def test_ac002_verify_password_incorrect(self):
        """Wrong password should not verify."""
        hashed = hash_password("SecurePass123!")
        assert verify_password("WrongPassword1!", hashed) is False

    def test_ac002_different_passwords_different_hashes(self):
        """Same password hashed twice should produce different hashes (salted)."""
        h1 = hash_password("SecurePass123!")
        h2 = hash_password("SecurePass123!")
        assert h1 != h2  # Different salts


class TestRoleConstants:
    """AC-005: Three roles exist with distinct permission sets."""

    def test_ac005_three_roles_defined(self):
        assert ROLE_ADMIN == "admin"
        assert ROLE_OPERATOR == "operator"
        assert ROLE_VIEWER == "viewer"

    def test_ac005_admin_has_all_permissions(self):
        """Admin should have every permission."""
        for perm in [
            "view_dashboard",
            "view_sync_logs",
            "submit_sync_logs",
            "view_webhooks",
            "manage_webhooks",
            "delete_sync_logs",
            "manage_users",
            "view_settings",
            "manage_own_api_keys",
            "manage_all_api_keys",
        ]:
            assert has_permission(ROLE_ADMIN, perm), f"Admin missing {perm}"

    def test_ac005_operator_permissions(self):
        """Operator can view and manage but not delete or manage users."""
        assert has_permission(ROLE_OPERATOR, "view_dashboard")
        assert has_permission(ROLE_OPERATOR, "submit_sync_logs")
        assert has_permission(ROLE_OPERATOR, "manage_webhooks")
        assert has_permission(ROLE_OPERATOR, "view_settings")
        assert not has_permission(ROLE_OPERATOR, "delete_sync_logs")
        assert not has_permission(ROLE_OPERATOR, "manage_users")
        assert not has_permission(ROLE_OPERATOR, "manage_all_api_keys")

    def test_ac005_viewer_read_only(self):
        """Viewer can only view and manage own API keys."""
        assert has_permission(ROLE_VIEWER, "view_dashboard")
        assert has_permission(ROLE_VIEWER, "view_sync_logs")
        assert has_permission(ROLE_VIEWER, "view_webhooks")
        assert has_permission(ROLE_VIEWER, "manage_own_api_keys")
        assert not has_permission(ROLE_VIEWER, "submit_sync_logs")
        assert not has_permission(ROLE_VIEWER, "manage_webhooks")
        assert not has_permission(ROLE_VIEWER, "delete_sync_logs")
        assert not has_permission(ROLE_VIEWER, "manage_users")

    def test_ac005_role_hierarchy(self):
        """Admin > Operator > Viewer."""
        assert role_at_least(ROLE_ADMIN, ROLE_ADMIN)
        assert role_at_least(ROLE_ADMIN, ROLE_OPERATOR)
        assert role_at_least(ROLE_ADMIN, ROLE_VIEWER)
        assert role_at_least(ROLE_OPERATOR, ROLE_OPERATOR)
        assert role_at_least(ROLE_OPERATOR, ROLE_VIEWER)
        assert not role_at_least(ROLE_OPERATOR, ROLE_ADMIN)
        assert role_at_least(ROLE_VIEWER, ROLE_VIEWER)
        assert not role_at_least(ROLE_VIEWER, ROLE_OPERATOR)
        assert not role_at_least(ROLE_VIEWER, ROLE_ADMIN)

    def test_ac005_unknown_role_has_no_permissions(self):
        """An invalid role should have no permissions."""
        assert not has_permission("hacker", "view_dashboard")
        assert not role_at_least("hacker", ROLE_VIEWER)


class TestRegistrationEndpoint:
    """AC-001: Users can register with username, email, and password."""

    @pytest.mark.asyncio
    async def test_ac001_register_valid_user(self, client: AsyncClient):
        """Registration with valid data returns 201 and user data."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert "password" not in data
        assert "password_hash" not in data
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_ac001_register_duplicate_username(self, client: AsyncClient):
        """Duplicate username returns 409."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "dupuser",
                "email": "first@example.com",
                "password": "SecurePass123!",
            },
        )
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "dupuser",
                "email": "second@example.com",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_ac001_register_duplicate_email(self, client: AsyncClient):
        """Duplicate email returns 409."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "user_one",
                "email": "same@example.com",
                "password": "SecurePass123!",
            },
        )
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "user_two",
                "email": "same@example.com",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_ac001_register_weak_password_no_uppercase(self, client: AsyncClient):
        """Password without uppercase returns 422."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "weakuser",
                "email": "weak@example.com",
                "password": "weakpass123!",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_ac001_register_weak_password_no_digit(self, client: AsyncClient):
        """Password without digit returns 422."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "weakuser",
                "email": "weak@example.com",
                "password": "WeakPassword!",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_ac001_register_short_password(self, client: AsyncClient):
        """Password under 8 chars returns 422."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "shortpw",
                "email": "short@example.com",
                "password": "Ab1!",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_ac001_register_invalid_email(self, client: AsyncClient):
        """Invalid email format returns 422."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "bademail",
                "email": "not-an-email",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_ac001_register_invalid_username_chars(self, client: AsyncClient):
        """Username with special chars returns 422."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "bad user!",
                "email": "badchars@example.com",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_ac001_register_short_username(self, client: AsyncClient):
        """Username under 3 chars returns 422."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "ab",
                "email": "short@example.com",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_ac001_email_normalized_lowercase(self, client: AsyncClient):
        """Email should be stored lowercase."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "casetest",
                "email": "Test@EXAMPLE.COM",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 201
        assert response.json()["email"] == "test@example.com"


class TestFirstUserAdmin:
    """AC-015: First registered user is automatically assigned the Admin role."""

    @pytest.mark.asyncio
    async def test_ac015_first_user_gets_admin(self, client: AsyncClient):
        """First registered user should be admin."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "firstadmin",
                "email": "admin@example.com",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 201
        assert response.json()["role"] == "admin"

    @pytest.mark.asyncio
    async def test_ac015_second_user_gets_viewer(self, client: AsyncClient):
        """Second registered user should be viewer."""
        # First user (admin)
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "admin_first",
                "email": "admin1@example.com",
                "password": "SecurePass123!",
            },
        )
        # Second user (viewer)
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "viewer_second",
                "email": "viewer@example.com",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 201
        assert response.json()["role"] == "viewer"

    @pytest.mark.asyncio
    async def test_ac015_third_user_also_viewer(self, client: AsyncClient):
        """Third+ registered user should also be viewer."""
        for i, name in enumerate(["admin_a", "viewer_b", "viewer_c"]):
            await client.post(
                "/api/v1/auth/register",
                json={
                    "username": name,
                    "email": f"{name}@example.com",
                    "password": "SecurePass123!",
                },
            )
        # Check third user
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "viewer_d",
                "email": "viewer_d@example.com",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 201
        assert response.json()["role"] == "viewer"


class TestUserModelStorage:
    """AC-002: Verify password is stored hashed, not plaintext."""

    @pytest.mark.asyncio
    async def test_ac002_password_not_stored_plaintext(
        self, client: AsyncClient, db_session: Session
    ):
        """Password hash in DB should not equal the plaintext password."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "hashcheck",
                "email": "hash@example.com",
                "password": "SecurePass123!",
            },
        )
        user = db_session.exec(select(User).where(User.username == "hashcheck")).first()
        assert user is not None
        assert user.password_hash != "SecurePass123!"
        assert user.password_hash.startswith("$2b$")
        assert verify_password("SecurePass123!", user.password_hash)
