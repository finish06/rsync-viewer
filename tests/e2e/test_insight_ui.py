"""E2E tests for the Insight UI SPA — specs/insight-ui.md.

TC-001 (overview glance), TC-008 (deep link while logged out), TC-009 (mobile).
Screenshots: tests/screenshots/insight-ui/
"""

import re
import uuid
from pathlib import Path

from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL, ingest_sync_log

SCREENSHOTS = (
    Path(__file__).resolve().parents[2] / "tests" / "screenshots" / "insight-ui"
)


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
            "data-status", re.compile(r"passing|failing|unknown|disabled")
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
            "href", "/app/settings"
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


class TestTransfersAndTrends:
    def test_tc003_filtered_transfers_via_url(
        self, admin_page: Page, admin_api_key: str
    ):
        """AC-009, AC-011, AC-012: filters restored from the URL and applied."""
        source = f"e2e-xfer-{uuid.uuid4().hex[:8]}"
        ingest_sync_log(admin_api_key, source)

        admin_page.goto(f"{BASE_URL}/app/transfers?source={source}&range=30d")
        admin_page.wait_for_load_state("networkidle")

        expect(admin_page.get_by_role("button", name="30d")).to_have_attribute(
            "aria-pressed", "true"
        )
        day = admin_page.get_by_test_id("transfer-day").first
        expect(day).to_contain_text("Today")
        expect(admin_page.get_by_test_id("transfer-source")).to_have_count(1)
        expect(admin_page.get_by_test_id("transfer-source").first).to_contain_text(
            source
        )

        admin_page.reload()
        admin_page.wait_for_load_state("networkidle")
        expect(admin_page.get_by_test_id("transfer-source").first).to_contain_text(
            source
        )
        _shot(admin_page, "step-07-transfers-filtered")

    def test_tc004_trends_source_filter(self, admin_page: Page, admin_api_key: str):
        """AC-013, AC-014: four charts; clicking a source row filters and updates URL."""
        source = f"e2e-trend-{uuid.uuid4().hex[:8]}"
        ingest_sync_log(admin_api_key, source)

        admin_page.goto(f"{BASE_URL}/app/trends")
        admin_page.wait_for_load_state("networkidle")
        expect(admin_page.get_by_test_id("trend-chart")).to_have_count(4)

        row = admin_page.get_by_test_id("source-row").filter(has_text=source).first
        expect(row).to_be_visible(timeout=15000)
        row.click()
        admin_page.wait_for_url(f"**/app/trends?source={source}")
        expect(row).to_have_attribute("aria-selected", "true")
        _shot(admin_page, "step-03-trends")


class TestMediaAndUptime:
    def test_tc005_new_media(self, admin_page: Page, admin_api_key: str):
        """AC-016–AC-019: media paths become titles; re-ingest never duplicates."""
        import requests

        source = f"e2e-media-{uuid.uuid4().hex[:8]}"
        show = f"E2E Show {uuid.uuid4().hex[:6]}"
        movie = f"E2E Movie {uuid.uuid4().hex[:6]}"
        raw = (
            "receiving file list ... done\n"
            f"{movie} (2004)/{movie}.2004.Bluray-1080p.mkv\n"
            f"{show} (2022)/Season 02/{show} - S02E03 - Pilot.mkv\n"
            "\nsent 1.20K bytes  received 1.10G bytes  20.00M bytes/sec\n"
            "total size is 3.30G  speedup is 3.00\n"
        )
        now = _utc_now_iso()
        for _ in range(2):
            resp = requests.post(
                f"{BASE_URL}/api/v1/sync-logs",
                json={
                    "source_name": source,
                    "start_time": now,
                    "end_time": now,
                    "raw_content": raw,
                    "exit_code": 0,
                },
                headers={"X-API-Key": admin_api_key},
                timeout=10,
            )
            resp.raise_for_status()

        admin_page.goto(f"{BASE_URL}/app/media")
        admin_page.wait_for_load_state("networkidle")
        show_item = admin_page.get_by_test_id("show-item").filter(has_text=show)
        expect(show_item).to_have_count(1)
        expect(show_item).to_contain_text("1 new")
        expect(show_item.get_by_role("link", name="S02E03")).to_be_visible()
        movie_item = admin_page.get_by_test_id("movie-item").filter(has_text=movie)
        expect(movie_item).to_have_count(1)
        expect(movie_item).to_contain_text("(2004)")
        _shot(admin_page, "step-04-media")

    def test_tc006_uptime_history(self, admin_page: Page):
        """AC-003, AC-004: status header, timeline cells, latency chart or empty note."""
        admin_page.goto(f"{BASE_URL}/app/uptime")
        admin_page.wait_for_load_state("networkidle")
        page_root = admin_page.get_by_test_id("uptime-page")
        expect(page_root).to_be_visible()
        if admin_page.get_by_test_id("uptime-header").count():
            expect(admin_page.get_by_test_id("uptime-stats")).to_be_visible()
            expect(admin_page.get_by_test_id("timeline-cell").first).to_be_visible()
        _shot(admin_page, "step-05-uptime")


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
