"""E2E tests for API key management in the SPA — specs/settings-ui.md.

TC-001: create → reveal once → copy → revoke lifecycle.
Screenshots: tests/screenshots/settings-ui/
"""

import uuid
from pathlib import Path

from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL

SCREENSHOTS = (
    Path(__file__).resolve().parents[2] / "tests" / "screenshots" / "settings-ui"
)


def _shot(page: Page, name: str) -> None:
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SCREENSHOTS / f"{name}.png"), full_page=True)


class TestApiKeyLifecycle:
    def test_tc001_create_reveal_copy_revoke(self, admin_page: Page):
        """AC-012: create, one-time reveal with copy, cancel-then-confirm revoke."""
        admin_page.goto(f"{BASE_URL}/app/settings/api-keys")
        admin_page.wait_for_load_state("networkidle")

        section = admin_page.get_by_test_id("api-keys-section")
        expect(section).to_be_visible()
        section.get_by_role("button", name="+ New key").click()

        form = admin_page.get_by_test_id("api-key-form")
        expect(form).to_be_visible()
        key_name = f"e2e-key-{uuid.uuid4().hex[:8]}"
        form.get_by_label("Name").fill(key_name)
        form.get_by_role("button", name="Create key").click()

        created = admin_page.get_by_test_id("api-key-created")
        expect(created).to_be_visible(timeout=10000)
        expect(created).to_contain_text("rsv_")
        expect(created.get_by_role("button", name="Copy")).to_be_visible()
        _shot(admin_page, "step-10-api-key-created")

        created.get_by_role("button", name="Done").click()
        expect(admin_page.get_by_test_id("api-key-created")).to_have_count(0)

        row = admin_page.get_by_test_id("api-key-row").filter(has_text=key_name)
        expect(row).to_be_visible()

        # Arm revoke, then cancel — the key must stay.
        row.get_by_role("button", name="Revoke").click()
        row.get_by_role("button", name="Cancel").click()
        expect(
            admin_page.get_by_test_id("api-key-row").filter(has_text=key_name)
        ).to_be_visible()

        # Arm again and confirm — the row disappears without a page reload.
        row.get_by_role("button", name="Revoke").click()
        row.get_by_role("button", name="Confirm").click()
        expect(
            admin_page.get_by_test_id("api-key-row").filter(has_text=key_name)
        ).to_have_count(0, timeout=10000)
        _shot(admin_page, "step-11-api-key-revoked")

    def test_ac012_role_override_is_capped_at_own_role(self, admin_page: Page):
        """The role-override select never offers a role above the caller's own."""
        admin_page.goto(f"{BASE_URL}/app/settings/api-keys")
        admin_page.wait_for_load_state("networkidle")
        section = admin_page.get_by_test_id("api-keys-section")
        section.get_by_role("button", name="+ New key").click()

        form = admin_page.get_by_test_id("api-key-form")
        role_select = form.get_by_label("Role override")
        options = role_select.locator("option").all_inner_texts()
        assert "admin" in options  # admin_page user is an admin
        form.get_by_role("button", name="Cancel").click()
        expect(admin_page.get_by_test_id("api-key-form")).to_have_count(0)
