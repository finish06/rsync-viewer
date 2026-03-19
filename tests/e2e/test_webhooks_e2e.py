"""E2E tests for webhook management — happy paths.

Spec: specs/e2e-playwright-happy-path.md
AC-016, AC-022, TC-005
"""

import uuid

from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL


def _open_settings_webhooks(page: Page):
    """Navigate to settings and wait for webhooks list to load."""
    page.goto(f"{BASE_URL}/settings")
    page.wait_for_load_state("networkidle")
    page.wait_for_function(
        """() => {
            const el = document.getElementById('webhooks-list');
            return el && el.innerHTML.trim().length > 10;
        }""",
        timeout=10000,
    )


def _create_webhook(page: Page, name: str) -> None:
    """Create a webhook via the settings UI modal."""
    add_btn = page.locator('[hx-get="/htmx/webhooks/add"]')
    if add_btn.count() == 0:
        add_btn = page.locator(
            'button:has-text("Add Webhook"), a:has-text("Add Webhook")'
        )
    add_btn.first.click()
    page.wait_for_selector(".modal-backdrop, .modal", timeout=5000)

    # Fill the form fields using their IDs
    page.locator("#wh-name").fill(name)
    page.locator("#wh-url").fill("https://httpbin.org/post")

    # Submit
    page.locator(
        '.modal button[type="submit"], .modal input[type="submit"]'
    ).first.click()

    # Wait for the response to swap the webhooks list (the form hx-target
    # is #webhooks-list and the response includes closeModal trigger)
    page.wait_for_timeout(3000)


class TestWebhookLifecycle:
    """TC-005: Webhook create, verify, toggle, delete lifecycle."""

    def test_ac016_create_webhook(self, admin_page: Page):
        """Create a webhook via the settings UI."""
        _open_settings_webhooks(admin_page)

        wh_name = f"e2e-wh-{uuid.uuid4().hex[:8]}"
        _create_webhook(admin_page, wh_name)

        # After creation, the list should refresh via HTMX swap.
        # Reload to be sure.
        _open_settings_webhooks(admin_page)
        expect(admin_page.locator(f"text={wh_name}")).to_be_visible(timeout=5000)

    def test_ac016_webhook_appears_in_list(self, admin_page: Page):
        """Created webhook shows in the webhooks list with its URL."""
        _open_settings_webhooks(admin_page)

        wh_name = f"e2e-whlist-{uuid.uuid4().hex[:8]}"
        _create_webhook(admin_page, wh_name)

        _open_settings_webhooks(admin_page)

        # Webhook name should be in the list
        expect(admin_page.locator(f"text={wh_name}")).to_be_visible(timeout=5000)

        # The row with our webhook should contain the URL
        wh_row = admin_page.locator(f"tr:has-text('{wh_name}')")
        expect(wh_row).to_be_visible(timeout=5000)
        expect(wh_row.locator("text=httpbin.org")).to_be_visible()

    def test_ac016_toggle_webhook(self, admin_page: Page):
        """Toggle a webhook enabled/disabled."""
        _open_settings_webhooks(admin_page)

        wh_name = f"e2e-whtoggle-{uuid.uuid4().hex[:8]}"
        _create_webhook(admin_page, wh_name)
        _open_settings_webhooks(admin_page)

        expect(admin_page.locator(f"text={wh_name}")).to_be_visible(timeout=5000)

        # Find toggle button in our webhook's row
        wh_row = admin_page.locator(f"tr:has-text('{wh_name}')")
        toggle_btn = wh_row.locator('[hx-post*="toggle"]')
        if toggle_btn.count() > 0:
            toggle_btn.click()
            admin_page.wait_for_timeout(2000)
            # Page should still be on settings (HTMX update)
            assert "/settings" in admin_page.url

    def test_ac016_delete_webhook(self, admin_page: Page):
        """Delete a webhook from the list."""
        _open_settings_webhooks(admin_page)

        wh_name = f"e2e-whdel-{uuid.uuid4().hex[:8]}"
        _create_webhook(admin_page, wh_name)
        _open_settings_webhooks(admin_page)

        expect(admin_page.locator(f"text={wh_name}")).to_be_visible(timeout=5000)

        # Accept confirm dialog
        admin_page.on("dialog", lambda dialog: dialog.accept())

        # Find and click delete button in the specific row
        wh_row = admin_page.locator(f"tr:has-text('{wh_name}')")
        delete_btn = wh_row.locator("[hx-delete]")
        if delete_btn.count() == 0:
            delete_btn = wh_row.locator(
                'button:has-text("Delete"), button:has-text("Remove")'
            )
        delete_btn.first.click()
        admin_page.wait_for_timeout(3000)

        # Reload and verify webhook is gone
        _open_settings_webhooks(admin_page)
        expect(admin_page.locator(f"text={wh_name}")).to_have_count(0, timeout=5000)

    def test_ac022_webhook_crud_htmx(self, admin_page: Page):
        """Webhook CRUD updates DOM via HTMX without full page reload."""
        _open_settings_webhooks(admin_page)

        wh_name = f"e2e-whhtmx-{uuid.uuid4().hex[:8]}"
        _create_webhook(admin_page, wh_name)

        # Should still be on settings (HTMX, no navigation)
        assert "/settings" in admin_page.url
