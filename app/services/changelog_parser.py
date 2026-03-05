"""Parse CHANGELOG.md into structured version data.

Handles the Keep a Changelog format:
  ## [version] - date
  ### Section
  - Item
    - Sub-item
"""

import re
from functools import lru_cache
from pathlib import Path

from app.schemas.changelog import ChangelogItem, ChangelogVersion

# Matches: ## [1.7.0] - 2026-02-24  or  ## [Unreleased]
VERSION_HEADER = re.compile(
    r"^##\s+\[(?P<version>[^\]]+)\](?:\s*-\s*(?P<date>\S+))?\s*$"
)

# Matches: ### Added, ### Fixed, etc.
SECTION_HEADER = re.compile(r"^###\s+(?P<section>.+)$")

# Matches: - Item text (top-level list item, no leading whitespace)
LIST_ITEM = re.compile(r"^-\s+(?P<text>.+)$")

# Matches:   - Sub-item text (indented 2+ spaces)
SUB_LIST_ITEM = re.compile(r"^\s{2,}-\s+(?P<text>.+)$")


def _parse_content(content: str) -> list[ChangelogVersion]:
    """Parse changelog content string into structured version data."""
    if not content.strip():
        return []

    versions: list[ChangelogVersion] = []
    current_version: str | None = None
    current_date: str | None = None
    current_sections: dict[str, list[ChangelogItem]] = {}
    current_section: str | None = None

    for line in content.splitlines():
        version_match = VERSION_HEADER.match(line)
        if version_match:
            # Save previous version if it has content
            if current_version is not None and current_sections:
                versions.append(
                    ChangelogVersion(
                        version=current_version,
                        date=current_date,
                        sections=current_sections,
                    )
                )
            current_version = version_match.group("version")
            current_date = version_match.group("date")
            current_sections = {}
            current_section = None
            continue

        section_match = SECTION_HEADER.match(line)
        if section_match and current_version is not None:
            current_section = section_match.group("section").strip()
            continue

        # Check for indented sub-item first (before top-level item)
        sub_item_match = SUB_LIST_ITEM.match(line)
        if (
            sub_item_match
            and current_version is not None
            and current_section is not None
        ):
            items = current_sections.get(current_section, [])
            if items:
                items[-1].children.append(sub_item_match.group("text").strip())
            continue

        item_match = LIST_ITEM.match(line)
        if item_match and current_version is not None and current_section is not None:
            current_sections.setdefault(current_section, []).append(
                ChangelogItem(text=item_match.group("text").strip())
            )
            continue

    # Don't forget the last version
    if current_version is not None and current_sections:
        versions.append(
            ChangelogVersion(
                version=current_version,
                date=current_date,
                sections=current_sections,
            )
        )

    return versions


@lru_cache(maxsize=1)
def _parse_changelog_from_file(path_str: str) -> list[ChangelogVersion]:
    """Cached file-based parsing — reads disk once per process lifetime."""
    try:
        content = Path(path_str).read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return []
    return _parse_content(content)


def parse_changelog(
    path: Path | None = None,
    content: str | None = None,
) -> list[ChangelogVersion]:
    """Parse a CHANGELOG.md file or string into structured version data.

    Args:
        path: Path to CHANGELOG.md file. Ignored if content is provided.
        content: Raw changelog text. Takes priority over path.

    Returns:
        List of ChangelogVersion models, most recent first.
        Returns empty list if file is missing, empty, or unparseable.
    """
    if content is not None:
        return _parse_content(content)
    if path is None:
        return []
    return _parse_changelog_from_file(str(path))
