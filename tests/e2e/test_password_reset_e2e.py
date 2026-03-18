"""E2E tests for password reset flow — happy paths.

Spec: specs/e2e-playwright-happy-path.md
AC-018, TC-008
"""

from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL


class TestPasswordResetFlow:
    """TC-008: Password reset request flow."""

    def test_ac018_forgot_password_page_renders(self, page: Page):
        """Forgot password page loads with email field."""
        page.goto(f"{BASE_URL}/forgot-password")
        page.wait_for_load_state("networkidle")

        expect(page.locator('input[name="email"], input#email')).to_be_visible()
        expect(page.locator('button[type="submit"]')).to_be_visible()

    def test_ac018_submit_password_reset_request(self, page: Page):
        """Submit email for password reset shows confirmation."""
        page.goto(f"{BASE_URL}/forgot-password")
        page.wait_for_load_state("networkidle")

        page.fill("input#email", "test@example.com")
        page.click('button[type="submit"]')

        # The form uses JS fetch. On success, #reset-message gets class
        # "auth-message success" which sets display:block. Wait for that.
        page.wait_for_function(
            """() => {
                const el = document.getElementById('reset-message');
                return el && el.classList.contains('success');
            }""",
            timeout=10000,
        )

        # Verify the message has the expected text
        message = page.locator("#reset-message")
        assert (
            "reset" in message.text_content().lower()
            or "email" in message.text_content().lower()
        )

    def test_ac018_reset_password_page_renders(self, page: Page):
        """Reset password page loads with token parameter."""
        page.goto(f"{BASE_URL}/reset-password?token=fake-token-for-render-test")
        page.wait_for_load_state("networkidle")

        # Should render the reset form (even if token is invalid,
        # the page itself should load)
        expect(page.locator('input[type="password"]').first).to_be_visible()

    def test_ac018_login_page_has_forgot_password_link(self, page: Page):
        """Login page links to forgot password."""
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")

        forgot_link = page.locator('a[href*="forgot-password"]')
        expect(forgot_link).to_be_visible()

        forgot_link.click()
        page.wait_for_url("**/forgot-password*", timeout=5000)
        assert "/forgot-password" in page.url
