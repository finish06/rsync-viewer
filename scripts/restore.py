"""Database restore (specs/backup-restore.md AC-003).

Usage:
    python -m scripts.restore backups/rsync-viewer-YYYYMMDD-HHMMSS.dump --yes

Runs ``pg_restore --clean --if-exists`` into ``DATABASE_URL``. Refuses to run
without ``--yes`` — restoring OVERWRITES the current database.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from scripts.backup import libpq_url


def build_restore_command(database_url: str, archive: Path) -> list[str]:
    return [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        f"--dbname={libpq_url(database_url)}",
        str(archive),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", help="pg_dump custom-format archive")
    parser.add_argument(
        "--yes", action="store_true", help="confirm overwriting the database"
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", ""),
        help="defaults to $DATABASE_URL",
    )
    args = parser.parse_args(argv)
    archive = Path(args.archive)
    if not archive.is_file():
        print(f"archive not found: {archive}", file=sys.stderr)
        return 2
    if not args.database_url:
        print("DATABASE_URL is not set and --database-url missing", file=sys.stderr)
        return 2
    command = build_restore_command(args.database_url, archive)
    print(f"will run: pg_restore --clean --if-exists … {archive.name}")
    if not args.yes:
        print(
            "refusing to overwrite the database without --yes "
            "(this REPLACES all current data)",
            file=sys.stderr,
        )
        return 3
    result = subprocess.run(command)
    if result.returncode != 0:
        print(f"pg_restore exited {result.returncode}", file=sys.stderr)
        return 1
    print("restore complete — restart the app so caches and state reset")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
