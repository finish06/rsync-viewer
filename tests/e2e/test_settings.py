"""E2E tests for /app/settings — specs/settings-ui.md.

TC-008 (viewer scope + forbidden direct link), TC-009 (legacy redirects),
TC-005 (synthetic interval save), TC-006 (monitoring wizard).
Screenshots: tests/screenshots/settings-ui/
"""

import uuid
from pathlib import Path

import requests
from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL

SCREENSHOTS = (
    Path(__file__).resolve().parents[2] / "tests" / "screenshots" / "settings-ui"
)

SECTION_LABELS = [
    "API keys",
    "Webhooks",
    "Email",
    "Sign-in",
    "Monitoring",
    "Users",
    "Changelog",
]


def _shot(page: Page, name: str) -> None:
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SCREENSHOTS / f"{name}.png"), full_page=True)


class TestLegacyRedirects:
    """TC-009: /settings, /settings#changelog, /admin/users — logged in and out."""

    def test_tc009_settings_redirects_when_authenticated(self, admin_page: Page):
        admin_page.goto(f"{BASE_URL}/settings")
        admin_page.wait_for_url("**/app/settings/api-keys", timeout=10000)
        expect(admin_page.get_by_test_id("settings-layout")).to_be_visible()

    def test_tc009_admin_users_redirects_when_authenticated(self, admin_page: Page):
        admin_page.goto(f"{BASE_URL}/admin/users")
        admin_page.wait_for_url("**/app/settings/users", timeout=10000)
        expect(admin_page.get_by_test_id("users-section")).to_be_visible()

    def test_tc009_settings_changelog_hash_redirects_when_authenticated(
        self, admin_page: Page
    ):
        admin_page.goto(f"{BASE_URL}/settings#changelog")
        admin_page.wait_for_url("**/app/settings/changelog", timeout=10000)
        expect(admin_page.get_by_test_id("changelog-section")).to_be_visible()

    def test_tc009_settings_redirects_to_login_when_unauthenticated(self, page: Page):
        page.goto(f"{BASE_URL}/settings")
        page.wait_for_load_state("networkidle")
        assert "/login" in page.url
        assert (
            "return_url=%2Fsettings" in page.url or "return_url=/settings" in page.url
        )

    def test_tc009_admin_users_redirects_to_login_when_unauthenticated(
        self, page: Page
    ):
        page.goto(f"{BASE_URL}/admin/users")
        page.wait_for_load_state("networkidle")
        assert "/login" in page.url
        assert (
            "return_url=%2Fadmin%2Fusers" in page.url
            or "return_url=/admin/users" in page.url
        )


class TestAdminSections:
    """AC-011: every section renders for an admin."""

    def test_ac011_admin_sees_all_sections(self, admin_page: Page):
        admin_page.goto(f"{BASE_URL}/app/settings")
        admin_page.wait_for_url("**/app/settings/api-keys", timeout=10000)
        expect(admin_page.get_by_test_id("settings-layout")).to_be_visible()

        nav = admin_page.get_by_role("navigation", name="Settings")
        for label in SECTION_LABELS:
            expect(nav.get_by_role("link", name=label)).to_be_visible()
        expect(admin_page.get_by_test_id("api-keys-section")).to_be_visible()
        _shot(admin_page, "step-01-settings-home")

        nav.get_by_role("link", name="Webhooks").click()
        admin_page.wait_for_url("**/app/settings/webhooks", timeout=10000)
        expect(admin_page.get_by_test_id("webhooks-section")).to_be_visible()

        nav.get_by_role("link", name="Email").click()
        admin_page.wait_for_url("**/app/settings/email", timeout=10000)
        expect(admin_page.get_by_test_id("email-section")).to_be_visible()
        expect(admin_page.get_by_test_id("smtp-form")).to_be_visible()
        _shot(admin_page, "step-02-email")

        nav.get_by_role("link", name="Sign-in").click()
        admin_page.wait_for_url("**/app/settings/sign-in", timeout=10000)
        expect(admin_page.get_by_test_id("signin-section")).to_be_visible()
        expect(admin_page.get_by_test_id("oidc-form")).to_be_visible()
        _shot(admin_page, "step-03-sign-in")

        nav.get_by_role("link", name="Monitoring").click()
        admin_page.wait_for_url("**/app/settings/monitoring", timeout=10000)
        expect(admin_page.get_by_test_id("synthetic-settings")).to_be_visible()
        expect(admin_page.get_by_test_id("monitoring-wizard")).to_be_visible()
        _shot(admin_page, "step-04-monitoring")

        nav.get_by_role("link", name="Users").click()
        admin_page.wait_for_url("**/app/settings/users", timeout=10000)
        expect(admin_page.get_by_test_id("users-section")).to_be_visible()
        _shot(admin_page, "step-05-users")

        nav.get_by_role("link", name="Changelog").click()
        admin_page.wait_for_url("**/app/settings/changelog", timeout=10000)
        expect(admin_page.get_by_test_id("changelog-section")).to_be_visible()
        _shot(admin_page, "step-06-changelog")


