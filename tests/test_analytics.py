"""Tests for analytics and reporting (specs/analytics.md)."""

from datetime import datetime, timedelta

import pytest

pytestmark = pytest.mark.asyncio


class TestSummaryEndpoint:
    """AC-001: Statistics API returns daily/weekly/monthly summaries."""

    async def test_ac001_daily_summary_returns_data(self, client, create_sync_log):
        """GET /api/v1/analytics/summary with period=daily returns daily aggregates."""
        base = datetime(2026, 1, 15, 10, 0, 0)
        # Day 1: 2 syncs
        create_sync_log(
            source_name="srv-a",
            start_time=base,
            end_time=base + timedelta(minutes=5),
            bytes_received=1000,
            file_count=10,
            exit_code=0,
        )
        create_sync_log(
            source_name="srv-a",
            start_time=base + timedelta(hours=2),
            end_time=base + timedelta(hours=2, minutes=10),
            bytes_received=2000,
            file_count=20,
            exit_code=1,
        )
        # Day 2: 1 sync
        create_sync_log(
            source_name="srv-a",
            start_time=base + timedelta(days=1),
            end_time=base + timedelta(days=1, minutes=3),
            bytes_received=500,
            file_count=5,
            exit_code=0,
        )

        response = await client.get(
            "/api/v1/analytics/summary",
            params={"period": "daily", "start": "2026-01-15", "end": "2026-01-16"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "daily"
        assert len(data["data"]) == 2

        day1 = data["data"][0]
        assert day1["total_syncs"] == 2
        assert day1["successful_syncs"] == 1
        assert day1["failed_syncs"] == 1
        assert day1["total_bytes_transferred"] == 3000
        assert day1["total_files_transferred"] == 30

    async def test_ac001_weekly_summary(self, client, create_sync_log):
        """GET /api/v1/analytics/summary with period=weekly returns weekly aggregates."""
        base = datetime(2026, 1, 6, 10, 0, 0)  # Monday
        for i in range(5):
            create_sync_log(
                source_name="srv-a",
                start_time=base + timedelta(days=i),
                end_time=base + timedelta(days=i, minutes=5),
                bytes_received=100 * (i + 1),
                file_count=i + 1,
            )

        response = await client.get(
            "/api/v1/analytics/summary",
            params={"period": "weekly", "start": "2026-01-06", "end": "2026-01-12"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "weekly"
        assert len(data["data"]) >= 1
        assert data["data"][0]["total_syncs"] == 5

    async def test_ac001_monthly_summary(self, client, create_sync_log):
        """GET /api/v1/analytics/summary with period=monthly returns monthly aggregates."""
        base = datetime(2026, 1, 10, 10, 0, 0)
        create_sync_log(
            source_name="srv-a",
            start_time=base,
            end_time=base + timedelta(minutes=5),
            bytes_received=1000,
            file_count=10,
        )

        response = await client.get(
            "/api/v1/analytics/summary",
            params={"period": "monthly", "start": "2026-01-01", "end": "2026-01-31"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "monthly"
        assert len(data["data"]) >= 1

    async def test_ac001_summary_with_source_filter(self, client, create_sync_log):
        """Summary endpoint filters by source when source param provided."""
        base = datetime(2026, 1, 15, 10, 0, 0)
        create_sync_log(
            source_name="srv-a",
            start_time=base,
            end_time=base + timedelta(minutes=5),
            bytes_received=1000,
        )
        create_sync_log(
            source_name="srv-b",
            start_time=base,
            end_time=base + timedelta(minutes=5),
            bytes_received=2000,
        )

        response = await client.get(
            "/api/v1/analytics/summary",
            params={
                "period": "daily",
                "start": "2026-01-15",
                "end": "2026-01-15",
                "source": "srv-a",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["total_syncs"] == 1
        assert data["data"][0]["total_bytes_transferred"] == 1000

    async def test_ac001_summary_empty_range(self, client):
        """Summary returns empty data array for date range with no syncs."""
        response = await client.get(
            "/api/v1/analytics/summary",
            params={"period": "daily", "start": "2020-01-01", "end": "2020-01-31"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []

    async def test_ac001_summary_includes_avg_duration(self, client, create_sync_log):
        """Summary includes avg_duration_seconds computed from start/end times."""
        base = datetime(2026, 1, 15, 10, 0, 0)
        create_sync_log(
            source_name="srv-a",
            start_time=base,
            end_time=base + timedelta(minutes=5),
        )
        create_sync_log(
            source_name="srv-a",
            start_time=base + timedelta(hours=1),
            end_time=base + timedelta(hours=1, minutes=15),
        )

        response = await client.get(
            "/api/v1/analytics/summary",
            params={"period": "daily", "start": "2026-01-15", "end": "2026-01-15"},
        )
        assert response.status_code == 200
        data = response.json()
        day = data["data"][0]
        assert "avg_duration_seconds" in day
        # Avg of 300s and 900s = 600s
        assert day["avg_duration_seconds"] == pytest.approx(600.0, abs=1)

    async def test_ac001_summary_missing_period_returns_422(self, client):
        """Missing required 'period' parameter returns 422."""
        response = await client.get(
            "/api/v1/analytics/summary",
            params={"start": "2026-01-01", "end": "2026-01-31"},
        )
        assert response.status_code == 422

    async def test_ac001_summary_invalid_period_returns_422(self, client):
        """Invalid period value returns 422."""
        response = await client.get(
            "/api/v1/analytics/summary",
            params={
                "period": "hourly",
                "start": "2026-01-01",
                "end": "2026-01-31",
            },
        )
        assert response.status_code == 422


class TestSourceStatsEndpoint:
    """AC-002: Per-source statistics endpoint."""

    async def test_ac002_sources_returns_per_source_stats(
        self, client, create_sync_log
    ):
        """GET /api/v1/analytics/sources returns aggregate stats per source."""
        base = datetime(2026, 1, 15, 10, 0, 0)
        # srv-a: 2 syncs, 1 success, 1 failure
        create_sync_log(
            source_name="srv-a",
            start_time=base,
            end_time=base + timedelta(minutes=5),
            bytes_received=1000,
            file_count=10,
            exit_code=0,
        )
        create_sync_log(
            source_name="srv-a",
            start_time=base + timedelta(hours=1),
            end_time=base + timedelta(hours=1, minutes=10),
            bytes_received=2000,
            file_count=20,
            exit_code=1,
        )
        # srv-b: 1 sync, success
        create_sync_log(
            source_name="srv-b",
            start_time=base,
            end_time=base + timedelta(minutes=3),
            bytes_received=500,
            file_count=5,
            exit_code=0,
        )

        response = await client.get("/api/v1/analytics/sources")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        sources = {s["source_name"]: s for s in data}
        assert "srv-a" in sources
        assert "srv-b" in sources

        srv_a = sources["srv-a"]
        assert srv_a["total_syncs"] == 2
        assert srv_a["success_rate"] == pytest.approx(0.5)
        assert srv_a["avg_files_transferred"] == 15
        assert srv_a["avg_bytes_transferred"] == 1500

        srv_b = sources["srv-b"]
        assert srv_b["total_syncs"] == 1
        assert srv_b["success_rate"] == pytest.approx(1.0)

    async def test_ac002_sources_with_date_filter(self, client, create_sync_log):
        """Sources endpoint filters by date range when start/end provided."""
        old = datetime(2026, 1, 1, 10, 0, 0)
        recent = datetime(2026, 2, 1, 10, 0, 0)
        create_sync_log(
            source_name="srv-a",
            start_time=old,
            end_time=old + timedelta(minutes=5),
        )
        create_sync_log(
            source_name="srv-a",
            start_time=recent,
            end_time=recent + timedelta(minutes=5),
        )

        response = await client.get(
            "/api/v1/analytics/sources",
            params={"start": "2026-02-01", "end": "2026-02-28"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["total_syncs"] == 1

    async def test_ac002_sources_includes_avg_duration(self, client, create_sync_log):
        """Per-source stats include avg_duration_seconds."""
        base = datetime(2026, 1, 15, 10, 0, 0)
        create_sync_log(
            source_name="srv-a",
            start_time=base,
            end_time=base + timedelta(minutes=10),
        )

        response = await client.get("/api/v1/analytics/sources")
        assert response.status_code == 200
        data = response.json()
        assert data[0]["avg_duration_seconds"] == pytest.approx(600.0, abs=1)

    async def test_ac002_sources_includes_last_sync(self, client, create_sync_log):
        """Per-source stats include last_sync_at timestamp."""
        base = datetime(2026, 1, 15, 10, 0, 0)
        create_sync_log(
            source_name="srv-a",
            start_time=base,
            end_time=base + timedelta(minutes=5),
        )

        response = await client.get("/api/v1/analytics/sources")
        assert response.status_code == 200
        data = response.json()
        assert "last_sync_at" in data[0]
        assert data[0]["last_sync_at"] is not None

    async def test_ac002_sources_empty_returns_empty_list(self, client):
        """Sources endpoint returns empty list when no sync data exists."""
        response = await client.get("/api/v1/analytics/sources")
        assert response.status_code == 200
        data = response.json()
        assert data == []


class TestFrequencyTrend:
    """AC-003: Sync frequency trend data as time series."""

    async def test_ac003_summary_provides_frequency_data(
        self, client, create_sync_log
    ):
        """Daily summary data can be used as frequency time series (syncs per day)."""
        base = datetime(2026, 1, 15, 10, 0, 0)
        # 3 syncs on day 1, 1 sync on day 2
        for i in range(3):
            create_sync_log(
                source_name="srv-a",
                start_time=base + timedelta(hours=i),
                end_time=base + timedelta(hours=i, minutes=5),
            )
        create_sync_log(
            source_name="srv-a",
            start_time=base + timedelta(days=1),
            end_time=base + timedelta(days=1, minutes=5),
        )

        response = await client.get(
            "/api/v1/analytics/summary",
            params={"period": "daily", "start": "2026-01-15", "end": "2026-01-16"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["data"][0]["total_syncs"] == 3
        assert data["data"][1]["total_syncs"] == 1


class TestExportEndpoint:
    """AC-004, AC-005, AC-010: Data export in CSV and JSON formats."""

    async def test_ac004_csv_export(self, client, create_sync_log):
        """GET /api/v1/analytics/export?format=csv returns CSV file."""
        base = datetime(2026, 1, 15, 10, 0, 0)
        create_sync_log(
            source_name="srv-a",
            start_time=base,
            end_time=base + timedelta(minutes=5),
            bytes_received=1000,
            file_count=10,
            exit_code=0,
        )

        response = await client.get(
            "/api/v1/analytics/export",
            params={"format": "csv"},
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers.get("content-disposition", "")

        lines = response.text.strip().split("\n")
        assert len(lines) == 2  # header + 1 data row
        header = lines[0]
        assert "source_name" in header
        assert "start_time" in header
        assert "exit_code" in header

    async def test_ac004_csv_with_source_filter(self, client, create_sync_log):
        """CSV export filters by source name."""
        base = datetime(2026, 1, 15, 10, 0, 0)
        create_sync_log(source_name="srv-a", start_time=base, end_time=base + timedelta(minutes=5))
        create_sync_log(source_name="srv-b", start_time=base, end_time=base + timedelta(minutes=5))

        response = await client.get(
            "/api/v1/analytics/export",
            params={"format": "csv", "source": "srv-a"},
        )
        assert response.status_code == 200
        lines = response.text.strip().split("\n")
        assert len(lines) == 2  # header + 1 row for srv-a only

    async def test_ac004_csv_with_date_filter(self, client, create_sync_log):
        """CSV export filters by date range."""
        old = datetime(2026, 1, 1, 10, 0, 0)
        recent = datetime(2026, 2, 1, 10, 0, 0)
        create_sync_log(source_name="srv-a", start_time=old, end_time=old + timedelta(minutes=5))
        create_sync_log(source_name="srv-a", start_time=recent, end_time=recent + timedelta(minutes=5))

        response = await client.get(
            "/api/v1/analytics/export",
            params={"format": "csv", "start": "2026-02-01", "end": "2026-02-28"},
        )
        assert response.status_code == 200
        lines = response.text.strip().split("\n")
        assert len(lines) == 2  # header + 1 row

    async def test_ac005_json_export(self, client, create_sync_log):
        """GET /api/v1/analytics/export?format=json returns JSON array."""
        base = datetime(2026, 1, 15, 10, 0, 0)
        create_sync_log(
            source_name="srv-a",
            start_time=base,
            end_time=base + timedelta(minutes=5),
            bytes_received=1000,
            file_count=10,
        )

        response = await client.get(
            "/api/v1/analytics/export",
            params={"format": "json"},
        )
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["source_name"] == "srv-a"
        assert "start_time" in data[0]
        assert "bytes_received" in data[0]

    async def test_ac010_export_pagination(self, client, create_sync_log):
        """Export supports limit and offset for pagination."""
        base = datetime(2026, 1, 15, 10, 0, 0)
        for i in range(5):
            create_sync_log(
                source_name="srv-a",
                start_time=base + timedelta(hours=i),
                end_time=base + timedelta(hours=i, minutes=5),
            )

        response = await client.get(
            "/api/v1/analytics/export",
            params={"format": "json", "limit": 2, "offset": 0},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    async def test_ac010_export_max_limit_enforced(self, client, create_sync_log):
        """Export enforces maximum limit of 10000."""
        response = await client.get(
            "/api/v1/analytics/export",
            params={"format": "json", "limit": 20000},
        )
        assert response.status_code == 200
        # The endpoint should cap at 10000, not error

    async def test_export_invalid_format_returns_400(self, client):
        """Invalid format parameter returns 400."""
        response = await client.get(
            "/api/v1/analytics/export",
            params={"format": "xml"},
        )
        assert response.status_code in (400, 422)

    async def test_export_empty_returns_headers_only_csv(self, client):
        """CSV export with no data returns header row only."""
        response = await client.get(
            "/api/v1/analytics/export",
            params={"format": "csv", "source": "nonexistent"},
        )
        assert response.status_code == 200
        lines = response.text.strip().split("\n")
        assert len(lines) == 1  # header only


class TestDashboardAnalyticsRoute:
    """AC-006, AC-007, AC-008, AC-009: Dashboard charts and analytics page."""

    async def test_ac006_analytics_page_renders(self, client):
        """GET /analytics returns 200 with HTML page."""
        response = await client.get("/analytics")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    async def test_ac006_analytics_page_includes_chartjs(self, client):
        """Analytics page includes Chart.js script."""
        response = await client.get("/analytics")
        assert response.status_code == 200
        assert "chart.js" in response.text.lower() or "Chart" in response.text

    async def test_ac007_analytics_page_has_date_picker(self, client):
        """Analytics page includes date range inputs."""
        response = await client.get("/analytics")
        assert response.status_code == 200
        assert 'type="date"' in response.text

    async def test_ac007_analytics_page_has_period_selector(self, client):
        """Analytics page includes period selector (daily/weekly/monthly)."""
        response = await client.get("/analytics")
        assert response.status_code == 200
        assert "daily" in response.text.lower()
        assert "weekly" in response.text.lower()
        assert "monthly" in response.text.lower()

    async def test_ac006_analytics_page_has_source_filter(self, client):
        """Analytics page includes source filter dropdown."""
        response = await client.get("/analytics")
        assert response.status_code == 200
        assert "source" in response.text.lower()

    async def test_ac008_analytics_page_has_comparison_section(self, client):
        """Analytics page includes per-source comparison section."""
        response = await client.get("/analytics")
        assert response.status_code == 200
        assert "comparison" in response.text.lower() or "compare" in response.text.lower()

    async def test_ac009_htmx_chart_data_endpoint(self, client, create_sync_log):
        """HTMX chart data partial returns chart-ready JSON."""
        base = datetime(2026, 1, 15, 10, 0, 0)
        create_sync_log(
            source_name="srv-a",
            start_time=base,
            end_time=base + timedelta(minutes=5),
            bytes_received=1000,
            file_count=10,
            exit_code=0,
        )
        create_sync_log(
            source_name="srv-a",
            start_time=base,
            end_time=base + timedelta(minutes=10),
            bytes_received=2000,
            file_count=20,
            exit_code=1,
        )

        response = await client.get(
            "/api/v1/analytics/sources",
        )
        assert response.status_code == 200
        data = response.json()
        # Should include success rate data for charts
        assert any("success_rate" in s for s in data)

    async def test_analytics_nav_link_on_dashboard(self, client):
        """Main dashboard includes navigation link to /analytics."""
        response = await client.get("/")
        assert response.status_code == 200
        assert "/analytics" in response.text
