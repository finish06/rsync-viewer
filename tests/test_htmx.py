"""Tests for HTMX handler endpoints and dashboard pages."""

from datetime import timedelta
from app.utils import utc_now


class TestIndexPage:
    """Test GET / dashboard page"""

    async def test_index_returns_200(self, client):
        """Test index page returns 200"""
        response = await client.get("/")
        assert response.status_code == 200

    async def test_index_contains_dashboard_content(self, client):
        """Test index page contains expected dashboard elements"""
        response = await client.get("/")
        assert response.status_code == 200
        html = response.text
        assert "Rsync Log Viewer" in html or "rsync" in html.lower()


class TestHealthEndpoint:
    """Test GET /health endpoint"""

    async def test_health_returns_ok(self, client):
        """Test health endpoint returns ok status"""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestHtmxSyncTable:
    """Test GET /htmx/sync-table endpoint"""

    async def test_sync_table_returns_200(self, client):
        """Test sync table partial returns 200"""
        response = await client.get("/htmx/sync-table")
        assert response.status_code == 200

    async def test_sync_table_with_data(self, client, create_sync_log):
        """Test sync table displays created logs"""
        create_sync_log(
            source_name="test-source",
            bytes_received=1024,
            file_count=3,
        )
        response = await client.get("/htmx/sync-table")
        assert response.status_code == 200
        assert "test-source" in response.text

    async def test_sync_table_filter_by_source(self, client, create_sync_log):
        """Test filtering sync table by source name"""
        create_sync_log(source_name="source-a", file_count=1)
        create_sync_log(source_name="source-b", file_count=1)

        response = await client.get("/htmx/sync-table?source_name=source-a")
        assert response.status_code == 200
        assert "source-a" in response.text

    async def test_sync_table_hide_dry_run(self, client, create_sync_log):
        """Test hiding dry runs from sync table"""
        create_sync_log(source_name="real-run", is_dry_run=False, file_count=1)
        create_sync_log(source_name="dry-run", is_dry_run=True, file_count=1)

        response = await client.get("/htmx/sync-table?show_dry_run=hide")
        assert response.status_code == 200

    async def test_sync_table_show_only_dry_run(self, client, create_sync_log):
        """Test showing only dry runs in sync table"""
        create_sync_log(source_name="real-run", is_dry_run=False, file_count=1)
        create_sync_log(source_name="dry-run", is_dry_run=True, file_count=1)

        response = await client.get("/htmx/sync-table?show_dry_run=only")
        assert response.status_code == 200

    async def test_sync_table_hide_empty(self, client, create_sync_log):
        """Test hiding empty runs (zero file count)"""
        create_sync_log(source_name="has-files", file_count=5)
        create_sync_log(source_name="empty-run", file_count=0)

        response = await client.get("/htmx/sync-table?hide_empty=hide")
        assert response.status_code == 200

    async def test_sync_table_show_only_empty(self, client, create_sync_log):
        """Test showing only empty runs"""
        create_sync_log(source_name="has-files", file_count=5)
        create_sync_log(source_name="empty-run", file_count=0)

        response = await client.get("/htmx/sync-table?hide_empty=only")
        assert response.status_code == 200

    async def test_sync_table_date_filter(self, client, create_sync_log):
        """Test filtering sync table by date range"""
        now = utc_now()
        create_sync_log(
            source_name="recent",
            start_time=now - timedelta(hours=1),
            end_time=now,
            file_count=1,
        )

        start = (now - timedelta(days=1)).isoformat()
        end = now.isoformat()
        response = await client.get(
            f"/htmx/sync-table?start_date={start}&end_date={end}"
        )
        assert response.status_code == 200

    async def test_sync_table_pagination(self, client, create_sync_log):
        """Test sync table pagination parameters"""
        for i in range(5):
            create_sync_log(source_name=f"source-{i}", file_count=1)

        response = await client.get("/htmx/sync-table?offset=2&limit=2")
        assert response.status_code == 200

    async def test_sync_table_show_all_dry_runs(self, client, create_sync_log):
        """Test showing all runs including dry runs"""
        create_sync_log(source_name="real", is_dry_run=False, file_count=1)
        create_sync_log(source_name="dry", is_dry_run=True, file_count=1)

        response = await client.get("/htmx/sync-table?show_dry_run=show")
        assert response.status_code == 200


