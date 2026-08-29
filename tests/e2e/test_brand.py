"""E2E: brand assets are served and used — docs/brand/README.md.

Screenshots: tests/screenshots/brand/
"""

from pathlib import Path

from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL

SCREENSHOTS = Path(__file__).resolve().parents[2] / "tests" / "screenshots" / "brand"


def _shot(page: Page, name: str) -> None:
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SCREENSHOTS / f"{name}.png"), full_page=False)


class TestBrand:
    def test_header_logo_and_favicon_in_spa(self, admin_page: Page):
        admin_page.goto(f"{BASE_URL}/app")
        admin_page.wait_for_load_state("networkidle")
        logo = admin_page.locator("header img[src='/static/app/favicon.svg']")
        expect(logo).to_be_visible()
        assert (
            admin_page.evaluate(
                "() => document.querySelector(\"header img[src='/static/app/favicon.svg']\").naturalWidth"
            )
            > 0
        )
        icons = admin_page.locator("link[rel='icon']")
        expect(icons).to_have_count(2)
        expect(admin_page.locator("link[rel='manifest']")).to_have_attribute(
            "href", "/static/app/manifest.webmanifest"
        )
        _shot(admin_page, "step-01-spa-header")

    def test_favicon_on_server_rendered_pages(self, page: Page):
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")
        expect(
            page.locator("link[rel='icon'][type='image/svg+xml']")
        ).to_have_attribute("href", "/static/app/favicon.svg")
        response = page.request.get(f"{BASE_URL}/static/app/favicon.ico")
        assert response.ok
        assert response.headers.get("content-type", "").startswith("image/")
        _shot(page, "step-02-login-favicon")
