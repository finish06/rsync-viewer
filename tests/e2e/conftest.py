"""Shared Playwright E2E fixtures.

Provides authenticated browser contexts, test user creation, and API helpers.
Runs against a live instance at http://localhost:8000 (override via E2E_BASE_URL).

Usage:
    docker-compose up -d
    python3 -m pytest tests/e2e/ -v
"""

import os
import uuid
from datetime import datetime, timezone

import pytest
import requests
from playwright.sync_api import Browser, BrowserContext, Page

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")
# Dev API key set in docker-compose.yml — used for data ingestion and user promotion
DEV_API_KEY = os.environ.get("E2E_DEV_API_KEY", "rsv_dev_key_12345")


def _unique_id() -> str:
    return uuid.uuid4().hex[:8]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# User creation helpers
# ---------------------------------------------------------------------------


def register_user_via_api(
    username: str, email: str, password: str
) -> requests.Response:
    """Register a user via the REST API."""
    return requests.post(
        f"{BASE_URL}/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
        timeout=10,
    )


def login_via_api(username: str, password: str) -> dict:
    """Login via REST API and return token data."""
    resp = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def create_api_key_via_api(access_token: str, name: str) -> dict:
    """Create an API key via REST API, return {key, id, prefix}."""
    resp = requests.post(
        f"{BASE_URL}/api/v1/api-keys",
        json={"name": name},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def promote_user_to_admin(user_id: str) -> None:
    """Promote a user to admin role via direct DB update.

    The REST API requires an existing admin JWT to change roles, creating
    a chicken-and-egg problem for test setup. Since we control the Docker
    Compose stack, a direct DB update is the pragmatic approach.
    """
    import subprocess

    subprocess.run(
        [
            "docker",
            "exec",
            "rsync-viewer-db",
            "psql",
            "-U",
            "postgres",
            "-d",
            "rsync_viewer",
            "-c",
            f"UPDATE users SET role = 'admin' WHERE id = '{user_id}';",
        ],
        check=True,
        capture_output=True,
        timeout=10,
    )


def ingest_sync_log(api_key: str, source_name: str) -> dict:
    """POST a realistic sync log via API. Returns the created log."""
    now = _utc_now()
    raw_content = (
        "sending incremental file list\n"
        "test-file.txt\n"
        "\n"
        "Number of files: 10 (reg: 8, dir: 2)\n"
        "Number of created files: 1\n"
        "Number of deleted files: 0\n"
        "Number of regular files transferred: 1\n"
        "Total file size: 1,024 bytes\n"
        "Total transferred file size: 512 bytes\n"
        "Literal data: 512 bytes\n"
        "Matched data: 0 bytes\n"
        "File list size: 0\n"
        "File list generation time: 0.001 seconds\n"
        "File list transfer time: 0.000 seconds\n"
        "Total bytes sent: 620\n"
        "Total bytes received: 45\n"
        "\n"
        "sent 620 bytes  received 45 bytes  1,330.00 bytes/sec\n"
        "total size is 1,024  speedup is 1.54\n"
    )
    resp = requests.post(
        f"{BASE_URL}/api/v1/sync-logs",
        json={
            "source_name": source_name,
            "start_time": now,
            "end_time": now,
            "raw_content": raw_content,
            "exit_code": 0,
        },
        headers={"X-API-Key": api_key},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Fixtures — session-scoped (shared across all tests in a session)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def admin_credentials() -> dict:
    """Register a user and ensure they have admin role.

    Strategy:
    1. Register a new user via API
    2. Log in to get a JWT
    3. Try to promote via dev API key
    4. If the user is already admin (first user), this is a no-op
    """
    uid = _unique_id()
    creds = {
        "username": f"e2e_admin_{uid}",
        "email": f"e2e_admin_{uid}@test.local",
        "password": "AdminPass123!",
    }
    resp = register_user_via_api(creds["username"], creds["email"], creds["password"])
    assert resp.status_code in (200, 201), (
        f"Admin registration failed ({resp.status_code}): {resp.text}"
    )
    user_data = resp.json()
    user_id = user_data["id"]

    # If user is already admin (first user), great. Otherwise promote.
    if user_data.get("role") != "admin":
        promote_user_to_admin(user_id)

    creds["id"] = user_id
    return creds


@pytest.fixture(scope="session")
def admin_token(admin_credentials) -> str:
    """Get a JWT access token for the admin user."""
    data = login_via_api(admin_credentials["username"], admin_credentials["password"])
    return data["access_token"]


@pytest.fixture(scope="session")
def admin_api_key(admin_token) -> str:
    """Create an API key for ingesting test data.

    Falls back to DEV_API_KEY if the user can't create keys (not admin).
    """
    try:
        data = create_api_key_via_api(admin_token, f"e2e-ingest-{_unique_id()}")
        return data["key"]
    except requests.HTTPError:
        return DEV_API_KEY


@pytest.fixture(scope="session")
def viewer_credentials(admin_credentials) -> dict:
    """Register a second (non-admin, viewer-role) user."""
    uid = _unique_id()
    creds = {
        "username": f"e2e_viewer_{uid}",
        "email": f"e2e_viewer_{uid}@test.local",
        "password": "ViewerPass123!",
    }
    resp = register_user_via_api(creds["username"], creds["email"], creds["password"])
    assert resp.status_code in (200, 201), (
        f"Viewer registration failed ({resp.status_code}): {resp.text}"
    )
    return creds


# ---------------------------------------------------------------------------
# Browser context fixtures
# ---------------------------------------------------------------------------


def _login_browser(browser: Browser, username: str, password: str) -> BrowserContext:
    """Log in via the browser and return a context with auth cookies."""
    context = browser.new_context()
    page = context.new_page()
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_url("**/", timeout=10000)
    page.close()
    return context


@pytest.fixture()
def admin_context(browser, admin_credentials) -> BrowserContext:
    """Authenticated browser context for admin user."""
    ctx = _login_browser(
        browser, admin_credentials["username"], admin_credentials["password"]
    )
    yield ctx
    ctx.close()


@pytest.fixture()
def admin_page(admin_context) -> Page:
    """Fresh page in admin browser context."""
    p = admin_context.new_page()
    yield p
    p.close()


@pytest.fixture()
def viewer_context(browser, viewer_credentials) -> BrowserContext:
    """Authenticated browser context for viewer user."""
    ctx = _login_browser(
        browser, viewer_credentials["username"], viewer_credentials["password"]
    )
    yield ctx
    ctx.close()


@pytest.fixture()
def viewer_page(viewer_context) -> Page:
    """Fresh page in viewer browser context."""
    p = viewer_context.new_page()
    yield p
    p.close()
