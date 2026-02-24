"""Changelog schema for parsed CHANGELOG.md entries."""

from pydantic import BaseModel


class ChangelogVersion(BaseModel):
    """A single version entry parsed from CHANGELOG.md."""

    version: str  # e.g. "1.7.0" or "Unreleased"
    date: str | None = None  # e.g. "2026-02-24", None for Unreleased
    sections: dict[str, list[str]]  # e.g. {"Added": ["feature 1", "feature 2"]}
