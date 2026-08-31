"""Database backup with rotation (specs/backup-restore.md AC-001/002/005).

Usage:
    python -m scripts.backup [--dir backups] [--keep 14] [--database-url URL]

Produces ``backups/rsync-viewer-YYYYMMDD-HHMMSS.dump`` (pg_dump custom
format) and prunes the oldest archives beyond ``--keep``. Credentials are
never printed; failures leave no partial file behind.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ARCHIVE_RE = re.compile(r"^rsync-viewer-\d{8}-\d{6}\.dump$")


class BackupError(Exception):
    """Backup failed; message is safe to print (no credentials)."""


def libpq_url(database_url: str) -> str:
    """``postgresql+psycopg://`` → ``postgresql://`` for the pg client tools."""
    return re.sub(r"^postgresql\+[a-z0-9]+://", "postgresql://", database_url)


def archive_name(now: datetime | None = None) -> str:
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%d-%H%M%S")
    return f"rsync-viewer-{stamp}.dump"


def prune_backups(directory: Path, keep: int) -> list[Path]:
    """Delete the oldest archives beyond ``keep``; only our own files (AC-002)."""
    if keep < 1:
        raise BackupError("--keep must be at least 1 (0 would delete the new backup)")
    archives = sorted(
        (p for p in directory.glob("*.dump") if ARCHIVE_RE.match(p.name)),
        key=lambda p: p.name,
    )
    doomed = archives[: max(0, len(archives) - keep)]
    for path in doomed:
        path.unlink()
    return doomed


def run_backup(database_url: str, directory: Path, *, keep: int) -> Path:
    """Dump the database, then rotate. Returns the archive path (AC-001)."""
    if keep < 1:
        raise BackupError("--keep must be at least 1 (0 would delete the new backup)")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / archive_name()
    command = [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        f"--file={target}",
        libpq_url(database_url),
    ]
    try:
        result = subprocess.run(command, capture_output=True)
    except FileNotFoundError as error:
        raise BackupError(
            "pg_dump not found — install postgresql client tools or run inside "
            "the app container (see docs/backup-restore.md)"
        ) from error
    if result.returncode != 0:
        target.unlink(missing_ok=True)  # never leave a partial archive
        stderr = (result.stderr or b"").decode(errors="replace")[:500]
        raise BackupError(f"pg_dump failed (exit {result.returncode}): {stderr}")
    prune_backups(directory, keep)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default="backups", help="backup directory")
    parser.add_argument("--keep", type=int, default=14, help="archives to keep")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", ""),
        help="defaults to $DATABASE_URL",
    )
    args = parser.parse_args(argv)
    if not args.database_url:
        print("DATABASE_URL is not set and --database-url missing", file=sys.stderr)
        return 2
    try:
        path = run_backup(args.database_url, Path(args.dir), keep=args.keep)
    except BackupError as error:
        print(f"backup failed: {error}", file=sys.stderr)
        return 1
    print(f"backup written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
