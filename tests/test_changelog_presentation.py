"""Tests for changelog presentation improvements.

Spec: specs/changelog-presentation.md
"""

import pytest
from unittest.mock import patch

from app.schemas.changelog import ChangelogItem, ChangelogVersion
from app.services.changelog_parser import parse_changelog
from app.templating import render_changelog_md


# ── Sample data ──────────────────────────────────────────────────────────

CHANGELOG_WITH_NESTED = """\
# Changelog

## [2.0.0] - 2026-03-03

### Added

- New dashboard with analytics
  - Chart.js integration
  - Export to CSV
- API v2 endpoints

### Fixed

- Login redirect loop

## [1.9.0] - 2026-03-01

### Changed

- Updated dependencies
"""

CHANGELOG_MANY_VERSIONS = """\
# Changelog

## [2.0.0] - 2026-03-03

### Added

- Feature A

## [1.9.0] - 2026-03-01

### Added

- Feature B

## [1.8.0] - 2026-02-28

### Fixed

- Bug C

## [1.7.0] - 2026-02-24

### Added

- Feature D

## [1.6.0] - 2026-02-23

### Fixed

- Bug E

## [1.5.0] - 2026-02-20

### Added

- Feature F

## [1.0.0] - 2026-01-26

### Added

- Initial release
"""


def _make_version(
    version: str,
    date: str | None = None,
    sections: dict[str, list[ChangelogItem]] | None = None,
) -> ChangelogVersion:
    return ChangelogVersion(
        version=version,
        date=date,
        sections=sections or {"Added": [ChangelogItem(text="Something")]},
    )


# ── AC-001: Version header hierarchy ────────────────────────────────────


class TestAC001VersionHeaderHierarchy:
    @pytest.mark.anyio
    async def test_ac001_version_header_hierarchy(self, client):
        """Version headers show version, date, and Current badge."""
        versions = [
            _make_version("2.0.0", "2026-03-03"),
            _make_version("1.9.0", "2026-03-01"),
        ]
        with (
            patch("app.routes.pages.parse_changelog", return_value=versions),
            patch("app.routes.pages.get_settings") as mock_settings,
        ):
            mock_settings.return_value.app_version = "2.0.0"
            response = await client.get("/htmx/changelog")
            html = response.text
            assert "2.0.0" in html
            assert "2026-03-03" in html
            assert "badge-current" in html
            assert "Current" in html
            assert "1.9.0" in html


# ── AC-002: Section badges ──────────────────────────────────────────────


class TestAC002SectionBadges:
    @pytest.mark.anyio
    async def test_ac002_section_badges(self, client):
        """Section headers render as color-coded badges."""
        version = ChangelogVersion(
            version="2.0.0",
            date="2026-03-03",
            sections={
                "Added": [ChangelogItem(text="New feature")],
                "Fixed": [ChangelogItem(text="Bug fix")],
                "Changed": [ChangelogItem(text="Update")],
                "Removed": [ChangelogItem(text="Old thing")],
                "Documentation": [ChangelogItem(text="Docs")],
                "GA Promotion": [ChangelogItem(text="Promoted")],
                "Security": [ChangelogItem(text="Patch")],
            },
        )
        with patch("app.routes.pages.parse_changelog", return_value=[version]):
            response = await client.get("/htmx/changelog/2.0.0")
            html = response.text
            assert "badge-added" in html
            assert "badge-fixed" in html
            assert "badge-changed" in html
            assert "badge-removed" in html
            assert "badge-docs" in html
            assert "badge-promotion" in html
            assert "badge-default" in html  # Security -> default


# ── AC-003: Markdown rendering ──────────────────────────────────────────


class TestAC003MarkdownRendering:
    def test_ac003_bold_rendered(self):
        """Bold markdown converts to <strong>."""
        result = render_changelog_md("This is **bold** text")
        assert "<strong>bold</strong>" in result

    def test_ac003_code_rendered(self):
        """Inline code converts to <code>."""
        result = render_changelog_md("Use `some_func()` here")
        assert "<code>some_func()</code>" in result

    def test_ac003_link_rendered(self):
        """Markdown links convert to <a> tags."""
        result = render_changelog_md("See [docs](https://example.com)")
        assert '<a href="https://example.com">docs</a>' in result

    def test_ac003_xss_prevention(self):
        """Script tags are escaped, not rendered as HTML."""
        result = render_changelog_md('<script>alert("xss")</script>')
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_ac003_plain_text_unchanged(self):
        """Plain text passes through without modification."""
        result = render_changelog_md("Just plain text")
        assert str(result) == "Just plain text"

    @pytest.mark.anyio
    async def test_ac003_markdown_rendered_in_detail(self, client):
        """Markdown items render as HTML in the detail partial."""
        version = ChangelogVersion(
            version="2.0.0",
            date="2026-03-03",
            sections={
                "Added": [ChangelogItem(text="Support for **bold** and `code`")],
            },
        )
        with patch("app.routes.pages.parse_changelog", return_value=[version]):
            response = await client.get("/htmx/changelog/2.0.0")
            html = response.text
            assert "<strong>bold</strong>" in html
            assert "<code>code</code>" in html


# ── AC-004: Auto-expand current version ─────────────────────────────────


