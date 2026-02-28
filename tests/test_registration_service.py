"""Tests for app.services.registration — register_user() business logic.

Covers: first user gets admin, subsequent users get viewer, duplicate username,
duplicate email, and RegistrationError properties.
"""

import pytest
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Session, SQLModel, create_engine

from app.services.auth import ROLE_ADMIN, ROLE_VIEWER
from app.services.registration import RegistrationError, register_user


@pytest.fixture(scope="module")
def sqlite_engine():
    """SQLite in-memory engine with user tables (JSONB -> JSON)."""
    for table in SQLModel.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, JSONB):
                col.type = JSON()

    engine = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture()
def session(sqlite_engine):
    """Per-test session that rolls back all changes."""
    connection = sqlite_engine.connect()
    transaction = connection.begin()
    sess = Session(bind=connection)
    yield sess
    sess.close()
    transaction.rollback()
    connection.close()


# ---------- RegistrationError ----------


class TestRegistrationError:
    def test_default_status_code(self):
        err = RegistrationError("duplicate")
        assert err.status_code == 409
        assert str(err) == "duplicate"

    def test_custom_status_code(self):
        err = RegistrationError("bad", status_code=400)
        assert err.status_code == 400


# ---------- First user (admin) ----------


class TestFirstUserRegistration:
    def test_first_user_gets_admin_role(self, session):
        user = register_user(
            session,
            username="admin_user",
            email="admin@example.com",
            password="StrongPass1!",
        )
        assert user.role == ROLE_ADMIN
        assert user.username == "admin_user"
        assert user.email == "admin@example.com"
        assert user.id is not None

    def test_first_user_password_is_hashed(self, session):
        user = register_user(
            session,
            username="hashcheck",
            email="hash@example.com",
            password="PlainText1!",
        )
        assert user.password_hash != "PlainText1!"
        assert len(user.password_hash) > 20  # bcrypt hashes are long


# ---------- Subsequent users (viewer) ----------


class TestSubsequentUserRegistration:
    def test_second_user_gets_viewer_role(self, session):
        # First user => admin
        register_user(
            session,
            username="first",
            email="first@example.com",
            password="Pass1!",
        )
        # Second user => viewer
        second = register_user(
            session,
            username="second",
            email="second@example.com",
            password="Pass2!",
        )
        assert second.role == ROLE_VIEWER

    def test_third_user_also_viewer(self, session):
        register_user(session, username="u1", email="u1@test.com", password="Pass1!")
        register_user(session, username="u2", email="u2@test.com", password="Pass2!")
        third = register_user(
            session, username="u3", email="u3@test.com", password="Pass3!"
        )
        assert third.role == ROLE_VIEWER


# ---------- Duplicate checks ----------


class TestDuplicateRegistration:
    def test_duplicate_username_raises(self, session):
        register_user(
            session,
            username="taken",
            email="original@test.com",
            password="Pass1!",
        )
        with pytest.raises(RegistrationError, match="Username already exists"):
            register_user(
                session,
                username="taken",
                email="different@test.com",
                password="Pass2!",
            )

    def test_duplicate_email_raises(self, session):
        register_user(
            session,
            username="unique_user",
            email="taken@test.com",
            password="Pass1!",
        )
        with pytest.raises(RegistrationError, match="Email already exists"):
            register_user(
                session,
                username="other_user",
                email="taken@test.com",
                password="Pass2!",
            )

    def test_duplicate_username_status_code_409(self, session):
        register_user(
            session,
            username="dup409",
            email="dup409@test.com",
            password="Pass1!",
        )
        with pytest.raises(RegistrationError) as exc_info:
            register_user(
                session,
                username="dup409",
                email="other409@test.com",
                password="Pass2!",
            )
        assert exc_info.value.status_code == 409
