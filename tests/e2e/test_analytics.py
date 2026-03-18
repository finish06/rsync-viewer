"""E2E tests for analytics page — happy paths.

Spec: specs/e2e-playwright-happy-path.md
AC-013
"""

import uuid

from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL, ingest_sync_log


class TestAnalyticsPage:
    """Analytics page renders charts and stats."""

    def test_ac013_analytics_redirect(self, admin_page: Page):
        """/analytics redirects to dashboard with analytics tab."""
        admin_page.goto(f"{BASE_URL}/analytics")
        admin_page.wait_for_load_state("networkidle")

        # Should redirect to /?tab=analytics
        assert "tab=analytics" in admin_page.url or admin_page.url.endswith("/")

    def test_ac013_analytics_tab_has_content(
        self, admin_page: Page, admin_api_key: str
    ):
        """Analytics tab renders summary stats after data ingestion."""
        # Ingest some data so analytics has something to show
        source = f"e2e-analytics-{uuid.uuid4().hex[:8]}"
        ingest_sync_log(admin_api_key, source)

        admin_page.goto(f"{BASE_URL}/")
        admin_page.wait_for_load_state("networkidle")

        # Switch to analytics tab
        admin_page.locator('[data-tab="analytics"]').click()

        # Wait for analytics content to load
        analytics = admin_page.locator("#analytics-container")
        expect(analytics).to_be_visible(timeout=10000)

        admin_page.wait_for_function(
            """() => {
                const el = document.getElementById('analytics-container');
                return el && el.innerHTML.trim().length > 50;
            }""",
            timeout=10000,
        )

        # Analytics should contain some numeric data or chart elements
        content = analytics.inner_text()
        assert len(content.strip()) > 0
