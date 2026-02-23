"""Playwright E2E tests for analytics features (specs/analytics.md).

Validates the full user journey through the analytics dashboard,
including page rendering, Chart.js initialization, controls, and navigation.
"""

import re

import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="session")
def browser_context_args():
    return {"base_url": BASE_URL}


class TestDashboardNavigation:
    """Verify navigation between dashboard and analytics pages."""

    def test_dashboard_loads(self, page: Page):
        """Main dashboard page loads successfully."""
        page.goto(f"{BASE_URL}/")
        expect(page).to_have_title(re.compile("Rsync Log Viewer"))
        page.screenshot(
            path="tests/screenshots/dashboard/step-01-dashboard-loaded.png",
            full_page=True,
        )

    def test_analytics_link_in_nav(self, page: Page):
        """Dashboard header contains Analytics navigation link."""
        page.goto(f"{BASE_URL}/")
        analytics_link = page.locator('nav.header-nav a[href="/analytics"]')
        expect(analytics_link).to_be_visible()
        expect(analytics_link).to_have_text("Analytics")

    def test_navigate_to_analytics(self, page: Page):
        """Clicking Analytics link navigates to /analytics page."""
        page.goto(f"{BASE_URL}/")
        page.click('a[href="/analytics"]')
        expect(page).to_have_url(re.compile(r"/analytics"))
        page.screenshot(
            path="tests/screenshots/analytics/step-01-analytics-page-loaded.png",
            full_page=True,
        )

    def test_settings_link_in_nav(self, page: Page):
        """Settings link still visible alongside Analytics."""
        page.goto(f"{BASE_URL}/")
        settings_link = page.locator('nav.header-nav a[href="/settings"]')
        expect(settings_link).to_be_visible()


class TestAnalyticsPageStructure:
    """Verify the analytics page renders all required sections and controls."""

    def test_analytics_page_loads(self, page: Page):
        """Analytics page returns 200 and renders HTML."""
        response = page.goto(f"{BASE_URL}/analytics")
        assert response.status == 200

    def test_page_title(self, page: Page):
        """Analytics page has correct title."""
        page.goto(f"{BASE_URL}/analytics")
        expect(page).to_have_title(re.compile("Analytics"))

    def test_period_selector_present(self, page: Page):
        """Period selector dropdown with daily/weekly/monthly options exists."""
        page.goto(f"{BASE_URL}/analytics")
        period_select = page.locator("#analytics-period")
        expect(period_select).to_be_visible()

        options = period_select.locator("option")
        texts = [options.nth(i).text_content() for i in range(options.count())]
        assert "Daily" in texts
        assert "Weekly" in texts
        assert "Monthly" in texts

    def test_date_range_picker_present(self, page: Page):
        """Start and end date inputs are present."""
        page.goto(f"{BASE_URL}/analytics")
        start_input = page.locator("#analytics-start")
        end_input = page.locator("#analytics-end")
        expect(start_input).to_be_visible()
        expect(end_input).to_be_visible()
        # Dates should be pre-populated (last 30 days default)
        assert start_input.input_value() != ""
        assert end_input.input_value() != ""

    def test_source_filter_present(self, page: Page):
        """Source filter dropdown exists with 'All Sources' option."""
        page.goto(f"{BASE_URL}/analytics")
        source_select = page.locator("#analytics-source")
        expect(source_select).to_be_visible()
        all_option = source_select.locator('option[value=""]')
        expect(all_option).to_have_text("All Sources")

    def test_update_charts_button(self, page: Page):
        """Update Charts button is present and clickable."""
        page.goto(f"{BASE_URL}/analytics")
        button = page.locator('button:has-text("Update Charts")')
        expect(button).to_be_visible()
        expect(button).to_be_enabled()

    def test_chart_canvases_present(self, page: Page):
        """All 4 Chart.js canvas elements exist."""
        page.goto(f"{BASE_URL}/analytics")
        assert page.locator("#duration-chart").count() == 1
        assert page.locator("#filecount-chart").count() == 1
        assert page.locator("#bytes-chart").count() == 1
        assert page.locator("#success-chart").count() == 1
        page.screenshot(
            path="tests/screenshots/analytics/step-02-chart-canvases.png",
            full_page=True,
        )

    def test_comparison_section_present(self, page: Page):
        """Source comparison section exists."""
        page.goto(f"{BASE_URL}/analytics")
        comparison = page.locator(".analytics-comparison")
        expect(comparison).to_be_visible()
        heading = comparison.locator("h3")
        expect(heading).to_have_text("Source Comparison")

    def test_export_section_present(self, page: Page):
        """Export section with CSV and JSON download links exists."""
        page.goto(f"{BASE_URL}/analytics")
        export_section = page.locator(".analytics-export")
        expect(export_section).to_be_visible()

        csv_link = page.locator("#export-csv")
        json_link = page.locator("#export-json")
        expect(csv_link).to_be_visible()
        expect(json_link).to_be_visible()
        assert "format=csv" in csv_link.get_attribute("href")
        assert "format=json" in json_link.get_attribute("href")


