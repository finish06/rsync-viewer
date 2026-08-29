"""Classify rsync file paths into movies and TV episodes (specs/insight-ui.md §4).

Heuristics, not a database lookup: Plex/Sonarr/Radarr-style layouts are
recognised; anything ambiguous is ignored rather than guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".m4v", ".avi", ".mov", ".ts", ".wmv", ".webm"}

# Top-level folders that only say "this is where movies/shows live"
MOVIE_CONTAINERS = {"movies", "movie", "films", "film", "cinema"}
SHOW_CONTAINERS = {"tv", "tv shows", "tvshows", "shows", "series", "television"}

# Release tags that never belong to a title; stripped from cleaned names
RELEASE_TAGS = {
    "1080p",
    "2160p",
    "720p",
    "480p",
    "4k",
    "uhd",
    "hdr",
    "hdr10",
    "dv",
    "webdl",
    "web-dl",
    "web",
    "webrip",
    "bluray",
    "blu-ray",
    "bdrip",
    "brrip",
    "dvdrip",
    "hdtv",
    "remux",
    "proper",
    "repack",
    "x264",
    "x265",
    "h264",
    "h265",
    "hevc",
    "avc",
    "aac",
    "ac3",
    "eac3",
    "dts",
    "atmos",
    "truehd",
    "10bit",
    "multi",
    "internal",
    "limited",
}

_SXXEYY = re.compile(r"(?i)\bS(\d{1,2})[ ._-]?E(\d{1,3})\b")
_NXNN = re.compile(r"(?i)\b(\d{1,2})x(\d{2,3})\b")
_SEASON_DIR = re.compile(r"(?i)^season[ ._-]?(\d{1,2})$")
_EPISODE_ONLY = re.compile(r"(?i)\b(?:e|ep|episode)[ ._-]?(\d{1,3})\b")
_TITLE_YEAR = re.compile(
    r"^(?P<title>.+?)[ .(\[]+(?P<year>(?:19|20)\d{2})[)\]]?(?:[ .\-]|$)"
)
_TRAILING_YEAR = re.compile(r"\s*[(\[]((?:19|20)\d{2})[)\]]\s*$")

# rsync lines that are not transfers (specs/insight-ui.md AC-028).
# ``deleting …`` (plain) and ``*deleting …`` (--itemize-changes) name a path
# that was removed on the receiver; everything else here is bookkeeping.
_DELETION = re.compile(r"^\*?deleting\s+(.+)$")
# --itemize-changes: YX + 7–9 attribute flags, whitespace, path. Y is the
# update type (< > c . h *), X the file type (f d L D S).
_ITEMIZE = re.compile(r"^([<>ch.])([fdLDS])[.+?cstpoguaxbn ]{7,10}\s+(.+)$")
_CONTROL = re.compile(
    r"^(?:created directory\b|sending incremental|receiving incremental|"
    r"building file list|receiving file list|number of |total |literal data|"
    r"matched data|file list |sent \d|cannot delete|skipping |rsync\b|"
    r"warning:|error:)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MediaMatch:
    """One recognised movie or episode, with the path that produced it."""

    kind: str  # "movie" | "episode"
    title: str
    year: Optional[int]
    season: Optional[int]
    episode: Optional[int]
    path: str

    @property
    def dedupe_key(self) -> str:
        """Stable identity: same title/year/season/episode ⇒ same item."""
        return "|".join(
            [
                self.kind,
                self.title.casefold(),
                str(self.year),
                str(self.season),
                str(self.episode),
            ]
        )


def _clean_title(raw: str) -> str:
    text = raw.replace(".", " ").replace("_", " ")
    words: list[str] = []
    for word in text.split():
        if word.casefold().strip("-") in RELEASE_TAGS:
            break
        words.append(word)
    return " ".join(words).strip(" -")


def _split_title_year(segment: str) -> tuple[str, Optional[int]]:
    """'Severance (2022)' → ('Severance', 2022); 'Dark' → ('Dark', None)."""
    match = _TRAILING_YEAR.search(segment)
    if match:
        return _clean_title(segment[: match.start()]), int(match.group(1))
    return _clean_title(segment), None


def _episode_match(stem: str, dirs: list[str]) -> Optional[tuple[int, int, int]]:
    """Return (season, episode, marker_start) if the stem names an episode."""
    for pattern in (_SXXEYY, _NXNN):
        found = pattern.search(stem)
        if found:
            return int(found.group(1)), int(found.group(2)), found.start()
    for directory in reversed(dirs):
        season_dir = _SEASON_DIR.match(directory)
        if season_dir:
            episode_only = _EPISODE_ONLY.search(stem)
            if episode_only:
                return (
                    int(season_dir.group(1)),
                    int(episode_only.group(1)),
                    episode_only.start(),
                )
    return None


def _show_title(
    dirs: list[str], stem: str, marker_start: int
) -> tuple[str, Optional[int]]:
    for directory in dirs:
        if directory.casefold() in SHOW_CONTAINERS or _SEASON_DIR.match(directory):
            continue
        return _split_title_year(directory)
    return _split_title_year(stem[:marker_start])


def _movie_match(dirs: list[str], stem: str) -> Optional[tuple[str, Optional[int]]]:
    parent = dirs[-1] if dirs else ""
    if parent and parent.casefold() not in MOVIE_CONTAINERS:
        title, year = _split_title_year(parent)
        if year is not None and title:
            return title, year
    found = _TITLE_YEAR.match(stem)
    if found:
        title = _clean_title(found.group("title"))
        if title:
            return title, int(found.group("year"))
    if any(d.casefold() in MOVIE_CONTAINERS for d in dirs):
        title = _clean_title(stem)
        if title:
            return title, None
    return None


def parse_rsync_line(line: object) -> Optional[tuple[str, str]]:
    """Split a ``file_list`` line into ``("transfer" | "deletion", path)``.

    Returns None for rsync control output (summary lines, ``created
    directory``, attribute-only or hard-link itemize entries, …) so callers
    never mistake it for a path. A directory deletion keeps its trailing ``/``.
    """
    if not isinstance(line, str):
        return None
    text = line.strip()
    if not text:
        return None
    deletion = _DELETION.match(text)
    if deletion:
        return "deletion", deletion.group(1).strip()
    itemized = _ITEMIZE.match(text)
    if itemized:
        update_type, file_type, path = itemized.groups()
        if update_type in "<>c" and file_type == "f":
            return "transfer", path.strip()
        return None
    if _CONTROL.match(text):
        return None
    return "transfer", text


def split_file_list(paths: object) -> tuple[list[str], list[str]]:
    """Separate a sync log's ``file_list`` into transferred and deleted paths."""
    transfers: list[str] = []
    deletions: list[str] = []
    if not isinstance(paths, (list, tuple)):
        return transfers, deletions
    for line in paths:
        parsed = parse_rsync_line(line)
        if parsed is None:
            continue
        kind, path = parsed
        (transfers if kind == "transfer" else deletions).append(path)
    return transfers, deletions


