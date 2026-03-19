"""E2E tests for registration flow — happy paths and error scenarios.

Spec: specs/e2e-playwright-happy-path.md (AC-011, TC-002)
Spec: specs/e2e-playwright-error-scenarios.md (AC-111, AC-140–142, TC-105, TC-106)
"""

import uuid

from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL, register_user_via_api


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


class TestRegistrationErrors:
    """Error scenarios for registration — AC-140, AC-141, AC-142, TC-105, TC-106."""

    def test_ac140_duplicate_username_shows_error(self, browser):
        """Registering with an existing username shows error."""
        uid = uuid.uuid4().hex[:8]
        username = f"e2e_dup_{uid}"
        email = f"e2e_dup_{uid}@test.local"
        password = "DupPass123!"

        # Register first time via API
        register_user_via_api(username, email, password)

        # Try again via browser with same username, different email
        context = browser.new_context()
        page = context.new_page()
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state("networkidle")

        page.fill('input[name="username"]', username)
        page.fill('input[name="email"]', f"other_{uid}@test.local")
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        # Should stay on register page with error
        assert "/register" in page.url or "/login" not in page.url
        content = page.content().lower()
        assert "already" in content or "exists" in content or "taken" in content

        page.close()
        context.close()

    def test_ac141_duplicate_email_shows_error(self, browser):
        """Registering with an existing email shows error."""
        uid = uuid.uuid4().hex[:8]
        username = f"e2e_dupemail_{uid}"
        email = f"e2e_dupemail_{uid}@test.local"
        password = "DupEmailPass123!"

        # Register first time
        register_user_via_api(username, email, password)

        # Try again with same email, different username
        context = browser.new_context()
        page = context.new_page()
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state("networkidle")

        page.fill('input[name="username"]', f"other_{uid}")
        page.fill('input[name="email"]', email)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        # Should stay on register page with error
        assert "/register" in page.url or "/login" not in page.url
        content = page.content().lower()
        assert "already" in content or "exists" in content or "taken" in content

        page.close()
        context.close()

    def test_ac142_short_password_shows_error(self, page: Page):
        """Registering with too-short password shows validation error."""
        uid = uuid.uuid4().hex[:8]
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state("networkidle")

        page.fill('input[name="username"]', f"e2e_shortpw_{uid}")
        page.fill('input[name="email"]', f"e2e_shortpw_{uid}@test.local")
        page.fill('input[name="password"]', "abc")
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        # Should show validation error (either server-side or HTML5 validation)
        # Check for error message in page content
        content = page.content().lower()
        has_error = (
            "password" in content
            and ("short" in content or "min" in content or "8" in content)
        ) or "/register" in page.url

        assert has_error


class TestCsrfRegistration:
    """CSRF validation on registration form — AC-111.

    Note: CSRF middleware only protects /htmx/* prefixed endpoints (see
    CSRF_PROTECTED_PREFIXES in app/middleware.py). The /register endpoint
    is NOT CSRF-protected because registration is a public endpoint with
    no existing session to protect. This test documents that behavior.
    """

    def test_ac111_register_form_includes_csrf_token(self, page: Page):
        """Registration form includes a CSRF hidden field (for HTMX forms)."""
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state("networkidle")

        csrf_field = page.locator('input[name="csrf_token"]')
        assert csrf_field.count() > 0
        token_value = csrf_field.get_attribute("value")
        assert token_value and len(token_value) > 10
