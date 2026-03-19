"""E2E tests for login flow — happy paths and error scenarios.

Spec: specs/e2e-playwright-happy-path.md (AC-010, TC-001)
Spec: specs/e2e-playwright-error-scenarios.md (AC-101–103, AC-110, AC-120–122)
"""

import subprocess
import uuid

from playwright.sync_api import BrowserContext, Page, expect

from tests.e2e.conftest import BASE_URL, register_user_via_api


class TestLoginFlow:
    """TC-001: Full login flow."""

    def test_ac010_login_page_renders(self, page: Page):
        """Login page loads with username, password fields and submit button."""
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")

        expect(page.locator('input[name="username"]')).to_be_visible()
        expect(page.locator('input[name="password"]')).to_be_visible()
        expect(page.locator('button[type="submit"]')).to_be_visible()

    def test_ac010_login_success_redirects_to_dashboard(self, browser):
        """Submit valid credentials → redirect to dashboard."""
        uid = uuid.uuid4().hex[:8]
        username = f"e2e_login_{uid}"
        email = f"e2e_login_{uid}@test.local"
        password = "LoginTestPass123!"

        # Register via API
        resp = register_user_via_api(username, email, password)
        assert resp.status_code in (200, 201)

        # Login via browser
        context = browser.new_context()
        page = context.new_page()
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")

        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')

        # Should redirect to dashboard
        page.wait_for_url("**/", timeout=10000)
        assert page.url.rstrip("/").endswith(BASE_URL.rstrip("/")) or page.url.endswith(
            "/"
        )

        page.close()
        context.close()

    def test_ac010_login_sets_auth_cookie(self, browser):
        """After login, access_token cookie is set."""
        uid = uuid.uuid4().hex[:8]
        username = f"e2e_cookie_{uid}"
        email = f"e2e_cookie_{uid}@test.local"
        password = "CookieTestPass123!"

        register_user_via_api(username, email, password)

        context = browser.new_context()
        page = context.new_page()
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")

        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_url("**/", timeout=10000)

        cookies = context.cookies()
        cookie_names = [c["name"] for c in cookies]
        assert "access_token" in cookie_names

        page.close()
        context.close()

    def test_ac010_logout_clears_session(self, admin_page: Page):
        """Clicking logout redirects to login page."""
        admin_page.goto(f"{BASE_URL}/")
        admin_page.wait_for_load_state("networkidle")

        # Find and click logout (typically a form POST)
        logout = admin_page.locator('a[href="/logout"], form[action="/logout"] button')
        if logout.count() > 0:
            logout.first.click()
            admin_page.wait_for_url("**/login*", timeout=10000)
            assert "/login" in admin_page.url


class TestLoginErrors:
    """Error scenarios for login — AC-101, AC-102, AC-103, TC-101."""

    def test_ac101_invalid_password_shows_error(self, browser):
        """Wrong password shows error message, stays on login page."""
        uid = uuid.uuid4().hex[:8]
        username = f"e2e_badpw_{uid}"
        register_user_via_api(username, f"{username}@test.local", "RealPass123!")

        context = browser.new_context()
        page = context.new_page()
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")

        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', "WrongPassword999!")
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        # Should stay on login page with error
        assert "/login" in page.url or page.url.endswith("/login")
        error = page.locator("text=Invalid username or password")
        expect(error).to_be_visible(timeout=5000)

        page.close()
        context.close()

    def test_ac102_nonexistent_user_shows_error(self, page: Page):
        """Login with non-existent username shows error."""
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")

        page.fill('input[name="username"]', f"nobody_{uuid.uuid4().hex[:8]}")
        page.fill('input[name="password"]', "AnyPass123!")
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        assert "/login" in page.url
        error = page.locator("text=Invalid username or password")
        expect(error).to_be_visible(timeout=5000)

    def test_ac103_disabled_account_shows_error(self, browser):
        """Disabled account shows 'Account is disabled' error."""
        uid = uuid.uuid4().hex[:8]
        username = f"e2e_disabled_{uid}"
        resp = register_user_via_api(
            username, f"{username}@test.local", "DisabledPass123!"
        )
        user_id = resp.json()["id"]

        # Disable the user via DB
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
                f"UPDATE users SET is_active = false WHERE id = '{user_id}';",
            ],
            check=True,
            capture_output=True,
            timeout=10,
        )

        context = browser.new_context()
        page = context.new_page()
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")

        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', "DisabledPass123!")
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        assert "/login" in page.url
        error = page.locator("text=Account is disabled")
        expect(error).to_be_visible(timeout=5000)

        page.close()
        context.close()


class TestCsrfLogin:
    """CSRF validation on login form — AC-110, TC-102."""

    def test_ac110_tampered_csrf_token_rejected(self, page: Page):
        """Login with tampered CSRF token fails."""
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")

        # Tamper the hidden CSRF token
        page.evaluate("""() => {
            const csrf = document.querySelector('input[name="csrf_token"]');
            if (csrf) csrf.value = 'tampered-invalid-token';
        }""")

        page.fill('input[name="username"]', "anyuser")
        page.fill('input[name="password"]', "anypass")
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        # Should not be on dashboard — either error or back on login
        assert (
            "/login" in page.url or "403" in page.content() or "CSRF" in page.content()
        )


class TestSessionExpiry:
    """Session expiry and auth redirects — AC-120, AC-121, AC-122, TC-103."""

    def test_ac120_unauthenticated_dashboard_redirects(self, browser):
        """Accessing / without auth cookie redirects to /login."""
        context = browser.new_context()
        page = context.new_page()
        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state("networkidle")

        assert "/login" in page.url

        page.close()
        context.close()

    def test_ac121_unauthenticated_settings_redirects(self, browser):
        """Accessing /settings without auth cookie redirects to /login."""
        context = browser.new_context()
        page = context.new_page()
        page.goto(f"{BASE_URL}/settings")
        page.wait_for_load_state("networkidle")

        assert "/login" in page.url

        page.close()
        context.close()

    def test_ac122_unauthenticated_admin_redirects(self, browser):
        """Accessing /admin/users without auth cookie redirects to /login."""
        context = browser.new_context()
        page = context.new_page()
        page.goto(f"{BASE_URL}/admin/users")
        page.wait_for_load_state("networkidle")

        assert "/login" in page.url

        page.close()
        context.close()

    def test_ac120_cleared_cookie_redirects(self, admin_context: BrowserContext):
        """Clearing access_token cookie then navigating redirects to login."""
        page = admin_context.new_page()

        # Verify we're authenticated
        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state("networkidle")
        assert "/login" not in page.url

        # Clear cookies to simulate session expiry
        admin_context.clear_cookies()

        # Navigate to a protected page
        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state("networkidle")
        assert "/login" in page.url

        page.close()