class TestHtmxCharts:
    """Test GET /htmx/charts endpoint"""

    async def test_charts_returns_200(self, client):
        """Test charts partial returns 200 with no data"""
        response = await client.get("/htmx/charts")
        assert response.status_code == 200

    async def test_charts_with_data(self, client, create_sync_log):
        """Test charts partial renders with sync data"""
        now = utc_now()
        create_sync_log(
            source_name="test-source",
            start_time=now - timedelta(minutes=5),
            end_time=now,
            bytes_received=1024000,
            file_count=10,
        )
        response = await client.get("/htmx/charts")
        assert response.status_code == 200

    async def test_charts_filter_by_source(self, client, create_sync_log):
        """Test charts filter by source"""
        now = utc_now()
        create_sync_log(
            source_name="filtered-source",
            start_time=now - timedelta(minutes=5),
            end_time=now,
            file_count=3,
        )
        response = await client.get("/htmx/charts?source_name=filtered-source")
        assert response.status_code == 200

    async def test_charts_hide_dry_run(self, client, create_sync_log):
        """Test charts with dry run filter"""
        now = utc_now()
        create_sync_log(
            source_name="real",
            start_time=now - timedelta(minutes=5),
            end_time=now,
            is_dry_run=False,
            file_count=1,
        )
        response = await client.get("/htmx/charts?show_dry_run=hide")
        assert response.status_code == 200

    async def test_charts_show_only_dry_run(self, client, create_sync_log):
        """Test charts showing only dry runs"""
        now = utc_now()
        create_sync_log(
            source_name="dry",
            start_time=now - timedelta(minutes=5),
            end_time=now,
            is_dry_run=True,
            file_count=1,
        )
        response = await client.get("/htmx/charts?show_dry_run=only")
        assert response.status_code == 200

    async def test_charts_hide_empty(self, client, create_sync_log):
        """Test charts hiding empty runs"""
        now = utc_now()
        create_sync_log(
            source_name="has-files",
            start_time=now - timedelta(minutes=5),
            end_time=now,
            file_count=5,
        )
        response = await client.get("/htmx/charts?hide_empty=hide")
        assert response.status_code == 200

    async def test_charts_show_only_empty(self, client, create_sync_log):
        """Test charts showing only empty runs"""
        now = utc_now()
        create_sync_log(
            source_name="empty",
            start_time=now - timedelta(minutes=5),
            end_time=now,
            file_count=0,
        )
        response = await client.get("/htmx/charts?hide_empty=only")
        assert response.status_code == 200

    async def test_charts_with_missing_end_time(self, client, create_sync_log):
        """Test charts handle syncs without duration gracefully"""
        now = utc_now()
        create_sync_log(
            source_name="no-duration",
            start_time=now - timedelta(minutes=5),
            end_time=now,
            bytes_received=0,
            file_count=1,
        )
        response = await client.get("/htmx/charts")
        assert response.status_code == 200


class TestHtmxSyncDetail:
    """Test GET /htmx/sync-detail/{sync_id} endpoint"""

    async def test_sync_detail_returns_200(self, client, create_sync_log):
        """Test sync detail partial returns 200"""
        log = create_sync_log(
            source_name="detail-test",
            total_size_bytes=5000,
            file_count=2,
            file_list=["file1.txt", "file2.txt"],
        )
        response = await client.get(f"/htmx/sync-detail/{log.id}")
        assert response.status_code == 200
        assert "detail-test" in response.text

    async def test_sync_detail_not_found(self, client):
        """Test sync detail returns not found partial for invalid ID"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/htmx/sync-detail/{fake_id}")
        assert response.status_code == 200  # Returns a partial, not 404


class TestTemplateFilters:
    """Test custom template filters"""

    def test_format_bytes_none(self):
        """Test format_bytes with None returns dash"""
        from app.main import format_bytes

        assert format_bytes(None) == "-"

    def test_format_bytes_small(self):
        """Test format_bytes with small values"""
        from app.main import format_bytes

        assert "B" in format_bytes(100)

    def test_format_bytes_kilobytes(self):
        """Test format_bytes with kilobyte range"""
        from app.main import format_bytes

        result = format_bytes(2048)
        assert "KB" in result

    def test_format_bytes_megabytes(self):
        """Test format_bytes with megabyte range"""
        from app.main import format_bytes

        result = format_bytes(2 * 1024 * 1024)
        assert "MB" in result

    def test_format_bytes_gigabytes(self):
        """Test format_bytes with gigabyte range"""
        from app.main import format_bytes

        result = format_bytes(5 * 1024 * 1024 * 1024)
        assert "GB" in result

    def test_format_duration_seconds_only(self):
        """Test format_duration with seconds only"""
        from app.main import format_duration

        delta = timedelta(seconds=45)
        assert format_duration(delta) == "45s"

    def test_format_duration_minutes_seconds(self):
        """Test format_duration with minutes and seconds"""
        from app.main import format_duration

        delta = timedelta(minutes=3, seconds=30)
        assert format_duration(delta) == "3m 30s"

    def test_format_duration_hours_minutes_seconds(self):
        """Test format_duration with hours, minutes, and seconds"""
        from app.main import format_duration

        delta = timedelta(hours=2, minutes=15, seconds=10)
        assert format_duration(delta) == "2h 15m 10s"
