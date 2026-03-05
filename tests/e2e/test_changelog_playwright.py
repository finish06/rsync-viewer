"""Playwright e2e tests for changelog presentation.

Spec: specs/changelog-presentation.md
Runs against a live instance at http://localhost:8000.

Usage:
    .venv/bin/python3 -m pytest tests/e2e/test_changelog_playwright.py -v
"""

import os
import uuid

import pytest
from playwright.sync_api import Page, expect

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="module")
def test_user():
    """Generate unique test credentials."""
    uid = uuid.uuid4().hex[:8]
    return {
        "username": f"e2e_cl_{uid}",
        "email": f"e2e_cl_{uid}@test.local",
        "password": "TestPassword123!",
    }


@pytest.fixture(scope="module")
def authenticated_context(browser, test_user):
    """Register and log in, return a browser context with auth cookies."""
    context = browser.new_context()
    page = context.new_page()

    # Register
    page.goto(f"{BASE_URL}/register")
    page.wait_for_load_state("networkidle")
    page.fill('input[name="username"]', test_user["username"])
    page.fill('input[name="email"]', test_user["email"])
    page.fill('input[name="password"]', test_user["password"])
    page.click('button[type="submit"]')
    page.wait_for_url("**/login*", timeout=10000)

    # Login
    page.fill('input[name="username"]', test_user["username"])
    page.fill('input[name="password"]', test_user["password"])
    page.click('button[type="submit"]')
    page.wait_for_url("**/", timeout=10000)

    yield context
    context.close()


@pytest.fixture()
def page(authenticated_context):
    """Fresh page in authenticated context."""
    p = authenticated_context.new_page()
    yield p
    p.close()


# Minimal HTML page that loads HTMX + our changelog JS, then fetches the
# changelog list partial from the real server.  This is the key to testing
# the actual JS+HTMX interaction without needing operator-level access to
# the settings page.
_CHANGELOG_HARNESS = """<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="{base}/static/css/styles.css">
</head>
<body>
  <script src="{base}/static/js/htmx.min.js"></script>
  <script src="{base}/static/js/changelog.js"></script>
  <div id="changelog-container"
       hx-get="{base}/htmx/changelog"
       hx-trigger="load"
       hx-swap="innerHTML">
    Loading...
  </div>
</body>
</html>"""


def _load_changelog_harness(page: Page):
    """Load a minimal HTMX-enabled page that fetches the real changelog."""
    # Navigate to the main page first so cookies are sent on the same origin,
    # then set content won't have the cookies.  Instead, navigate to a data
    # URL won't work for same-origin HTMX.  Best approach: use the real
    # index page and inject our harness via JavaScript.
    page.goto(f"{BASE_URL}/")
    page.wait_for_load_state("networkidle")
    # Inject the changelog container and trigger HTMX load
    page.evaluate("""() => {
        // Clear body and inject changelog harness
        document.body.innerHTML = `
          <div id="changelog-container"
               hx-get="/htmx/changelog"
               hx-trigger="load"
               hx-swap="innerHTML">
            Loading...
          </div>
        `;
        // Load our changelog JS
        var script = document.createElement('script');
        script.src = '/static/js/changelog.js';
        document.head.appendChild(script);
        // Tell HTMX to process the new content
        if (window.htmx) htmx.process(document.body);
    }""")
    # Wait for the changelog list to load
    page.wait_for_selector(".changelog-list", timeout=10000)


def _load_changelog_list(page: Page):
    """Load the changelog list partial directly (no JS/HTMX context)."""
    page.goto(f"{BASE_URL}/htmx/changelog")
    page.wait_for_load_state("networkidle")


def _load_changelog_via_settings(page: Page) -> bool:
    """Try to load changelog via settings page. Returns False if 403."""
    page.goto(f"{BASE_URL}/settings")
    page.wait_for_load_state("networkidle")
    if "403" in page.content() or "Requires operator" in page.content():
        return False
    changelog_tab = page.locator("text=Changelog")
    if changelog_tab.count() > 0:
        changelog_tab.first.click()
        page.wait_for_selector(".changelog-list", timeout=10000)
        return True
    return False


# ── Structure & Styling Tests (raw partial, no JS needed) ────────────────


