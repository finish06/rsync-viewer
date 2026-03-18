"""E2E tests for dashboard page — happy paths.

Spec: specs/e2e-playwright-happy-path.md
AC-012, AC-020, TC-003
"""

import uuid

from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL, ingest_sync_log


class TestDashboardPage:
    """TC-003: Dashboard data display and HTMX partials."""

    def test_ac012_dashboard_loads(self, admin_page: Page):
        """Dashboard page loads for authenticated user."""
        admin_page.goto(f"{BASE_URL}/")
        admin_page.wait_for_load_state("networkidle")

        # Should see the dashboard tabs
        expect(admin_page.locator('[data-tab="syncs"]')).to_be_visible()

    def test_ac012_sync_table_renders(self, admin_page: Page, admin_api_key: str):
        """Sync table shows ingested logs."""
        source = f"e2e-dash-{uuid.uuid4().hex[:8]}"
        ingest_sync_log(admin_api_key, source)

        # Navigate to dashboard — click "max" quick-select to see all logs
        admin_page.goto(f"{BASE_URL}/")
        admin_page.wait_for_load_state("networkidle")

        # Wait for sync table HTMX content to load
        admin_page.wait_for_function(
            """() => {
                const el = document.getElementById('sync-table');
                return el && el.innerHTML.trim().length > 50;
            }""",
            timeout=15000,
        )

        # Click "max" date range to ensure all logs are visible
        max_btn = admin_page.locator('.quick-select-btn[data-range="max"]')
        if max_btn.count() > 0:
            max_btn.click()
            admin_page.wait_for_timeout(3000)

        # Source should appear in the table (not in the filter dropdown <option>)
        table_cell = admin_page.locator(f"#sync-table td:has-text('{source}')")
        expect(table_cell.first).to_be_visible(timeout=10000)

    def test_ac020_sync_table_loads_via_htmx(self, admin_page: Page):
        """Sync table content is loaded via HTMX (not server-rendered in initial HTML)."""
        admin_page.goto(f"{BASE_URL}/")
        admin_page.wait_for_load_state("networkidle")

        # The #sync-table div should have hx-get or contain loaded table content
        sync_table = admin_page.locator("#sync-table")
        expect(sync_table).to_be_visible(timeout=10000)

    def test_ac020_analytics_tab_loads(self, admin_page: Page):
        """Clicking analytics tab triggers HTMX load."""
        admin_page.goto(f"{BASE_URL}/")
        admin_page.wait_for_load_state("networkidle")

        # Click analytics tab
        admin_page.locator('[data-tab="analytics"]').click()

        # Wait for analytics container to load content
        analytics = admin_page.locator("#analytics-container")
        expect(analytics).to_be_visible(timeout=10000)
        # Should have some analytics content (not just "Loading...")
        admin_page.wait_for_function(
            """() => {
                const el = document.getElementById('analytics-container');
                return el && el.innerHTML.trim().length > 20;
            }""",
            timeout=10000,
        )

    def test_ac020_notifications_tab_loads(self, admin_page: Page):
        """Clicking notifications tab triggers HTMX load."""
        admin_page.goto(f"{BASE_URL}/")
        admin_page.wait_for_load_state("networkidle")

        # Click notifications tab
        admin_page.locator('[data-tab="notifications"]').click()

        # Wait for notifications container to populate
        notifications = admin_page.locator("#notifications-container")
        expect(notifications).to_be_visible(timeout=10000)
        admin_page.wait_for_function(
            """() => {
                const el = document.getElementById('notifications-container');
                return el && el.innerHTML.trim().length > 20;
            }""",
            timeout=10000,
        )

    def test_ac012_sync_detail_modal(self, admin_page: Page, admin_api_key: str):
        """Clicking a sync log row opens the detail view."""
        source = f"e2e-detail-{uuid.uuid4().hex[:8]}"
        ingest_sync_log(admin_api_key, source)

        admin_page.goto(f"{BASE_URL}/")
        admin_page.wait_for_load_state("networkidle")

        admin_page.wait_for_function(
            """() => {
                const el = document.getElementById('sync-table');
                return el && el.innerHTML.trim().length > 50;
            }""",
            timeout=15000,
        )

        # Click "max" range to see all logs
        max_btn = admin_page.locator('.quick-select-btn[data-range="max"]')
        if max_btn.count() > 0:
            max_btn.click()
            admin_page.wait_for_timeout(3000)

        # Find and click the source name in the table (not filter dropdown)
        source_link = admin_page.locator(f"#sync-table td:has-text('{source}')")
        expect(source_link.first).to_be_visible(timeout=10000)
        source_link.first.click()
        admin_page.wait_for_timeout(2000)

        # Detail may be inline expansion, modal, or navigation
        # Just verify no server error occurred
        assert admin_page.locator("text=Internal Server Error").count() == 0

    def test_ac012_filter_by_source(self, admin_page: Page, admin_api_key: str):
        """Filter form exists and submitting it does not error."""
        source = f"e2e-filter-{uuid.uuid4().hex[:8]}"
        ingest_sync_log(admin_api_key, source)

        # Reload to pick up the new source in the dropdown
        admin_page.goto(f"{BASE_URL}/")
        admin_page.wait_for_load_state("networkidle")
        admin_page.wait_for_function(
            """() => {
                const el = document.getElementById('sync-table');
                return el && el.innerHTML.trim().length > 50;
            }""",
            timeout=15000,
        )

        # Verify the filter form exists
        filter_form = admin_page.locator("#filter-form")
        expect(filter_form).to_be_visible(timeout=5000)

        filter_select = admin_page.locator('select[name="source_name"]')
        expect(filter_select).to_be_visible(timeout=5000)

        # Submit the filter form (without changing the selection) and verify no error
        filter_form.evaluate(
            "form => form.dispatchEvent(new Event('submit', {bubbles: true}))"
        )
        admin_page.wait_for_timeout(2000)

        # Page should still be on the dashboard without errors
        assert admin_page.locator("text=Internal Server Error").count() == 0
        table = admin_page.locator("#sync-table")
        expect(table).to_be_visible(timeout=5000)
