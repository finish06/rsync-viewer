"""Tests for Average Transfer Rate feature.

Spec: specs/average-transfer-rate.md
"""

from datetime import datetime, timedelta
from types import SimpleNamespace


from app.main import format_rate
from app.utils import utc_now


class TestFormatRateFilter:
    """AC-002, AC-003, AC-005, AC-006, AC-007, AC-008, AC-009: format_rate filter."""

    def _make_sync(
        self,
        bytes_received=1024,
        start_time=None,
        end_time=None,
        is_dry_run=False,
    ):
        now = utc_now()
        return SimpleNamespace(
            bytes_received=bytes_received,
            start_time=start_time or (now - timedelta(seconds=10)),
            end_time=end_time or now,
            is_dry_run=is_dry_run,
        )

    def test_ac002_calculates_rate_from_bytes_and_duration(self):
        """AC-002: Rate = bytes_received / duration."""
        sync = self._make_sync(
            bytes_received=1000,
            start_time=datetime(2026, 1, 1, 0, 0, 0),
            end_time=datetime(2026, 1, 1, 0, 0, 10),
        )
        result = format_rate(sync)
        # 1000 bytes / 10 seconds = 100 B/s
        assert result == "100.00 B/s"

    def test_ac003_auto_scales_to_kbs(self):
        """AC-003: Auto-scales to KB/s."""
        sync = self._make_sync(
            bytes_received=10240,
            start_time=datetime(2026, 1, 1, 0, 0, 0),
            end_time=datetime(2026, 1, 1, 0, 0, 1),
        )
        result = format_rate(sync)
        assert result == "10.00 KB/s"

    def test_ac003_auto_scales_to_mbs(self):
        """AC-003: Auto-scales to MB/s."""
        # 10 MB in 1 second = 10 MB/s
        sync = self._make_sync(
            bytes_received=10 * 1024 * 1024,
            start_time=datetime(2026, 1, 1, 0, 0, 0),
            end_time=datetime(2026, 1, 1, 0, 0, 1),
        )
        result = format_rate(sync)
        assert result == "10.00 MB/s"

    def test_ac003_auto_scales_to_gbs(self):
        """AC-003: Auto-scales to GB/s."""
        # 2 GB in 1 second
        sync = self._make_sync(
            bytes_received=2 * 1024 * 1024 * 1024,
            start_time=datetime(2026, 1, 1, 0, 0, 0),
            end_time=datetime(2026, 1, 1, 0, 0, 1),
        )
        result = format_rate(sync)
        assert result == "2.00 GB/s"

    def test_ac005_none_bytes_returns_dash(self):
        """AC-005: Returns '-' when bytes_received is None."""
        sync = self._make_sync(bytes_received=None)
        assert format_rate(sync) == "-"

    def test_ac006_zero_duration_returns_dash(self):
        """AC-006: Returns '-' when duration is zero."""
        now = utc_now()
        sync = self._make_sync(start_time=now, end_time=now)
        assert format_rate(sync) == "-"

    def test_ac006_missing_start_time_returns_dash(self):
        """AC-006: Returns '-' when start_time is None."""
        sync = self._make_sync()
        sync.start_time = None
        assert format_rate(sync) == "-"

    def test_ac006_missing_end_time_returns_dash(self):
        """AC-006: Returns '-' when end_time is None."""
        sync = self._make_sync()
        sync.end_time = None
        assert format_rate(sync) == "-"

    def test_ac007_dry_run_returns_dash(self):
        """AC-007: Returns '-' for dry run entries."""
        sync = self._make_sync(is_dry_run=True)
        assert format_rate(sync) == "-"

    def test_ac008_zero_bytes_returns_zero_rate(self):
        """AC-008: Returns '0.00 B/s' when bytes is 0 but duration valid."""
        sync = self._make_sync(bytes_received=0)
        assert format_rate(sync) == "0.00 B/s"


class TestSyncTableAvgRateColumn:
    """AC-001: Sync table displays Avg Rate column."""

    async def test_ac001_table_has_avg_rate_header(self, client, create_sync_log):
        """AC-001: Table includes Avg Rate column header."""
        create_sync_log(source_name="rate-test", bytes_received=1024, file_count=1)
        response = await client.get("/htmx/sync-table")
        assert response.status_code == 200
        assert "Avg Rate" in response.text

    async def test_ac001_table_shows_calculated_rate(self, client, create_sync_log):
        """AC-001: Table shows calculated rate value."""
        now = utc_now()
        create_sync_log(
            source_name="rate-calc",
            bytes_received=10240,
            start_time=now - timedelta(seconds=10),
            end_time=now,
            file_count=1,
        )
        response = await client.get("/htmx/sync-table")
        assert response.status_code == 200
        assert "1.00 KB/s" in response.text


class TestDetailModalAvgRate:
    """AC-004: Detail modal displays average transfer rate."""

    async def test_ac004_detail_modal_has_avg_rate(self, client, create_sync_log):
        """AC-004: Detail modal includes Avg Rate field."""
        now = utc_now()
        log = create_sync_log(
            source_name="modal-rate",
            bytes_received=5120,
            start_time=now - timedelta(seconds=5),
            end_time=now,
            file_count=2,
        )
        response = await client.get(f"/htmx/sync-detail/{log.id}")
        assert response.status_code == 200
        assert "Avg Rate" in response.text
        assert "1.00 KB/s" in response.text
