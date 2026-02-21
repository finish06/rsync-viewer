"""Tests for Date Range Quick Select feature.

Spec: specs/date-range-quick-select.md
"""

from datetime import datetime, timedelta

import pytest

pytestmark = pytest.mark.asyncio


class TestQuickSelectButtons:
    """AC-001: Dashboard displays pill-style toggle buttons."""

    async def test_ac001_index_has_quick_select_buttons(self, client):
        """AC-001: Quick select buttons appear on dashboard."""
        response = await client.get("/")
        assert response.status_code == 200
        html = response.text
        assert "quick-select" in html
        assert "Last 7 Days" in html
        assert "Last 30 Days" in html
        assert "Max" in html
        assert "Custom" in html

    async def test_ac008_active_button_default_highlighted(self, client):
        """AC-008: The default quick-select button has active class."""
        response = await client.get("/")
        html = response.text
        # The "Last 7 Days" button should be marked as default active
        assert 'quick-select-btn active" data-range="7d"' in html


class TestDateRangeFiltering:
    """AC-002, AC-003: Date range filtering via quick select."""

    async def test_ac002_seven_day_filter(self, client, create_sync_log):
        """AC-002: Last 7 Days shows only recent logs."""
        now = datetime.utcnow()
        # Create a log from 3 days ago (should appear)
        create_sync_log(
            source_name="recent-log",
            start_time=now - timedelta(days=3),
            end_time=now - timedelta(days=3) + timedelta(minutes=5),
            file_count=2,
        )
        # Create a log from 14 days ago (should NOT appear)
        create_sync_log(
            source_name="old-log",
            start_time=now - timedelta(days=14),
            end_time=now - timedelta(days=14) + timedelta(minutes=5),
            file_count=2,
        )

        start_date = (now - timedelta(days=7)).isoformat()
        end_date = now.isoformat()
        response = await client.get(
            f"/htmx/sync-table?start_date={start_date}&end_date={end_date}"
        )
        assert response.status_code == 200
        assert "recent-log" in response.text
        assert "old-log" not in response.text

    async def test_ac003_thirty_day_filter(self, client, create_sync_log):
        """AC-003: Last 30 Days shows logs within 30 days."""
        now = datetime.utcnow()
        create_sync_log(
            source_name="within-30d",
            start_time=now - timedelta(days=15),
            end_time=now - timedelta(days=15) + timedelta(minutes=5),
            file_count=2,
        )
        create_sync_log(
            source_name="older-than-30d",
            start_time=now - timedelta(days=45),
            end_time=now - timedelta(days=45) + timedelta(minutes=5),
            file_count=2,
        )

        start_date = (now - timedelta(days=30)).isoformat()
        end_date = now.isoformat()
        response = await client.get(
            f"/htmx/sync-table?start_date={start_date}&end_date={end_date}"
        )
        assert response.status_code == 200
        assert "within-30d" in response.text
        assert "older-than-30d" not in response.text


class TestMaxRecordsLoadAll:
    """AC-004, AC-005: Max records with Load All functionality."""

    async def test_ac004_load_all_param_returns_all_records(self, client, create_sync_log):
        """AC-004/AC-005: load_all=true bypasses pagination limit."""
        now = datetime.utcnow()
        # Create 25 logs
        for i in range(25):
            create_sync_log(
                source_name=f"source-{i}",
                start_time=now - timedelta(hours=i),
                end_time=now - timedelta(hours=i) + timedelta(minutes=5),
                file_count=1,
            )

        # With default limit (20), should get 20
        response = await client.get("/htmx/sync-table?limit=20")
        assert response.status_code == 200
        # Pagination info should show total 25
        assert "of 25" in response.text

        # With load_all=true, should get all 25
        response = await client.get("/htmx/sync-table?load_all=true")
        assert response.status_code == 200
        assert "source-0" in response.text
        assert "source-24" in response.text

    async def test_ac004_load_all_button_shown_when_more_records(
        self, client, create_sync_log
    ):
        """AC-004: Load All button appears when total > displayed count."""
        now = datetime.utcnow()
        for i in range(25):
            create_sync_log(
                source_name=f"src-{i}",
                start_time=now - timedelta(hours=i),
                end_time=now - timedelta(hours=i) + timedelta(minutes=5),
                file_count=1,
            )

        response = await client.get("/htmx/sync-table?limit=20")
        assert response.status_code == 200
        assert "load-all-btn" in response.text

    async def test_ac004_load_all_button_hidden_when_all_shown(
        self, client, create_sync_log
    ):
        """AC-004: No Load All button when all records fit in one page."""
        now = datetime.utcnow()
        for i in range(5):
            create_sync_log(
                source_name=f"src-{i}",
                start_time=now - timedelta(hours=i),
                end_time=now - timedelta(hours=i) + timedelta(minutes=5),
                file_count=1,
            )

        response = await client.get("/htmx/sync-table?limit=20")
        assert response.status_code == 200
        assert "load-all-btn" not in response.text


class TestCombinedFilters:
    """AC-010: Quick select works with other filters."""

    async def test_ac010_date_range_with_source_filter(self, client, create_sync_log):
        """AC-010: Date range + source filter work together."""
        now = datetime.utcnow()
        create_sync_log(
            source_name="target-src",
            start_time=now - timedelta(days=5),
            end_time=now - timedelta(days=5) + timedelta(minutes=5),
            file_count=3,
        )
        create_sync_log(
            source_name="other-src",
            start_time=now - timedelta(days=5),
            end_time=now - timedelta(days=5) + timedelta(minutes=5),
            file_count=3,
        )

        start_date = (now - timedelta(days=7)).isoformat()
        end_date = now.isoformat()
        response = await client.get(
            f"/htmx/sync-table?start_date={start_date}&end_date={end_date}"
            f"&source_name=target-src"
        )
        assert response.status_code == 200
        assert "target-src" in response.text
        assert "other-src" not in response.text
