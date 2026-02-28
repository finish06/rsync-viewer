"""Tests for changelog viewer feature.

Spec: specs/changelog-viewer.md
Plan: docs/plans/changelog-viewer-plan.md
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from app.services.changelog_parser import parse_changelog
from app.schemas.changelog import ChangelogVersion


# ── Sample CHANGELOG.md content for tests ──────────────────────────────────


VALID_CHANGELOG = """\
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- CI/CD: Docker image build and push to self-hosted registry

### Fixed

- Fix ruff format issues in app/middleware.py

## [1.7.0] - 2026-02-24

### Added

- Development & deployment setup guide
- Architecture diagram with Mermaid

### Fixed

- Isolate Playwright e2e tests from pytest-asyncio

### Changed

- M6 Observability milestone marked COMPLETE

## [1.6.0] - 2026-02-23

### Added

- Prometheus `/metrics` endpoint with sync, API, and application health metrics
- Data retention service with configurable auto-cleanup

## [1.5.0] - 2026-02-23

### Added

- Rate limiting with slowapi

### Security

- API key hashing with bcrypt

### Deprecated

- Old SHA-256 key hashing

### Removed

- Legacy key format support

### Documentation

- Add security hardening spec

## [1.0.0] - 2026-01-26

### Added

- Initial project files
"""

EMPTY_CHANGELOG = ""

MALFORMED_CHANGELOG = """\
This is not a valid changelog.
No version headers here.
Just random text.
"""

CHANGELOG_NO_UNRELEASED = """\
# Changelog

## [1.2.0] - 2026-02-20

### Added

- Some feature

## [1.0.0] - 2026-01-26

### Added

- Initial release
"""

CHANGELOG_EMPTY_UNRELEASED = """\
# Changelog

## [Unreleased]

## [1.0.0] - 2026-01-26

### Added