class TestChartJsInitialization:
    """Verify Chart.js is loaded and charts are initialized."""

    def test_chartjs_script_loaded(self, page: Page):
        """Chart.js library is loaded on the analytics page."""
        page.goto(f"{BASE_URL}/analytics")
        # Wait for Chart.js to be available
        result = page.evaluate("typeof Chart !== 'undefined'")
        assert result is True, "Chart.js not loaded"

    def test_charts_initialized_on_page_load(self, page: Page):
        """Charts are initialized after page DOM is ready."""
        page.goto(f"{BASE_URL}/analytics")
        # Give JS time to initialize charts
        page.wait_for_timeout(1000)

        # Check that Chart instances exist on the canvases
        duration_exists = page.evaluate(
            """() => {
                const canvas = document.getElementById('duration-chart');
                return canvas && Chart.getChart(canvas) !== undefined;
            }"""
        )
        assert duration_exists, "Duration chart not initialized"

        filecount_exists = page.evaluate(
            """() => {
                const canvas = document.getElementById('filecount-chart');
                return canvas && Chart.getChart(canvas) !== undefined;
            }"""
        )
        assert filecount_exists, "File count chart not initialized"

        bytes_exists = page.evaluate(
            """() => {
                const canvas = document.getElementById('bytes-chart');
                return canvas && Chart.getChart(canvas) !== undefined;
            }"""
        )
        assert bytes_exists, "Bytes chart not initialized"

        success_exists = page.evaluate(
            """() => {
                const canvas = document.getElementById('success-chart');
                return canvas && Chart.getChart(canvas) !== undefined;
            }"""
        )
        assert success_exists, "Success/failure chart not initialized"

        page.screenshot(
            path="tests/screenshots/analytics/step-03-charts-initialized.png",
            full_page=True,
        )


class TestAnalyticsControls:
    """Verify interactive controls work correctly."""

    def test_period_selector_change(self, page: Page):
        """Changing period selector updates chart data request."""
        page.goto(f"{BASE_URL}/analytics")
        page.wait_for_timeout(500)

        # Change to weekly
        page.select_option("#analytics-period", "weekly")
        assert page.locator("#analytics-period").input_value() == "weekly"

    def test_date_range_change(self, page: Page):
        """Changing date range inputs works."""
        page.goto(f"{BASE_URL}/analytics")
        page.wait_for_timeout(500)

        page.fill("#analytics-start", "2026-01-01")
        page.fill("#analytics-end", "2026-01-31")

        assert page.locator("#analytics-start").input_value() == "2026-01-01"
        assert page.locator("#analytics-end").input_value() == "2026-01-31"

    def test_update_button_triggers_fetch(self, page: Page):
        """Clicking Update Charts triggers API fetch."""
        page.goto(f"{BASE_URL}/analytics")
        page.wait_for_timeout(500)

        # Set a date range and click update
        page.fill("#analytics-start", "2026-01-01")
        page.fill("#analytics-end", "2026-02-28")

        # Listen for network request
        with page.expect_request("**/api/v1/analytics/summary**") as request_info:
            page.click('button:has-text("Update Charts")')

        request = request_info.value
        assert "period=" in request.url
        assert "start=" in request.url
        assert "end=" in request.url

        page.screenshot(
            path="tests/screenshots/analytics/step-04-after-update-click.png",
            full_page=True,
        )