def classify_path(path: object) -> Optional[MediaMatch]:
    """Classify one rsync line; None for deletions, control output, non-video."""
    parsed = parse_rsync_line(path)
    if parsed is None or parsed[0] != "transfer":
        return None
    return classify_transfer_path(parsed[1])


def classify_transfer_path(path: str) -> Optional[MediaMatch]:
    """Classify a plain file path (already known to be a transfer)."""
    normalised = path.strip().replace("\\", "/")
    if not normalised or normalised.endswith("/"):
        return None
    segments = [s for s in normalised.split("/") if s]
    if not segments:
        return None
    filename = segments[-1]
    dirs = segments[:-1]
    dot = filename.rfind(".")
    if dot <= 0 or filename[dot:].casefold() not in VIDEO_EXTENSIONS:
        return None
    stem = filename[:dot]

    episode = _episode_match(stem, dirs)
    if episode:
        season_no, episode_no, marker_start = episode
        title, year = _show_title(dirs, stem, marker_start)
        if not title:
            return None
        return MediaMatch("episode", title, year, season_no, episode_no, path)

    movie = _movie_match(dirs, stem)
    if movie:
        title, year = movie
        return MediaMatch("movie", title, year, None, None, path)
    return None


def classify_file_list(paths: object) -> list[MediaMatch]:
    """Classify every path, dropping duplicates while preserving first order."""
    if not isinstance(paths, (list, tuple)):
        return []
    seen: set[str] = set()
    matches: list[MediaMatch] = []
    for path in paths:
        match = classify_path(path)
        if match is None or match.dedupe_key in seen:
            continue
        seen.add(match.dedupe_key)
        matches.append(match)
    return matches
