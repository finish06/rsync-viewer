"""Tests for scripts/backup.py and scripts/restore.py (specs/backup-restore.md)."""

from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.backup import (
    BackupError,
    archive_name,
    prune_backups,
    run_backup,
)
from scripts.restore import build_restore_command


class TestAC001Backup:
    def test_ac001_archive_name_is_timestamped(self):
        name = archive_name()
        assert name.startswith("rsync-viewer-")
        assert name.endswith(".dump")

    def test_ac001_run_backup_invokes_pg_dump_and_returns_path(self, tmp_path):
        with patch("scripts.backup.subprocess.run") as run:
            run.return_value.returncode = 0
            path = run_backup(
                "postgresql+psycopg://u:secret@db:5432/rsync_viewer",
                tmp_path,
                keep=14,
            )
        args = run.call_args.args[0]
        assert args[0] == "pg_dump"
        assert "--format=custom" in args
        # psycopg driver suffix stripped for libpq
        assert "postgresql://u:secret@db:5432/rsync_viewer" in args
        assert Path(path).parent == tmp_path

    def test_ac001_failure_leaves_no_partial_file(self, tmp_path):
        def boom(cmd, **kwargs):
            file_arg = [a for a in cmd if str(tmp_path) in a][0]
            Path(file_arg.removeprefix("--file=")).write_text("partial")

            class R:
                returncode = 1
                stderr = b"connection refused"

            return R()

        with patch("scripts.backup.subprocess.run", side_effect=boom):
            with pytest.raises(BackupError, match="pg_dump failed"):
                run_backup("postgresql://u:p@nowhere/db", tmp_path, keep=14)
        assert list(tmp_path.glob("*.dump")) == []

    def test_ac005_error_never_contains_password(self, tmp_path):
        with patch("scripts.backup.subprocess.run") as run:
            run.return_value.returncode = 1
            run.return_value.stderr = b"boom"
            with pytest.raises(BackupError) as excinfo:
                run_backup(
                    "postgresql://user:hunter2@db/rsync_viewer", tmp_path, keep=14
                )
        assert "hunter2" not in str(excinfo.value)


class TestAC002Rotation:
    def _seed(self, tmp_path, names):
        for i, name in enumerate(names):
            f = tmp_path / name
            f.write_text("x")
        return tmp_path

    def test_ac002_prunes_oldest_beyond_keep(self, tmp_path):
        self._seed(
            tmp_path,
            [
                "rsync-viewer-20260801-000000.dump",
                "rsync-viewer-20260815-000000.dump",
                "rsync-viewer-20260830-000000.dump",
            ],
        )
        removed = prune_backups(tmp_path, keep=2)
        assert [p.name for p in removed] == ["rsync-viewer-20260801-000000.dump"]
        assert len(list(tmp_path.glob("*.dump"))) == 2

    def test_ac002_never_touches_foreign_files(self, tmp_path):
        self._seed(
            tmp_path,
            ["rsync-viewer-20260801-000000.dump", "precious-manual-copy.dump"],
        )
        (tmp_path / "notes.txt").write_text("keep me")
        prune_backups(tmp_path, keep=1)
        assert (tmp_path / "precious-manual-copy.dump").exists()
        assert (tmp_path / "notes.txt").exists()

    def test_ac002_keep_zero_refused(self, tmp_path):
        with pytest.raises(BackupError, match="keep"):
            prune_backups(tmp_path, keep=0)


class TestAC003Restore:
    def test_ac003_command_shape(self):
        cmd = build_restore_command(
            "postgresql+psycopg://u:p@db:5432/rsync_viewer",
            Path("backups/rsync-viewer-20260830-000000.dump"),
        )
        assert cmd[0] == "pg_restore"
        assert "--clean" in cmd
        assert "--if-exists" in cmd
        assert "postgresql://u:p@db:5432/rsync_viewer" in " ".join(cmd)

    def test_ac003_main_refuses_without_yes(self, tmp_path, capsys):
        from scripts.restore import main

        archive = tmp_path / "rsync-viewer-20260830-000000.dump"
        archive.write_text("x")
        with patch("scripts.restore.subprocess.run") as run:
            code = main([str(archive), "--database-url", "postgresql://u:p@db/x"])
        assert code != 0
        assert run.call_count == 0
        assert "--yes" in capsys.readouterr().err
