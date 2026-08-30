"""E2E tests for the dashboard — now the Insight UI SPA at /.

Spec: specs/insight-ui.md (AC-024 cut-over) — replaces the legacy HTMX
dashboard tests from specs/e2e-playwright-happy-path.md TC-003.
"""

import uuid

from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL, ingest_sync_log


class TestDashboardPage:
    def test_ac024_root_serves_the_spa(self, admin_page: Page):
        """/ renders the SPA shell with the primary navigation."""
        admin_page.goto(f"{BASE_URL}/")
        admin_page.wait_for_load_state("networkidle")
        nav = admin_page.get_by_role("navigation", name="Primary")
        for label in ["Overview", "Transfers", "Trends", "Media", "Uptime"]:
            expect(nav.get_by_role("link", name=label)).to_be_visible()
        expect(admin_page.get_by_test_id("liveness-pill")).to_be_visible()

    def test_ac024_user_context_injected(self, admin_page: Page, admin_credentials):
        """The shell knows who is signed in without an extra request."""
        admin_page.goto(f"{BASE_URL}/")
        admin_page.wait_for_load_state("networkidle")
        injected = admin_page.evaluate("window.__USER__")
        assert injected["username"] == admin_credentials["username"]
        assert injected["role"] == "admin"

    def test_ac006_ingested_source_appears_on_overview(
        self, admin_page: Page, admin_api_key: str
    ):
        source = f"e2e-dash-{uuid.uuid4().hex[:8]}"
        ingest_sync_log(admin_api_key, source)
        admin_page.goto(f"{BASE_URL}/")
        admin_page.wait_for_load_state("networkidle")
        card = admin_page.get_by_test_id("source-row").filter(has_text=source)
        expect(card).to_be_visible(timeout=15000)
        expect(card).to_have_attribute("data-status", "ok")

    def test_ac024_legacy_tab_links_redirect(self, admin_page: Page):
        admin_page.goto(f"{BASE_URL}/?tab=notifications")
        admin_page.wait_for_load_state("networkidle")
        assert admin_page.url.rstrip("/").endswith("/notifications")
        expect(admin_page.locator("#notifications-container")).to_be_visible(
            timeout=10000
        )

    def test_ac023_settings_menu_opens_spa_settings(self, admin_page: Page):
        """AC-011: the ⚙ menu's Settings item opens the SPA settings, not a server page."""
        admin_page.goto(f"{BASE_URL}/")
        admin_page.wait_for_load_state("networkidle")
        admin_page.get_by_role("button", name="Settings menu").click()
        menu = admin_page.get_by_role("menu")
        expect(menu.get_by_role("menuitem", name="Users")).to_be_visible()
        menu.get_by_role("menuitem", name="Settings").click()
        admin_page.wait_for_url("**/app/settings**", timeout=10000)
        expect(admin_page.get_by_test_id("settings-layout")).to_be_visible()
