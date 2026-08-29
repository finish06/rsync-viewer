"""Tests for app/services/media_classifier.py — specs/insight-ui.md AC-016, AC-021.

Pure-function, table-driven. Paths mirror real Plex/Sonarr/Radarr layouts and
the samples in test_payload.json / scripts/seed.py.
"""

import pytest

from app.services.media_classifier import classify_file_list, classify_path

MOVIE_CASES = [
    (
        "The Polar Express (2004)/The Polar Express.2004.Bluray-1080p.EAC3.x265.mkv",
        ("The Polar Express", 2004),
    ),
    (
        "The Noel Diary (2022)/The Noel Diary.2022.WEBDL-1080p.EAC3 Atmos.x264.mkv",
        ("The Noel Diary", 2022),
    ),
    ("Movies/Dune (2021)/Dune.2021.2160p.REMUX.mkv", ("Dune", 2021)),
    ("Movies/Dune (1984)/Dune (1984).mkv", ("Dune", 1984)),
    ("Movies/Some.Movie.2019.1080p.WEB-DL.x264.mkv", ("Some Movie", 2019)),
    ("Movies/Ünïcode Fïlm (2020)/film.mkv", ("Ünïcode Fïlm", 2020)),
    ("Videos/Movies/movie_112.mkv", ("movie 112", None)),
    ("films/Heat (1995)/Heat.1995.mp4", ("Heat", 1995)),
]

EPISODE_CASES = [
    (
        "Severance (2022)/Season 02/Severance - S02E03 - Who Is Alive.mkv",
        ("Severance", 2022, 2, 3),
    ),
    (
        "TV Shows/Slow Horses/Season 04/Slow Horses 4x05.mkv",
        ("Slow Horses", None, 4, 5),
    ),
    ("Shows/Dark/Season 1/Dark.S01E01.1080p.WEB.mkv", ("Dark", None, 1, 1)),
    ("tv\\Andor\\Season 02\\Andor S02E01.mkv", ("Andor", None, 2, 1)),
    (
        "tv/Only Murders in the Building (2021)/Season 03/Only Murders - S03E10.mp4",
        ("Only Murders in the Building", 2021, 3, 10),
    ),
    ("Severance/Severance - S02E03.mkv", ("Severance", None, 2, 3)),
    ("Severance.S02E03.mkv", ("Severance", None, 2, 3)),
    ("series/The Bear/Season 3/The Bear - Episode 4.m4v", ("The Bear", None, 3, 4)),
]

IGNORED_CASES = [
    "The Polar Express (2004)/The Polar Express.2004.Bluray-1080p.EAC3.x265.en.srt",
    "Photos/2026/IMG_1004.jpg",
    "backup/db/dump.sql",
    "Documents/Report 2020.pdf",
    "The Perfect Christmas Present (2017)/",
    "random/clip.mkv",
    "Movies/Dune (2021)/poster.jpg",
    "",
    "sent 2.87K bytes  received 291.07K bytes  117.58K bytes/sec",
]


@pytest.mark.parametrize("path,expected", MOVIE_CASES)
def test_ac016_movies(path, expected):
    match = classify_path(path)
    assert match is not None, path
    assert match.kind == "movie"
    assert (match.title, match.year) == expected
    assert match.season is None and match.episode is None
    assert match.path == path


@pytest.mark.parametrize("path,expected", EPISODE_CASES)
def test_ac016_episodes(path, expected):
    match = classify_path(path)
    assert match is not None, path
    assert match.kind == "episode"
    assert (match.title, match.year, match.season, match.episode) == expected


@pytest.mark.parametrize("path", IGNORED_CASES)
def test_ac021_ignored(path):
    assert classify_path(path) is None


def test_ac016_dedupe_key_distinguishes_year_and_episode():
    dune_2021 = classify_path("Movies/Dune (2021)/Dune.2021.mkv")
    dune_1984 = classify_path("Movies/Dune (1984)/Dune.1984.mkv")
    ep3 = classify_path("Severance/Season 02/Severance - S02E03.mkv")
    ep4 = classify_path("Severance/Season 02/Severance - S02E04.mkv")
    assert dune_2021.dedupe_key != dune_1984.dedupe_key
    assert ep3.dedupe_key != ep4.dedupe_key
    assert ep3.dedupe_key == classify_path("Severance.S02E03.mkv").dedupe_key