class TestAnalyticsAPI:
    """Verify API endpoints work correctly via browser fetch."""

    def test_summary_api_returns_json(self, page: Page):
        """GET /api/v1/analytics/summary returns valid JSON."""
        response = page.goto(
            f"{BASE_URL}/api/v1/analytics/summary?period=daily&start=2026-01-01&end=2026-02-28"
        )
        assert response.status == 200
        body = page.evaluate("() => document.body.innerText")
        assert '"period"' in body
        assert '"data"' in body

    def test_sources_api_returns_json(self, page: Page):
        """GET /api/v1/analytics/sources returns valid JSON array."""
        response = page.goto(f"{BASE_URL}/api/v1/analytics/sources")
        assert response.status == 200

    def test_export_csv_returns_csv(self, page: Page):
        """GET /api/v1/analytics/export?format=csv returns CSV content."""
        # Use API request context since CSV triggers a download (Content-Disposition: attachment)
        response = page.request.get(f"{BASE_URL}/api/v1/analytics/export?format=csv")
        assert response.status == 200
        assert "text/csv" in response.headers.get("content-type", "")

    def test_export_json_returns_json(self, page: Page):
        """GET /api/v1/analytics/export?format=json returns JSON array."""
        response = page.goto(f"{BASE_URL}/api/v1/analytics/export?format=json")
        assert response.status == 200

    def test_summary_missing_params_returns_422(self, page: Page):
        """GET /api/v1/analytics/summary without required params returns 422."""
        response = page.goto(f"{BASE_URL}/api/v1/analytics/summary")
        assert response.status == 422

    def test_export_invalid_format_returns_400(self, page: Page):
        """GET /api/v1/analytics/export?format=xml returns 400."""
        response = page.goto(f"{BASE_URL}/api/v1/analytics/export?format=xml")
        assert response.status == 400


class TestExportLinks:
    """Verify export download links work correctly."""

    def test_csv_export_link_has_correct_href(self, page: Page):
        """CSV export link points to correct API endpoint."""
        page.goto(f"{BASE_URL}/analytics")
        csv_link = page.locator("#export-csv")
        href = csv_link.get_attribute("href")
        assert href.startswith("/api/v1/analytics/export")
        assert "format=csv" in href

    def test_json_export_link_has_correct_href(self, page: Page):
        """JSON export link points to correct API endpoint."""
        page.goto(f"{BASE_URL}/analytics")
        json_link = page.locator("#export-json")
        href = json_link.get_attribute("href")
        assert href.startswith("/api/v1/analytics/export")
        assert "format=json" in href

    def test_export_links_update_with_filters(self, page: Page):
        """Export links update when date range is changed and form submitted."""
        page.goto(f"{BASE_URL}/analytics")
        page.wait_for_timeout(500)

        page.fill("#analytics-start", "2026-01-15")
        page.fill("#analytics-end", "2026-01-31")
        page.click('button:has-text("Update Charts")')
        page.wait_for_timeout(500)

        csv_href = page.locator("#export-csv").get_attribute("href")
        assert "start=2026-01-15" in csv_href
        assert "end=2026-01-31" in csv_href

        page.screenshot(
            path="tests/screenshots/analytics/step-05-export-links-updated.png",
            full_page=True,
        )


class TestResponsiveLayout:
    """Basic responsive layout checks."""

    def test_desktop_layout(self, page: Page):
        """Analytics page renders correctly at desktop width."""
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(f"{BASE_URL}/analytics")
        page.wait_for_timeout(1000)
        page.screenshot(
            path="tests/screenshots/analytics/step-06-desktop-layout.png",
            full_page=True,
        )
        # Charts should be visible
        expect(page.locator("#duration-chart")).to_be_visible()

    def test_tablet_layout(self, page: Page):
        """Analytics page renders at tablet width without horizontal scroll."""
        page.set_viewport_size({"width": 768, "height": 1024})
        page.goto(f"{BASE_URL}/analytics")
        page.wait_for_timeout(1000)
        page.screenshot(
            path="tests/screenshots/analytics/step-07-tablet-layout.png",
            full_page=True,
        )
        # Page shouldn't have horizontal overflow
        overflow = page.evaluate(
            "document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        assert not overflow, "Page has horizontal scroll at tablet width"

    def test_mobile_layout(self, page: Page):
        """Analytics page renders at mobile width."""
        page.set_viewport_size({"width": 375, "height": 812})
        page.goto(f"{BASE_URL}/analytics")
        page.wait_for_timeout(1000)
        page.screenshot(
            path="tests/screenshots/analytics/step-08-mobile-layout.png",
            full_page=True,
        )