class TestAC004AutoExpand:
    @pytest.mark.anyio
    async def test_ac004_current_version_auto_expands(self, client):
        """Current version has hx-trigger='load' to auto-expand."""
        versions = [
            _make_version("2.0.0", "2026-03-03"),
            _make_version("1.9.0", "2026-03-01"),
        ]
        with (
            patch("app.routes.pages.parse_changelog", return_value=versions),
            patch("app.routes.pages.get_settings") as mock_settings,
        ):
            mock_settings.return_value.app_version = "2.0.0"
            response = await client.get("/htmx/changelog")
            html = response.text
            assert "load" in html
            assert 'hx-trigger="click, load"' in html


# ── AC-005: Accordion CSS classes ────────────────────────────────────────


class TestAC005AccordionCSS:
    @pytest.mark.anyio
    async def test_ac005_accordion_css_classes(self, client):
        """Accordion uses CSS classes, not inline display styles."""
        versions = [
            _make_version("2.0.0", "2026-03-03"),
            _make_version("1.9.0", "2026-03-01"),
        ]
        with (
            patch("app.routes.pages.parse_changelog", return_value=versions),
            patch("app.routes.pages.get_settings") as mock_settings,
        ):
            mock_settings.return_value.app_version = "2.0.0"
            response = await client.get("/htmx/changelog")
            html = response.text
            assert "changelog-content" in html
            assert "changelog-chevron" in html


# ── AC-006: Pagination ──────────────────────────────────────────────────


class TestAC006Pagination:
    @pytest.mark.anyio
    async def test_ac006_pagination_default_five(self, client):
        """Only first 5 versions shown by default."""
        versions = parse_changelog(content=CHANGELOG_MANY_VERSIONS)
        with (
            patch("app.routes.pages.parse_changelog", return_value=versions),
            patch("app.routes.pages.get_settings") as mock_settings,
        ):
            mock_settings.return_value.app_version = "2.0.0"
            response = await client.get("/htmx/changelog")
            html = response.text
            # Should show first 5 versions
            assert "2.0.0" in html
            assert "1.9.0" in html
            assert "1.8.0" in html
            assert "1.7.0" in html
            assert "1.6.0" in html
            # Should NOT show versions beyond 5
            assert "1.5.0" not in html
            assert "1.0.0" not in html
            # Should show the "Show older versions" button
            assert "Show older versions" in html

    @pytest.mark.anyio
    async def test_ac006_show_all(self, client):
        """All versions shown when show_all=true."""
        versions = parse_changelog(content=CHANGELOG_MANY_VERSIONS)
        with (
            patch("app.routes.pages.parse_changelog", return_value=versions),
            patch("app.routes.pages.get_settings") as mock_settings,
        ):
            mock_settings.return_value.app_version = "2.0.0"
            response = await client.get("/htmx/changelog?show_all=true")
            html = response.text
            assert "2.0.0" in html
            assert "1.5.0" in html
            assert "1.0.0" in html
            assert "Show older versions" not in html


# ── AC-007: No inline styles ────────────────────────────────────────────


class TestAC007NoInlineStyles:
    @pytest.mark.anyio
    async def test_ac007_no_inline_styles_in_list(self, client):
        """changelog_list.html has no style= attributes."""
        versions = [_make_version("2.0.0", "2026-03-03")]
        with (
            patch("app.routes.pages.parse_changelog", return_value=versions),
            patch("app.routes.pages.get_settings") as mock_settings,
        ):
            mock_settings.return_value.app_version = "2.0.0"
            response = await client.get("/htmx/changelog")
            assert "style=" not in response.text

    @pytest.mark.anyio
    async def test_ac007_no_inline_styles_in_detail(self, client):
        """changelog_detail.html has no style= attributes."""
        version = _make_version("2.0.0", "2026-03-03")
        with patch("app.routes.pages.parse_changelog", return_value=[version]):
            response = await client.get("/htmx/changelog/2.0.0")
            assert "style=" not in response.text


# ── AC-008: Nested sub-lists ────────────────────────────────────────────


class TestAC008NestedSublists:
    def test_ac008_nested_sublists_parsed(self):
        """Parser creates ChangelogItem with children for indented sub-items."""
        versions = parse_changelog(content=CHANGELOG_WITH_NESTED)
        v200 = next(v for v in versions if v.version == "2.0.0")
        added = v200.sections["Added"]
        assert len(added) == 2
        # First item has children
        assert added[0].text == "New dashboard with analytics"
        assert len(added[0].children) == 2
        assert added[0].children[0] == "Chart.js integration"
        assert added[0].children[1] == "Export to CSV"
        # Second item has no children
        assert added[1].text == "API v2 endpoints"
        assert added[1].children == []

    @pytest.mark.anyio
    async def test_ac008_nested_sublists_rendered(self, client):
        """Nested sub-items render as <ul class='changelog-nested-list'>."""
        version = ChangelogVersion(
            version="2.0.0",
            date="2026-03-03",
            sections={
                "Added": [
                    ChangelogItem(
                        text="Dashboard",
                        children=["Charts", "Export"],
                    ),
                ],
            },
        )
        with patch("app.routes.pages.parse_changelog", return_value=[version]):
            response = await client.get("/htmx/changelog/2.0.0")
            html = response.text
            assert "changelog-nested-list" in html
            assert "Charts" in html
            assert "Export" in html