def test_ac016_file_list_dedupes_and_preserves_order():
    paths = [
        "Movies/Heat (1995)/Heat.1995.mkv",
        "Movies/Heat (1995)/Heat.1995.en.srt",
        "Shows/Dark/Season 1/Dark.S01E01.mkv",
        "Shows/Dark/Season 1/Dark.S01E01.mkv",
        "Shows/Dark/Season 1/Dark.S01E02.mkv",
        "Photos/x.jpg",
    ]
    matches = classify_file_list(paths)
    assert [(m.kind, m.title, m.season, m.episode) for m in matches] == [
        ("movie", "Heat", None, None),
        ("episode", "Dark", 1, 1),
        ("episode", "Dark", 1, 2),
    ]


def test_ac021_never_raises_on_garbage():
    assert classify_file_list([None, 123, "   ", "/", "\\\\"]) == []  # type: ignore[list-item]


# ---------------------------------------------------------------------------
# AC-028: rsync control lines are never media
# ---------------------------------------------------------------------------

from app.services.media_classifier import parse_rsync_line, split_file_list  # noqa: E402

MOVIE_PATH = "Movies/Bloodlands (2021)/Bloodlands.2021.1080p.mkv"

CONTROL_LINES = [
    f"deleting {MOVIE_PATH}",
    f"*deleting   {MOVIE_PATH}",
    "deleting Movies/Bloodlands (2021)/",
    "*deleting   TV/Severance (2022)/Season 02/",
    "created directory /mnt/media/Movies/Bloodlands (2021)",
    "sending incremental file list",
    "receiving incremental file list",
    "Number of files: 1,234 (reg: 1,200, dir: 34)",
    "Number of created files: 3 (reg: 2, dir: 1)",
    "Number of deleted files: 1",
    "Number of regular files transferred: 2",
    "Total file size: 18.70G bytes",
    "Total transferred file size: 1.20G bytes",
    "Literal data: 1.20G bytes",
    "Matched data: 0 bytes",
    "File list size: 65.53K",
    "File list generation time: 0.001 seconds",
    "File list transfer time: 0.000 seconds",
    "cannot delete non-empty directory: Movies/Bloodlands (2021)",
    'skipping non-regular file "Movies/Bloodlands (2021)/link.mkv"',
    f".f..t...... {MOVIE_PATH}",  # attribute-only change, not a transfer
    f"hf          {MOVIE_PATH}",  # hard link
    "cd+++++++++ Movies/Bloodlands (2021)/",
]


@pytest.mark.parametrize("line", CONTROL_LINES)
def test_ac028_control_lines_are_not_media(line):
    assert classify_path(line) is None
    assert classify_file_list([line]) == []


@pytest.mark.parametrize(
    "line",
    [
        f">f+++++++++ {MOVIE_PATH}",
        f"<f.st...... {MOVIE_PATH}",
        f"cf+++++++++ {MOVIE_PATH}",
    ],
)
def test_ac028_itemized_transfers_classified_by_path(line):
    match = classify_path(line)
    assert match is not None
    assert (match.kind, match.title, match.year) == ("movie", "Bloodlands", 2021)
    assert match.path == MOVIE_PATH


@pytest.mark.parametrize(
    "line,expected",
    [
        (MOVIE_PATH, ("transfer", MOVIE_PATH)),
        (f"deleting {MOVIE_PATH}", ("deletion", MOVIE_PATH)),
        (f"*deleting   {MOVIE_PATH}", ("deletion", MOVIE_PATH)),
        (
            "deleting Movies/Bloodlands (2021)/",
            ("deletion", "Movies/Bloodlands (2021)/"),
        ),
        (f">f+++++++++ {MOVIE_PATH}", ("transfer", MOVIE_PATH)),
        (f".f..t...... {MOVIE_PATH}", None),
        ("created directory /mnt/x", None),
        ("sending incremental file list", None),
        ("Total file size: 18.70G bytes", None),
        ("", None),
        (42, None),
    ],
)
def test_ac028_parse_rsync_line(line, expected):
    assert parse_rsync_line(line) == expected


def test_ac028_split_file_list_separates_deletions():
    transfers, deletions = split_file_list(
        [
            f"deleting {MOVIE_PATH}",
            "TV/Severance (2022)/Season 02/Severance - S02E03.mkv",
            "sending incremental file list",
            "deleting Movies/Old (1999)/",
            None,
        ]
    )
    assert transfers == ["TV/Severance (2022)/Season 02/Severance - S02E03.mkv"]
    assert deletions == [MOVIE_PATH, "Movies/Old (1999)/"]