- Initial release
"""


# ── Parser Tests (AC-002, AC-004, AC-007, AC-008) ──────────────────────────


class TestChangelogParser:
    """TASK-001: Changelog parser tests for valid CHANGELOG.md."""

    def test_ac002_parse_versions_with_dates(self):
        """AC-002: Each version has version number and date."""
        versions = parse_changelog(content=VALID_CHANGELOG)
        # Filter out Unreleased
        released = [v for v in versions if v.version != "Unreleased"]
        assert len(released) == 4
        assert released[0].version == "1.7.0"
        assert released[0].date == "2026-02-24"
        assert released[1].version == "1.6.0"
        assert released[1].date == "2026-02-23"

    def test_ac004_grouped_change_sections(self):
        """AC-004: Changes grouped by section (Added, Fixed, Changed)."""
        versions = parse_changelog(content=VALID_CHANGELOG)
        v170 = next(v for v in versions if v.version == "1.7.0")
        assert "Added" in v170.sections
        assert "Fixed" in v170.sections
        assert "Changed" in v170.sections
        assert len(v170.sections["Added"]) == 2
        assert len(v170.sections["Fixed"]) == 1
        assert len(v170.sections["Changed"]) == 1

    def test_ac007_unreleased_section(self):
        """AC-007: Unreleased section parsed and at the top."""
        versions = parse_changelog(content=VALID_CHANGELOG)
        assert versions[0].version == "Unreleased"
        assert versions[0].date is None
        assert "Added" in versions[0].sections
        assert "Fixed" in versions[0].sections

    def test_ac008_all_keep_a_changelog_sections(self):
        """AC-008: Parser handles Added, Changed, Deprecated, Removed, Fixed, Security, Documentation."""
        versions = parse_changelog(content=VALID_CHANGELOG)
        v150 = next(v for v in versions if v.version == "1.5.0")
        assert "Added" in v150.sections
        assert "Security" in v150.sections
        assert "Deprecated" in v150.sections
        assert "Removed" in v150.sections
        assert "Documentation" in v150.sections

    def test_ac002_versions_ordered_most_recent_first(self):
        """AC-002: Versions are ordered most recent first."""
        versions = parse_changelog(content=VALID_CHANGELOG)
        # Unreleased first, then descending by version
        assert versions[0].version == "Unreleased"
        assert versions[1].version == "1.7.0"
        assert versions[-1].version == "1.0.0"

    def test_parse_returns_changelog_version_models(self):
        """Parser returns list of ChangelogVersion Pydantic models."""
        versions = parse_changelog(content=VALID_CHANGELOG)
        assert all(isinstance(v, ChangelogVersion) for v in versions)


class TestChangelogParserEdgeCases:
    """TASK-002: Parser edge case tests (AC-006)."""

    def test_ac006_empty_content_returns_empty_list(self):
        """AC-006: Empty content returns empty list."""
        versions = parse_changelog(content=EMPTY_CHANGELOG)
        assert versions == []

    def test_ac006_malformed_content_returns_empty_list(self):
        """AC-006: Malformed content returns empty list."""
        versions = parse_changelog(content=MALFORMED_CHANGELOG)
        assert versions == []

    def test_ac007_no_unreleased_section(self):
        """AC-007: No Unreleased section — not included."""
        versions = parse_changelog(content=CHANGELOG_NO_UNRELEASED)
        assert all(v.version != "Unreleased" for v in versions)
        assert len(versions) == 2

    def test_ac007_empty_unreleased_not_shown(self):
        """AC-007: Unreleased with no content is not included."""
        versions = parse_changelog(content=CHANGELOG_EMPTY_UNRELEASED)
        assert all(v.version != "Unreleased" for v in versions)

    def test_parse_from_file_path(self, tmp_path: Path):
        """Parser can read from a file path."""
        changelog_file = tmp_path / "CHANGELOG.md"
        changelog_file.write_text(VALID_CHANGELOG)
        versions = parse_changelog(path=changelog_file)
        assert len(versions) == 5  # Unreleased + 4 released

    def test_parse_missing_file_returns_empty_list(self, tmp_path: Path):
        """AC-006: Missing file returns empty list."""
        versions = parse_changelog(path=tmp_path / "nonexistent.md")
        assert versions == []


# ── Settings Page Tests (AC-001, AC-006) ─────────────────────────────────


class TestSettingsChangelog:
    """TASK-003: Settings page changelog tab visibility."""

    @pytest.mark.anyio
    async def test_ac001_changelog_tab_visible_when_file_exists(self, client):
        """AC-001: Changelog tab appears when CHANGELOG.md exists and is parseable."""
        with patch(
            "app.routes.pages.parse_changelog",
            return_value=[
                ChangelogVersion(
                    version="1.0.0",
                    date="2026-01-26",
                    sections={"Added": ["Initial release"]},
                )
            ],
        ):
            response = await client.get("/settings")
            assert response.status_code == 200
            assert "Changelog" in response.text

    @pytest.mark.anyio
    async def test_ac006_changelog_tab_hidden_when_no_file(self, client):
        """AC-006: Changelog tab hidden when CHANGELOG.md is missing."""
        with patch("app.routes.pages.parse_changelog", return_value=[]):
            response = await client.get("/settings")
            assert response.status_code == 200
            # The tab should not be rendered
            assert (
                "Changelog" not in response.text or "changelog-tab" not in response.text
            )


# ── HTMX Endpoint Tests (AC-003, AC-004) ────────────────────────────────


class TestChangelogEndpoints:
    """TASK-004: HTMX endpoint tests."""

    @pytest.mark.anyio
    async def test_ac003_get_changelog_list(self, client):
        """AC-003: GET /htmx/changelog returns version accordion list."""
        with patch(
            "app.routes.pages.parse_changelog",
            return_value=[
                ChangelogVersion(
                    version="1.7.0",
                    date="2026-02-24",
                    sections={"Added": ["New feature"]},
                ),
                ChangelogVersion(
                    version="1.6.0",
                    date="2026-02-23",
                    sections={"Fixed": ["Bug fix"]},
                ),
            ],
        ):
            response = await client.get("/htmx/changelog")
            assert response.status_code == 200
            assert "1.7.0" in response.text
            assert "1.6.0" in response.text

    @pytest.mark.anyio
    async def test_ac004_get_version_detail(self, client):
        """AC-004: GET /htmx/changelog/{version} returns grouped sections."""
        with patch(
            "app.routes.pages.parse_changelog",
            return_value=[
                ChangelogVersion(
                    version="1.7.0",
                    date="2026-02-24",
                    sections={
                        "Added": ["Setup guide", "Architecture diagram"],
                        "Fixed": ["E2E test isolation"],
                    },
                ),
            ],
        ):
            response = await client.get("/htmx/changelog/1.7.0")
            assert response.status_code == 200
            assert "Added" in response.text
            assert "Fixed" in response.text
            assert "Setup guide" in response.text

    @pytest.mark.anyio
    async def test_ac004_version_not_found_returns_404(self, client):
        """AC-004: Unknown version returns 404."""
        with patch("app.routes.pages.parse_changelog", return_value=[]):
            response = await client.get("/htmx/changelog/99.99.99")
            assert response.status_code == 404


# ── Current Badge Test (AC-005) ──────────────────────────────────────────


class TestCurrentBadge:
    """TASK-005: Current version badge."""

    @pytest.mark.anyio
    async def test_ac005_current_version_badge(self, client):
        """AC-005: Version matching app version displays 'Current' badge."""
        with (
            patch(
                "app.routes.pages.parse_changelog",
                return_value=[
                    ChangelogVersion(
                        version="1.7.0",
                        date="2026-02-24",
                        sections={"Added": ["New feature"]},
                    ),
                    ChangelogVersion(
                        version="1.6.0",
                        date="2026-02-23",
                        sections={"Fixed": ["Bug fix"]},
                    ),
                ],
            ),
            patch("app.routes.pages.get_settings") as mock_settings,
        ):
            settings_obj = mock_settings.return_value
            settings_obj.app_version = "1.7.0"
            response = await client.get("/htmx/changelog")
            assert response.status_code == 200
            assert "Current" in response.text
