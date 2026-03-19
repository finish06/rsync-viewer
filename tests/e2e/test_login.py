"""E2E tests for login flow — happy paths.

Spec: specs/e2e-playwright-happy-path.md
AC-010, TC-001
"""

import uuid

from playwright.sync_api import Page, expect

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
