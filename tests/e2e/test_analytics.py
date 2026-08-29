"""E2E tests for analytics — now the Insight UI Trends page.

Spec: specs/insight-ui.md AC-013, AC-024 (legacy /analytics redirect).
"""

from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL


class TestAnalyticsPage:
    def test_ac024_legacy_analytics_redirects_to_trends(self, admin_page: Page):
        admin_page.goto(f"{BASE_URL}/analytics")
        admin_page.wait_for_load_state("networkidle")
        assert admin_page.url.rstrip("/").endswith("/app/trends")

    def test_ac013_trends_has_four_linked_charts(self, admin_page: Page):
        admin_page.goto(f"{BASE_URL}/app/trends")
        admin_page.wait_for_load_state("networkidle")
        expect(admin_page.get_by_test_id("trend-chart")).to_have_count(4)
        expect(admin_page.get_by_test_id("source-table")).to_be_visible()
        assert admin_page.locator("text=Internal Server Error").count() == 0
