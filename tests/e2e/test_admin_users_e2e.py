"""E2E tests for user management in the SPA — specs/settings-ui.md.

TC-007: change a throwaway user's role, disable/enable, confirm the admin's
own row has no controls, and confirm a viewer cannot reach the Users section.
Screenshots: tests/screenshots/settings-ui/
"""

import uuid
from pathlib import Path

from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL, register_user_via_api

SCREENSHOTS = (
    Path(__file__).resolve().parents[2] / "tests" / "screenshots" / "settings-ui"
)


def _shot(page: Page, name: str) -> None:
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SCREENSHOTS / f"{name}.png"), full_page=True)


class TestAdminUsers:
    def test_tc007_role_change_disable_enable_self_row_and_viewer_forbidden(
        self, admin_page: Page, viewer_page: Page, admin_credentials: dict
    ):
        username = f"e2e_usermgmt_{uuid.uuid4().hex[:8]}"
        resp = register_user_via_api(
            username, f"{username}@test.local", "ThrowawayPass123!"
        )
        assert resp.status_code in (200, 201), (
            f"Throwaway user registration failed ({resp.status_code}): {resp.text}"
        )

        admin_page.goto(f"{BASE_URL}/app/settings/users")
        admin_page.wait_for_load_state("networkidle")
        section = admin_page.get_by_test_id("users-section")
        expect(section).to_be_visible()
        _shot(admin_page, "step-30-users")

        row = admin_page.get_by_test_id("user-row").filter(has_text=username)
        expect(row).to_be_visible(timeout=10000)

        role_select = row.get_by_label(f"Role for {username}")
        role_select.select_option("operator")
        toast = admin_page.get_by_test_id("toast").last
        expect(toast).to_contain_text(f"{username} is now operator")

        # Disable → status flips, button relabels to Enable.
        row.get_by_role("button", name="Disable").click()
        expect(row.locator("[data-status]")).to_have_attribute(
            "data-status", "never", timeout=10000
        )
        expect(row.get_by_role("button", name="Enable")).to_be_visible()

        # Enable → status flips back.
        row.get_by_role("button", name="Enable").click()
        expect(row.locator("[data-status]")).to_have_attribute(
            "data-status", "ok", timeout=10000
        )

        # The admin's own row has no role select and no action buttons.
        self_row = admin_page.get_by_test_id("user-row").filter(
            has_text=admin_credentials["username"]
        )
        expect(self_row).to_be_visible()
        expect(self_row).to_contain_text("(you)")
        expect(self_row.locator("select")).to_have_count(0)
        expect(self_row.get_by_role("button")).to_have_count(0)

        # A viewer cannot reach the Users section at all.
        viewer_page.goto(f"{BASE_URL}/app/settings/users")
        forbidden = viewer_page.get_by_test_id("forbidden")
        expect(forbidden).to_be_visible()
        expect(forbidden).to_contain_text("admin")

    def test_ac017_delete_user_with_confirmation(self, admin_page: Page):
        username = f"e2e_userdel_{uuid.uuid4().hex[:8]}"
        resp = register_user_via_api(
            username, f"{username}@test.local", "ThrowawayPass123!"
        )
        assert resp.status_code in (200, 201), (
            f"Throwaway user registration failed ({resp.status_code}): {resp.text}"
        )

        admin_page.goto(f"{BASE_URL}/app/settings/users")
        admin_page.wait_for_load_state("networkidle")
        row = admin_page.get_by_test_id("user-row").filter(has_text=username)
        expect(row).to_be_visible(timeout=10000)

        row.get_by_role("button", name="Delete").click()
        row.get_by_role("button", name="Delete user").click()
        expect(
            admin_page.get_by_test_id("user-row").filter(has_text=username)
        ).to_have_count(0, timeout=10000)
