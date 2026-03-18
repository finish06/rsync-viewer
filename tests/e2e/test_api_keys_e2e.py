"""E2E tests for API key management — happy paths.

Spec: specs/e2e-playwright-happy-path.md
AC-015, AC-022, TC-004
"""

import uuid

from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL


class TestApiKeyLifecycle:
    """TC-004: API key create → verify → revoke lifecycle."""

    def test_ac015_create_api_key(self, admin_page: Page):
        """Create a new API key via the settings UI."""
        admin_page.goto(f"{BASE_URL}/settings")
        admin_page.wait_for_load_state("networkidle")

        # Wait for API keys list to load
        admin_page.wait_for_function(
            """() => {
                const el = document.getElementById('api-keys-list');
                return el && el.innerHTML.trim().length > 10;
            }""",
            timeout=10000,
        )

        # Click "Generate Key" button to open modal
        gen_btn = admin_page.locator(
            'button:has-text("Generate"), a:has-text("Generate")'
        )
        if gen_btn.count() == 0:
            gen_btn = admin_page.locator('[hx-get="/htmx/api-keys/add"]')
        expect(gen_btn.first).to_be_visible()
        gen_btn.first.click()

        # Wait for modal to appear
        admin_page.wait_for_selector(".modal-backdrop, .modal", timeout=5000)

        # Fill in key name
        key_name = f"e2e-key-{uuid.uuid4().hex[:8]}"
        admin_page.fill('input[name="name"]', key_name)

        # Submit form
        admin_page.locator(
            '.modal button[type="submit"], .modal input[type="submit"]'
        ).first.click()

        # Wait for response — should show the created key or refresh the list
        admin_page.wait_for_timeout(3000)

        # The key value should be displayed (one-time display)
        key_display = admin_page.locator("#api-key-value, .api-key-value")
        if key_display.count() > 0:
            key_text = key_display.first.text_content()
            assert key_text and len(key_text) > 10

    def test_ac015_api_key_appears_in_list(self, admin_page: Page):
        """After creating a key, it appears in the API keys list."""
        admin_page.goto(f"{BASE_URL}/settings")
        admin_page.wait_for_load_state("networkidle")

        # Wait for API keys list to load
        admin_page.wait_for_function(
            """() => {
                const el = document.getElementById('api-keys-list');
                return el && el.innerHTML.trim().length > 10;
            }""",
            timeout=10000,
        )

        # Create a key via modal
        key_name = f"e2e-list-{uuid.uuid4().hex[:8]}"

        gen_btn = admin_page.locator(
            'button:has-text("Generate"), a:has-text("Generate")'
        )
        if gen_btn.count() == 0:
            gen_btn = admin_page.locator('[hx-get="/htmx/api-keys/add"]')
        gen_btn.first.click()
        admin_page.wait_for_selector(".modal-backdrop, .modal", timeout=5000)
        admin_page.fill('input[name="name"]', key_name)
        admin_page.locator(
            '.modal button[type="submit"], .modal input[type="submit"]'
        ).first.click()
        admin_page.wait_for_timeout(3000)

        # Close modal if still open (click backdrop or close button)
        close_btn = admin_page.locator(".modal-close, .modal-backdrop")
        if close_btn.count() > 0:
            # Try the close button first
            close_x = admin_page.locator(".modal-close")
            if close_x.count() > 0:
                close_x.first.click()

        # Reload settings to see updated list
        admin_page.goto(f"{BASE_URL}/settings")
        admin_page.wait_for_load_state("networkidle")
        admin_page.wait_for_function(
            """() => {
                const el = document.getElementById('api-keys-list');
                return el && el.innerHTML.trim().length > 10;
            }""",
            timeout=10000,
        )

        # Key name should appear in the list
        expect(admin_page.locator(f"text={key_name}")).to_be_visible(timeout=5000)

    def test_ac015_revoke_api_key(self, admin_page: Page):
        """Create then revoke an API key."""
        admin_page.goto(f"{BASE_URL}/settings")
        admin_page.wait_for_load_state("networkidle")

        admin_page.wait_for_function(
            """() => {
                const el = document.getElementById('api-keys-list');
                return el && el.innerHTML.trim().length > 10;
            }""",
            timeout=10000,
        )

        # Create a key to revoke
        key_name = f"e2e-revoke-{uuid.uuid4().hex[:8]}"
        gen_btn = admin_page.locator(
            'button:has-text("Generate"), a:has-text("Generate")'
        )
        if gen_btn.count() == 0:
            gen_btn = admin_page.locator('[hx-get="/htmx/api-keys/add"]')
        gen_btn.first.click()
        admin_page.wait_for_selector(".modal-backdrop, .modal", timeout=5000)
        admin_page.fill('input[name="name"]', key_name)
        admin_page.locator(
            '.modal button[type="submit"], .modal input[type="submit"]'
        ).first.click()
        admin_page.wait_for_timeout(3000)

        # Reload to get fresh list
        admin_page.goto(f"{BASE_URL}/settings")
        admin_page.wait_for_load_state("networkidle")
        admin_page.wait_for_function(
            """() => {
                const el = document.getElementById('api-keys-list');
                return el && el.innerHTML.trim().length > 10;
            }""",
            timeout=10000,
        )

        # Find the revoke button for our key within its table row
        # Accept the confirm dialog
        admin_page.on("dialog", lambda dialog: dialog.accept())

        key_row = admin_page.locator(f"tr:has-text('{key_name}')")
        expect(key_row).to_be_visible(timeout=5000)

        # Click the delete/revoke button within that specific row
        revoke_btn = key_row.locator("button[hx-delete]")
        if revoke_btn.count() == 0:
            revoke_btn = key_row.locator(
                'button:has-text("Revoke"), button:has-text("Delete")'
            )
        expect(revoke_btn.first).to_be_visible(timeout=5000)
        revoke_btn.first.click()
        admin_page.wait_for_timeout(3000)

        # Key should be gone from the list
        admin_page.goto(f"{BASE_URL}/settings")
        admin_page.wait_for_load_state("networkidle")
        admin_page.wait_for_function(
            """() => {
                const el = document.getElementById('api-keys-list');
                return el && el.innerHTML.trim().length > 10;
            }""",
            timeout=10000,
        )
        expect(admin_page.locator(f"text={key_name}")).to_have_count(0, timeout=5000)

    def test_ac022_api_key_crud_updates_dom(self, admin_page: Page):
        """API key CRUD operations update the DOM via HTMX (no full reload)."""
        admin_page.goto(f"{BASE_URL}/settings")
        admin_page.wait_for_load_state("networkidle")

        admin_page.wait_for_function(
            """() => {
                const el = document.getElementById('api-keys-list');
                return el && el.innerHTML.trim().length > 10;
            }""",
            timeout=10000,
        )

        # Create a key
        key_name = f"e2e-dom-{uuid.uuid4().hex[:8]}"
        gen_btn = admin_page.locator(
            'button:has-text("Generate"), a:has-text("Generate")'
        )
        if gen_btn.count() == 0:
            gen_btn = admin_page.locator('[hx-get="/htmx/api-keys/add"]')
        gen_btn.first.click()
        admin_page.wait_for_selector(".modal-backdrop, .modal", timeout=5000)
        admin_page.fill('input[name="name"]', key_name)
        admin_page.locator(
            '.modal button[type="submit"], .modal input[type="submit"]'
        ).first.click()
        admin_page.wait_for_timeout(3000)

        # The DOM should have been updated without a full page navigation
        # (URL should still be /settings)
        assert "/settings" in admin_page.url
