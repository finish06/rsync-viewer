"""E2E tests for registration flow — happy paths.

Spec: specs/e2e-playwright-happy-path.md
AC-011, TC-002
"""

import uuid

from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL


class TestRegistrationFlow:
    """TC-002: User registration."""

    def test_ac011_register_page_renders(self, page: Page):
        """Registration page loads with username, email, password fields."""
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state("networkidle")

        expect(page.locator('input[name="username"]')).to_be_visible()
        expect(page.locator('input[name="email"]')).to_be_visible()
        expect(page.locator('input[name="password"]')).to_be_visible()
        expect(page.locator('button[type="submit"]')).to_be_visible()

    def test_ac011_register_success_redirects_to_login(self, browser):
        """Submit valid registration → redirect to login with success message."""
        uid = uuid.uuid4().hex[:8]
        username = f"e2e_reg_{uid}"
        email = f"e2e_reg_{uid}@test.local"
        password = "RegisterPass123!"

        context = browser.new_context()
        page = context.new_page()
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state("networkidle")

        page.fill('input[name="username"]', username)
        page.fill('input[name="email"]', email)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')

        # Should redirect to login
        page.wait_for_url("**/login*", timeout=10000)
        assert "/login" in page.url

        # Should show success message
        success_msg = page.locator("text=Account created successfully")
        expect(success_msg).to_be_visible(timeout=5000)

        page.close()
        context.close()

    def test_ac011_can_login_after_registration(self, browser):
        """Register, then log in with the same credentials."""
        uid = uuid.uuid4().hex[:8]
        username = f"e2e_reglogin_{uid}"
        email = f"e2e_reglogin_{uid}@test.local"
        password = "RegLoginPass123!"

        context = browser.new_context()
        page = context.new_page()

        # Register
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state("networkidle")
        page.fill('input[name="username"]', username)
        page.fill('input[name="email"]', email)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_url("**/login*", timeout=10000)

        # Login
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_url("**/", timeout=10000)

        # Verify on dashboard
        assert page.url.rstrip("/").endswith(BASE_URL.rstrip("/")) or page.url.endswith(
            "/"
        )

        page.close()
        context.close()
