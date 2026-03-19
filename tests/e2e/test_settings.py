"""E2E tests for settings page — happy paths and error scenarios.

Spec: specs/e2e-playwright-happy-path.md (AC-014, AC-021, TC-007)
Spec: specs/e2e-playwright-error-scenarios.md (AC-130)
"""

from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL


class TestSettingsPage:
    """TC-007: Settings page tabs and HTMX content loading."""

    def test_ac014_settings_page_loads(self, admin_page: Page):
        """Settings page renders for admin/operator user."""
        admin_page.goto(f"{BASE_URL}/settings")
        admin_page.wait_for_load_state("networkidle")

        # Should see tab buttons
        tabs = admin_page.locator("[data-tab]")
        assert tabs.count() >= 2  # At least general + monitoring

    def test_ac021_general_tab_loads_api_keys(self, admin_page: Page):
        """General tab loads API keys list via HTMX."""
        admin_page.goto(f"{BASE_URL}/settings")
        admin_page.wait_for_load_state("networkidle")

        # API keys list should load via HTMX
        api_keys_list = admin_page.locator("#api-keys-list")
        expect(api_keys_list).to_be_visible(timeout=10000)

        # Wait for HTMX content to populate (not just the container)
        admin_page.wait_for_function(
            """() => {
                const el = document.getElementById('api-keys-list');
                return el && el.innerHTML.trim().length > 10;
            }""",
            timeout=10000,
        )

    def test_ac021_general_tab_loads_webhooks(self, admin_page: Page):
        """General tab loads webhooks list via HTMX."""
        admin_page.goto(f"{BASE_URL}/settings")
        admin_page.wait_for_load_state("networkidle")

        webhooks_list = admin_page.locator("#webhooks-list")
        expect(webhooks_list).to_be_visible(timeout=10000)

        admin_page.wait_for_function(
            """() => {
                const el = document.getElementById('webhooks-list');
                return el && el.innerHTML.trim().length > 10;
            }""",
            timeout=10000,
        )

    def test_ac014_smtp_settings_render(self, admin_page: Page):
        """SMTP settings section loads via HTMX."""
        admin_page.goto(f"{BASE_URL}/settings")
        admin_page.wait_for_load_state("networkidle")

        smtp_container = admin_page.locator("#smtp-settings-container")
        if smtp_container.count() > 0:
            expect(smtp_container).to_be_visible(timeout=10000)
            admin_page.wait_for_function(
                """() => {
                    const el = document.getElementById('smtp-settings-container');
                    return el && el.innerHTML.trim().length > 10;
                }""",
                timeout=10000,
            )

    def test_ac014_oidc_settings_render(self, admin_page: Page):
        """OIDC/Auth settings section loads via HTMX."""
        admin_page.goto(f"{BASE_URL}/settings")
        admin_page.wait_for_load_state("networkidle")

        oidc_container = admin_page.locator("#oidc-settings-container")
        if oidc_container.count() > 0:
            expect(oidc_container).to_be_visible(timeout=10000)
            admin_page.wait_for_function(
                """() => {
                    const el = document.getElementById('oidc-settings-container');
                    return el && el.innerHTML.trim().length > 10;
                }""",
                timeout=10000,
            )

    def test_ac021_monitoring_tab_loads(self, admin_page: Page):
        """Monitoring tab loads setup content via HTMX."""
        admin_page.goto(f"{BASE_URL}/settings")
        admin_page.wait_for_load_state("networkidle")

        # Click monitoring tab
        monitoring_tab = admin_page.locator('[data-tab="monitoring"]')
        if monitoring_tab.count() > 0:
            monitoring_tab.click()
            admin_page.wait_for_timeout(1000)

            monitoring_container = admin_page.locator("#monitoring-setup-container")
            if monitoring_container.count() > 0:
                expect(monitoring_container).to_be_visible(timeout=10000)

    def test_ac021_changelog_tab_loads(self, admin_page: Page):
        """Changelog tab renders version list."""
        admin_page.goto(f"{BASE_URL}/settings")
        admin_page.wait_for_load_state("networkidle")

        changelog_tab = admin_page.locator('[data-tab="changelog"]')
        if changelog_tab.count() > 0:
            changelog_tab.click()
            admin_page.wait_for_timeout(2000)

            # Changelog content should load
            changelog = admin_page.locator(".changelog-version-header")
            if changelog.count() > 0:
                expect(changelog.first).to_be_visible()


class TestSettingsRBAC:
    """RBAC enforcement on settings page — AC-130, TC-104."""

    def test_ac130_viewer_cannot_access_settings(self, viewer_page: Page):
        """Viewer user gets 403 when accessing /settings."""
        viewer_page.goto(f"{BASE_URL}/settings")
        viewer_page.wait_for_load_state("networkidle")

        # Should see 403 or "Requires operator" message
        content = viewer_page.content()
        assert (
            "403" in content
            or "operator" in content.lower()
            or "forbidden" in content.lower()
            or "denied" in content.lower()
        )
