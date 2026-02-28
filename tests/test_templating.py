"""Tests for app.templating — format_bytes, format_duration, format_rate, _form_str.

Pure-function tests with no database dependency.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.templating import _form_str, format_bytes, format_duration, format_rate


# ---------- format_bytes ----------


class TestFormatBytes:
    def test_none_returns_dash(self):
        assert format_bytes(None) == "-"

    def test_zero_bytes(self):
        assert format_bytes(0) == "0.00 B"

    def test_bytes_range(self):
        assert format_bytes(512) == "512.00 B"

    def test_kilobytes(self):
        result = format_bytes(1536)  # 1.5 KB
        assert "KB" in result

    def test_megabytes(self):
        result = format_bytes(5 * 1024 * 1024)
        assert "MB" in result

    def test_gigabytes(self):
        result = format_bytes(2 * 1024**3)
        assert "GB" in result

    def test_terabytes(self):
        result = format_bytes(3 * 1024**4)
        assert "TB" in result

    def test_petabytes(self):
        result = format_bytes(1024**5)
        assert "PB" in result

    def test_exact_1024_shows_next_unit(self):
        # 1024 bytes = 1.00 KB
        result = format_bytes(1024)
        assert "KB" in result

    def test_negative_bytes(self):
        # abs() is used internally
        result = format_bytes(-2048)
        assert "KB" in result


# ---------- format_duration ----------


class TestFormatDuration:
    def test_seconds_only(self):
        assert format_duration(timedelta(seconds=45)) == "45s"

    def test_minutes_and_seconds(self):
        assert format_duration(timedelta(minutes=3, seconds=12)) == "3m 12s"

    def test_hours_minutes_seconds(self):
        assert (
            format_duration(timedelta(hours=2, minutes=15, seconds=30)) == "2h 15m 30s"
        )

    def test_zero_duration(self):
        assert format_duration(timedelta(0)) == "0s"

    def test_hours_no_minutes(self):
        assert format_duration(timedelta(hours=1, seconds=5)) == "1h 5s"

    def test_exact_hour(self):
        assert format_duration(timedelta(hours=1)) == "1h 0s"

    def test_large_duration(self):
        result = format_duration(timedelta(days=1, hours=3, minutes=20, seconds=5))
        assert "27h" in result  # 24 + 3


# ---------- format_rate ----------


@dataclass
class FakeSync:
    """Minimal stand-in for SyncLog to test format_rate."""

    is_dry_run: bool = False
    bytes_received: int | None = 1024 * 1024  # 1 MB
    start_time: datetime | None = None
    end_time: datetime | None = None

    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime(2025, 1, 1, 12, 0, 0)
        if self.end_time is None:
            self.end_time = self.start_time + timedelta(seconds=10)


class TestFormatRate:
    def test_dry_run_returns_dash(self):
        sync = FakeSync(is_dry_run=True)
        assert format_rate(sync) == "-"

    def test_none_bytes_received_returns_dash(self):
        sync = FakeSync(bytes_received=None)
        assert format_rate(sync) == "-"

    def test_no_start_time_returns_dash(self):
        sync = FakeSync(start_time=None, end_time=datetime.now())
        # Reset to force None through __post_init__
        sync.start_time = None
        assert format_rate(sync) == "-"

    def test_no_end_time_returns_dash(self):
        sync = FakeSync()
        sync.end_time = None
        assert format_rate(sync) == "-"

    def test_zero_duration_returns_dash(self):
        now = datetime(2025, 1, 1, 12, 0, 0)
        sync = FakeSync(start_time=now, end_time=now)
        assert format_rate(sync) == "-"

    def test_negative_duration_returns_dash(self):
        now = datetime(2025, 1, 1, 12, 0, 0)
        sync = FakeSync(start_time=now, end_time=now - timedelta(seconds=5))
        assert format_rate(sync) == "-"

    def test_bytes_per_second(self):
        # 500 bytes over 10 seconds = 50 B/s
        sync = FakeSync(bytes_received=500)
        result = format_rate(sync)
        assert "B/s" in result

    def test_kilobytes_per_second(self):
        # 10 KB over 1 second
        now = datetime(2025, 1, 1, 12, 0, 0)
        sync = FakeSync(
            bytes_received=10 * 1024,
            start_time=now,
            end_time=now + timedelta(seconds=1),
        )
        result = format_rate(sync)
        assert "KB/s" in result

    def test_megabytes_per_second(self):
        # 10 MB over 1 second
        now = datetime(2025, 1, 1, 12, 0, 0)
        sync = FakeSync(
            bytes_received=10 * 1024 * 1024,
            start_time=now,
            end_time=now + timedelta(seconds=1),
        )
        result = format_rate(sync)
        assert "MB/s" in result


# ---------- _form_str ----------


class TestFormStr:
    def test_dict_like_form_data(self):
        form = {"name": "Alice"}
        result = _form_str(form, "name")
        assert result == "Alice"

    def test_missing_key_returns_default(self):
        form = {"name": "Alice"}
        result = _form_str(form, "missing", "fallback")
        assert result == "fallback"

    def test_none_value_returns_default(self):
        form = {"name": None}
        result = _form_str(form, "name", "default_val")
        assert result == "default_val"

    def test_default_empty_string(self):
        form = {}
        result = _form_str(form, "key")
        assert result == ""

    def test_non_string_value_converted(self):
        form = {"count": 42}
        result = _form_str(form, "count")
        assert result == "42"

    def test_object_without_get_returns_default(self):
        """Objects without a .get() method return the default."""

        class NoGet:
            pass

        result = _form_str(NoGet(), "key", "fallback")
        assert result == "fallback"