class TestViewerScope:
    """TC-008: viewer sees only API keys and Changelog; direct admin link is forbidden."""

    def test_tc008_viewer_scope_and_forbidden_direct_link(self, viewer_page: Page):
        viewer_page.goto(f"{BASE_URL}/app/settings")
        viewer_page.wait_for_url("**/app/settings/api-keys", timeout=10000)

        nav = viewer_page.get_by_role("navigation", name="Settings")
        expect(nav.get_by_role("link", name="API keys")).to_be_visible()
        expect(nav.get_by_role("link", name="Changelog")).to_be_visible()
        for label in ["Webhooks", "Email", "Sign-in", "Monitoring", "Users"]:
            expect(nav.get_by_role("link", name=label)).to_have_count(0)
        _shot(viewer_page, "step-07-viewer-scope")

        viewer_page.goto(f"{BASE_URL}/app/settings/users")
        forbidden = viewer_page.get_by_test_id("forbidden")
        expect(forbidden).to_be_visible()
        expect(forbidden).to_contain_text("admin")


class TestMonitoring:
    """TC-005 (synthetic interval) and TC-006 (monitoring wizard)."""

    def test_tc005_synthetic_interval_save_shows_toast(
        self, admin_page: Page, admin_token: str
    ):
        headers = {"Authorization": f"Bearer {admin_token}"}
        original = requests.get(
            f"{BASE_URL}/api/v1/settings/synthetic", headers=headers, timeout=10
        )
        original.raise_for_status()
        original_data = original.json()

        try:
            admin_page.goto(f"{BASE_URL}/app/settings/monitoring")
            admin_page.wait_for_load_state("networkidle")
            form = admin_page.get_by_test_id("synthetic-form")
            expect(form).to_be_visible()

            interval_input = form.get_by_label("Interval (seconds)")
            interval_input.fill("45")
            form.get_by_role("button", name="Save").click()

            toast = admin_page.get_by_test_id("toast").last
            expect(toast).to_contain_text(
                "Synthetic monitoring updated — changes take effect immediately"
            )
        finally:
            requests.put(
                f"{BASE_URL}/api/v1/settings/synthetic",
                json={
                    "enabled": original_data["enabled"],
                    "interval_seconds": original_data["interval_seconds"],
                },
                headers=headers,
                timeout=10,
            ).raise_for_status()

    def test_tc006_monitoring_wizard_generates_key(self, admin_page: Page):
        source = f"e2e-wizard-{uuid.uuid4().hex[:8]}"
        key_name = f"rsync-client-{source}"

        admin_page.goto(f"{BASE_URL}/app/settings/monitoring")
        admin_page.wait_for_load_state("networkidle")
        wizard = admin_page.get_by_test_id("monitoring-wizard")
        wizard.get_by_label("Source name").fill(source)
        wizard.get_by_label("Rsync source").fill("backup@nas.local:/data")
        wizard.get_by_role("button", name="Generate").click()

        result = admin_page.get_by_test_id("wizard-result")
        expect(result).to_be_visible(timeout=10000)
        expect(result).to_contain_text("RSYNC_VIEWER_API_KEY=rsv_")
        expect(result).to_contain_text(key_name)
        _shot(admin_page, "step-50-wizard-result")

        admin_page.get_by_role("navigation", name="Settings").get_by_role(
            "link", name="API keys"
        ).click()
        admin_page.wait_for_url("**/app/settings/api-keys", timeout=10000)
        row = admin_page.get_by_test_id("api-key-row").filter(has_text=key_name)
        expect(row).to_be_visible(timeout=10000)
