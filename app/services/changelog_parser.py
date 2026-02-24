"""Parse CHANGELOG.md into structured version data.

Handles the Keep a Changelog format:
  ## [version] - date
  ### Section
  - Item
"""

import re
from pathlib import Path

from app.schemas.changelog import ChangelogVersion

# Matches: ## [1.7.0] - 2026-02-24  or  ## [Unreleased]
VERSION_HEADER = re.compile(
    r"^##\s+\[(?P<version>[^\]]+)\](?:\s*-\s*(?P<date>\S+))?\s*$"
)

# Matches: ### Added, ### Fixed, etc.
SECTION_HEADER = re.compile(r"^###\s+(?P<section>.+)$")

# Matches: - Item text
LIST_ITEM = re.compile(r"^-\s+(?P<text>.+)$")


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
    if content is None:
        if path is None:
            return []
        try:
            content = Path(path).read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            return []

    if not content.strip():
        return []

    versions: list[ChangelogVersion] = []
    current_version: str | None = None
    current_date: str | None = None
    current_sections: dict[str, list[str]] = {}
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

        item_match = LIST_ITEM.match(line)
        if item_match and current_version is not None and current_section is not None:
            current_sections.setdefault(current_section, []).append(
                item_match.group("text").strip()
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
