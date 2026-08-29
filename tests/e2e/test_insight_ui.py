"""E2E tests for the Insight UI SPA — specs/insight-ui.md.

TC-001 (overview glance), TC-008 (deep link while logged out), TC-009 (mobile).
Screenshots: tests/screenshots/insight-ui/
"""

import uuid
from pathlib import Path

from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL, ingest_sync_log

SCREENSHOTS = Path("tests/screenshots/insight-ui")


def _shot(page: Page, name: str) -> None:
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SCREENSHOTS / f"{name}.png"), full_page=True)


class TestOverview:
    def test_tc001_overview_glance(self, admin_page: Page, admin_api_key: str):
        """AC-001, AC-006, AC-008: liveness pill, source cards, activity — no clicks."""
        source = f"e2e-insight-{uuid.uuid4().hex[:8]}"
        ingest_sync_log(admin_api_key, source)

        admin_page.goto(f"{BASE_URL}/app")
        admin_page.wait_for_load_state("networkidle")

        pill = admin_page.get_by_test_id("liveness-pill")
        expect(pill).to_be_visible()
        expect(pill).to_have_attribute(
            "data-status", r"passing|failing|unknown|disabled"
        )

        card = admin_page.get_by_test_id("source-card").filter(has_text=source)
        expect(card).to_be_visible(timeout=15000)
        expect(card).to_have_attribute("data-status", "ok")

        day = admin_page.get_by_test_id("activity-day").first
        expect(day).to_contain_text("Today")
        _shot(admin_page, "step-01-overview")

        # Card links to transfers filtered to the source (AC-006)
        expect(card).to_have_attribute("href", f"/app/transfers?source={source}")

    def test_tc002_drilldown_two_clicks(self, admin_page: Page, admin_api_key: str):
        """AC-008, AC-010: expand today's activity row, then a sync, inline."""
        source = f"e2e-drill-{uuid.uuid4().hex[:8]}"
        ingest_sync_log(admin_api_key, source)

        admin_page.goto(f"{BASE_URL}/app")
        admin_page.wait_for_load_state("networkidle")

        row = admin_page.get_by_test_id("sync-row").filter(has_text=source).first
        expect(row).to_be_visible(timeout=15000)
        row.get_by_role("button").click()
        detail = row.get_by_test_id("sync-detail")
        expect(detail).to_be_visible()
        expect(detail.get_by_test_id("file-list")).to_contain_text("test-file.txt")
        _shot(admin_page, "step-02-failure-drilldown")


class TestNavigationAndAuth:
    def test_tc008_deep_link_redirects_to_login(self, page: Page):
        """AC-022: unauthenticated deep link → login with return_url."""
        page.goto(f"{BASE_URL}/app/media")
        page.wait_for_load_state("networkidle")
        assert "/login" in page.url
        assert (
            "return_url=%2Fapp%2Fmedia" in page.url
            or "return_url=/app/media" in page.url
        )

    def test_ac023_nav_and_settings_menu(self, admin_page: Page):
        admin_page.goto(f"{BASE_URL}/app")
        admin_page.wait_for_load_state("networkidle")
        nav = admin_page.get_by_role("navigation", name="Primary")
        for label in ["Overview", "Transfers", "Trends", "Media", "Uptime"]:
            expect(nav.get_by_role("link", name=label)).to_be_visible()
        admin_page.get_by_role("button", name="Settings menu").click()
        expect(admin_page.get_by_role("menuitem", name="Settings")).to_have_attribute(
            "href", "/settings"
        )

    def test_tc009_mobile_no_horizontal_scroll(self, admin_context):
        """AC-027: 375px wide — no horizontal scroll, pill visible."""
        page = admin_context.new_page()
        page.set_viewport_size({"width": 375, "height": 740})
        page.goto(f"{BASE_URL}/app")
        page.wait_for_load_state("networkidle")
        expect(page.get_by_test_id("liveness-pill")).to_be_visible()
        scroll_width = page.evaluate("document.documentElement.scrollWidth")
        assert scroll_width <= 375, f"horizontal overflow: {scroll_width}px"
        _shot(page, "step-06-mobile")
        page.close()