class TestChangelogStructure:
    """Tests that verify HTML structure of the changelog partials."""

    def test_tc001_version_headers_present(self, page: Page):
        """TC-001: Changelog has version headers with version numbers."""
        _load_changelog_list(page)
        headers = page.locator(".changelog-version-header")
        assert headers.count() > 0
        expect(headers.first.locator("strong")).to_be_visible()

    def test_tc001_dates_shown(self, page: Page):
        """TC-001: Version headers include date."""
        _load_changelog_list(page)
        assert page.locator(".changelog-version-date").count() > 0

    def test_tc001_current_badge(self, page: Page):
        """TC-001: Current version shows 'Current' badge."""
        _load_changelog_list(page)
        badge = page.locator(".badge-current")
        if badge.count() > 0:
            expect(badge.first).to_contain_text("Current")

    def test_tc002_section_badges(self, page: Page):
        """TC-002: Section headers are color-coded badges."""
        _load_changelog_list(page)
        version = page.locator(".changelog-version-header strong").first.text_content()
        page.goto(f"{BASE_URL}/htmx/changelog/{version}")
        page.wait_for_load_state("networkidle")
        badges = page.locator(".changelog-section-badge")
        assert badges.count() > 0
        html = page.content()
        assert any(
            cls in html
            for cls in [
                "badge-added",
                "badge-fixed",
                "badge-changed",
                "badge-removed",
                "badge-docs",
                "badge-default",
            ]
        )

    def test_tc003_no_raw_markdown(self, page: Page):
        """TC-003: No raw **bold** markers in rendered items."""
        _load_changelog_list(page)
        version = page.locator(".changelog-version-header strong").first.text_content()
        page.goto(f"{BASE_URL}/htmx/changelog/{version}")
        page.wait_for_load_state("networkidle")
        items = page.locator(".changelog-items li")
        for i in range(min(items.count(), 10)):
            text = items.nth(i).text_content()
            assert "**" not in text, f"Raw bold markdown: {text}"

    def test_ac007_no_inline_styles_list(self, page: Page):
        """AC-007: No style= in changelog list."""
        _load_changelog_list(page)
        assert page.locator(".changelog-list [style]").count() == 0

    def test_ac007_no_inline_styles_detail(self, page: Page):
        """AC-007: No style= in changelog detail."""
        _load_changelog_list(page)
        version = page.locator(".changelog-version-header strong").first.text_content()
        page.goto(f"{BASE_URL}/htmx/changelog/{version}")
        page.wait_for_load_state("networkidle")
        assert page.locator(".changelog-detail [style]").count() == 0

    def test_ac005_chevrons_present(self, page: Page):
        """AC-005: Chevron indicators present."""
        _load_changelog_list(page)
        assert page.locator(".changelog-chevron").count() > 0

    def test_ac006_max_five_by_default(self, page: Page):
        """AC-006: At most 5 versions shown by default."""
        _load_changelog_list(page)
        count = page.locator(".changelog-version-header").count()
        assert count <= 5

    def test_ac006_show_all(self, page: Page):
        """AC-006: show_all=true returns all versions."""
        page.goto(f"{BASE_URL}/htmx/changelog")
        page.wait_for_load_state("networkidle")
        count_default = page.locator(".changelog-version-header").count()

        page.goto(f"{BASE_URL}/htmx/changelog?show_all=true")
        page.wait_for_load_state("networkidle")
        count_all = page.locator(".changelog-version-header").count()
        if count_all <= 5:
            pytest.skip("Fewer than 6 versions")
        assert count_all > count_default

    def test_css_classes_in_detail(self, page: Page):
        """AC-007: Detail uses CSS classes for structure."""
        _load_changelog_list(page)
        version = page.locator(".changelog-version-header strong").first.text_content()
        page.goto(f"{BASE_URL}/htmx/changelog/{version}")
        page.wait_for_load_state("networkidle")
        assert page.locator(".changelog-detail").count() > 0
        assert page.locator(".changelog-section").count() > 0
        assert page.locator(".changelog-items").count() > 0


# ── Interaction Tests (full HTMX+JS context) ────────────────────────────


class TestChangelogInteraction:
    """Tests that verify JS+HTMX click-to-expand behavior.

    These run inside a harness page with HTMX and changelog.js loaded,
    so they test the real user experience.
    """

    def test_tc004_click_expands_version(self, page: Page):
        """TC-004: Clicking a collapsed version fetches content and expands."""
        _load_changelog_harness(page)

        headers = page.locator(".changelog-version-header")
        if headers.count() < 2:
            pytest.skip("Need at least 2 versions")

        # Pick a non-current (second) version
        second_header = headers.nth(1)
        second_content = page.locator(".changelog-content").nth(1)

        # Should start collapsed
        assert "expanded" not in (second_content.get_attribute("class") or "")

        # Click to expand
        second_header.click()

        # Wait for section badges to appear (proves HTMX fetched and rendered)
        second_content.locator(".changelog-section-badge").first.wait_for(timeout=8000)

        # Content div should be expanded
        assert "expanded" in (second_content.get_attribute("class") or "")

    def test_tc004_click_collapses_expanded_version(self, page: Page):
        """TC-004: Clicking an expanded version collapses it client-side."""
        _load_changelog_harness(page)

        headers = page.locator(".changelog-version-header")
        if headers.count() < 2:
            pytest.skip("Need at least 2 versions")

        second_header = headers.nth(1)
        second_content = page.locator(".changelog-content").nth(1)

        # Expand first
        second_header.click()
        # Wait for the section badges to appear (content loaded)
        second_content.locator(".changelog-section-badge").first.wait_for(timeout=5000)
        assert "expanded" in (second_content.get_attribute("class") or "")

        # Click again to collapse
        second_header.click()
        page.wait_for_timeout(400)

        assert "expanded" not in (second_content.get_attribute("class") or "")

    def test_tc004_re_expand_no_refetch(self, page: Page):
        """TC-004: Re-expanding already-loaded content doesn't re-fetch."""
        _load_changelog_harness(page)

        headers = page.locator(".changelog-version-header")
        if headers.count() < 2:
            pytest.skip("Need at least 2 versions")

        second_header = headers.nth(1)
        second_content = page.locator(".changelog-content").nth(1)

        # Expand (triggers HTMX fetch)
        second_header.click()
        # Wait for content to load — use state="attached" because the badge may
        # not be "visible" if CSS overflow clips it during transition
        second_content.locator(".changelog-section-badge").first.wait_for(
            timeout=5000, state="attached"
        )

        # Collapse
        second_header.click()
        page.wait_for_timeout(300)
        assert "expanded" not in (second_content.get_attribute("class") or "")

        # Re-expand — should happen instantly (no network request)
        request_count = {"value": 0}

        def on_request(request):
            if "htmx/changelog/" in request.url:
                request_count["value"] += 1

        page.on("request", on_request)

        second_header.click()
        page.wait_for_timeout(500)

        assert "expanded" in (second_content.get_attribute("class") or "")
        assert request_count["value"] == 0, "Should not re-fetch already loaded content"

    def test_tc004_chevron_rotates(self, page: Page):
        """TC-004: Chevron rotates on expand/collapse."""
        _load_changelog_harness(page)

        headers = page.locator(".changelog-version-header")
        if headers.count() < 2:
            pytest.skip("Need at least 2 versions")

        second_content = page.locator(".changelog-content").nth(1)
        chevron = headers.nth(1).locator(".changelog-chevron")
        assert "expanded" not in (chevron.get_attribute("class") or "")

        # Click to expand and wait for content to load
        headers.nth(1).click()
        second_content.locator(".changelog-section-badge").first.wait_for(timeout=8000)
        assert "expanded" in (chevron.get_attribute("class") or "")

        # Click to collapse
        headers.nth(1).click()
        page.wait_for_timeout(400)
        assert "expanded" not in (chevron.get_attribute("class") or "")

    def test_tc001_current_version_auto_expanded(self, page: Page):
        """TC-001: Current version auto-expands on load."""
        _load_changelog_harness(page)

        # Find the version with the Current badge
        current_badge = page.locator(".badge-current")
        if current_badge.count() == 0:
            pytest.skip(
                "No current version badge — app version may not match changelog"
            )

        # The current version's changelog-content sibling should be expanded.
        # The template renders it with the expanded class and hx-trigger="click, load"
        # fetches the detail on load.
        current_version_div = current_badge.locator(
            "xpath=ancestor::div[contains(@class, 'changelog-version')]"
        )
        content = current_version_div.locator(".changelog-content")

        # Wait for detail content to be fetched via the "load" trigger
        content.locator(".changelog-section-badge").first.wait_for(timeout=8000)
        assert "expanded" in (content.get_attribute("class") or "")

    def test_tc005_show_older_versions_interactive(self, page: Page):
        """TC-005: 'Show older versions' button loads more via HTMX."""
        _load_changelog_harness(page)

        show_more = page.locator("text=Show older versions")
        if show_more.count() == 0:
            pytest.skip("Fewer than 6 versions")

        count_before = page.locator(".changelog-version-header").count()
        show_more.click()
        # Wait for the new list to load (button disappears after swap)
        page.wait_for_selector(
            "text=Show older versions", state="detached", timeout=5000
        )

        count_after = page.locator(".changelog-version-header").count()
        assert count_after > count_before


# ── Screenshots ──────────────────────────────────────────────────────────


class TestChangelogScreenshots:
    """Capture screenshots for visual verification."""

    def test_screenshot_list(self, page: Page):
        _load_changelog_list(page)
        page.screenshot(
            path="tests/screenshots/changelog/step-01-initial-load.png",
            full_page=True,
        )

    def test_screenshot_detail(self, page: Page):
        _load_changelog_list(page)
        version = page.locator(".changelog-version-header strong").first.text_content()
        page.goto(f"{BASE_URL}/htmx/changelog/{version}")
        page.wait_for_load_state("networkidle")
        page.screenshot(
            path="tests/screenshots/changelog/step-02-section-badges.png",
            full_page=True,
        )

    def test_screenshot_expanded_interactive(self, page: Page):
        """Screenshot of an expanded version via real click interaction."""
        _load_changelog_harness(page)
        headers = page.locator(".changelog-version-header")
        if headers.count() < 2:
            pytest.skip("Need at least 2 versions")
        headers.nth(1).click()
        page.wait_for_timeout(1000)
        page.screenshot(
            path="tests/screenshots/changelog/step-03-accordion-expanded.png",
            full_page=True,
        )


class TestChangelogViaSettings:
    """Test changelog tab in settings page (requires operator+ role)."""

    def test_settings_changelog_tab(self, page: Page):
        success = _load_changelog_via_settings(page)
        if not success:
            pytest.skip("User does not have operator role")
        headers = page.locator(".changelog-version-header")
        assert headers.count() > 0
        page.screenshot(
            path="tests/screenshots/changelog/step-04-settings-tab.png",
            full_page=True,
        )
