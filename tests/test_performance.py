"""Tests for performance optimization (specs/performance.md)."""

from datetime import timedelta
from app.utils import utc_now
from pathlib import Path

from sqlalchemy import inspect

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestDatabaseIndexing:
    """AC-002: Database indexes on frequently queried columns."""

    def test_ac002_sync_logs_source_name_index(self, test_engine):
        """sync_logs has index on source_name."""
        inspector = inspect(test_engine)
        indexes = inspector.get_indexes("sync_logs")
        indexed_columns = {col for idx in indexes for col in idx["column_names"]}
        assert "source_name" in indexed_columns

    def test_ac002_sync_logs_created_at_index(self, test_engine):
        """sync_logs has index on created_at for ordering."""
        inspector = inspect(test_engine)
        indexes = inspector.get_indexes("sync_logs")
        indexed_columns = {col for idx in indexes for col in idx["column_names"]}
        assert "created_at" in indexed_columns

    def test_ac002_sync_logs_exit_code_index(self, test_engine):
        """sync_logs has index on exit_code for status filtering."""
        inspector = inspect(test_engine)
        indexes = inspector.get_indexes("sync_logs")
        indexed_columns = {col for idx in indexes for col in idx["column_names"]}
        assert "exit_code" in indexed_columns

    def test_ac002_sync_logs_composite_source_created_index(self, test_engine):
        """sync_logs has composite index on (source_name, created_at)."""
        inspector = inspect(test_engine)
        indexes = inspector.get_indexes("sync_logs")
        composite_found = any(
            set(idx["column_names"]) == {"source_name", "created_at"} for idx in indexes
        )
        assert composite_found, (
            f"No composite index on (source_name, created_at) found. Indexes: {indexes}"
        )

    def test_ac002_failure_events_composite_source_detected_index(self, test_engine):
        """failure_events has composite index on (source_name, detected_at)."""
        inspector = inspect(test_engine)
        indexes = inspector.get_indexes("failure_events")
        composite_found = any(
            set(idx["column_names"]) == {"source_name", "detected_at"}
            for idx in indexes
        )
        assert composite_found, (
            "No composite index on (source_name, detected_at) found. "
            f"Indexes: {indexes}"
        )

    def test_ac002_notification_logs_created_at_index(self, test_engine):
        """notification_logs has index on created_at for ordering."""
        inspector = inspect(test_engine)
        indexes = inspector.get_indexes("notification_logs")
        indexed_columns = {col for idx in indexes for col in idx["column_names"]}
        assert "created_at" in indexed_columns


class TestConnectionPoolConfig:
    """AC-005: Connection pool configurable via environment variables."""

    def test_ac005_pool_size_setting_exists(self):
        """Settings has db_pool_size field."""
        from app.config import Settings

        fields = Settings.model_fields
        assert "db_pool_size" in fields

    def test_ac005_pool_max_overflow_setting_exists(self):
        """Settings has db_max_overflow field."""
        from app.config import Settings

        fields = Settings.model_fields
        assert "db_max_overflow" in fields

    def test_ac005_pool_timeout_setting_exists(self):
        """Settings has db_pool_timeout field."""
        from app.config import Settings

        fields = Settings.model_fields
        assert "db_pool_timeout" in fields

    def test_ac005_pool_size_default(self):
        """db_pool_size defaults to 10."""
        from app.config import Settings

        assert Settings.model_fields["db_pool_size"].default == 10

    def test_ac005_env_example_has_pool_vars(self):
        """`.env.example` documents pool configuration variables."""
        with open(PROJECT_ROOT / ".env.example") as f:
            content = f.read()
        assert "DB_POOL_SIZE" in content
        assert "DB_MAX_OVERFLOW" in content


class TestQueryOptimization:
    """AC-006, AC-009: No N+1 patterns, lazy file list loading."""

    async def test_ac009_list_endpoint_excludes_file_list(
        self, client, create_sync_log
    ):
        """List endpoint does not include file_list field (lazy loaded)."""
        create_sync_log(
            source_name="test-src",
            file_list=["file1.txt", "file2.txt"],
            file_count=2,
        )
        response = await client.get("/api/v1/sync-logs")
        assert response.status_code == 200
        data = response.json()
        if data["items"]:
            item = data["items"][0]
            assert "file_list" not in item, "file_list should not be in list response"

    async def test_ac009_list_endpoint_excludes_raw_content(
        self, client, create_sync_log
    ):
        """List endpoint does not include raw_content field."""
        create_sync_log(source_name="test-src")
        response = await client.get("/api/v1/sync-logs")
        assert response.status_code == 200
        data = response.json()
        if data["items"]:
            item = data["items"][0]
            assert "raw_content" not in item, (
                "raw_content should not be in list response"
            )

    async def test_ac009_detail_endpoint_includes_file_list(
        self, client, create_sync_log
    ):
        """Detail endpoint includes file_list field."""
        log = create_sync_log(
            source_name="test-src",
            file_list=["file1.txt", "file2.txt"],
            file_count=2,
        )
        response = await client.get(f"/api/v1/sync-logs/{log.id}")
        assert response.status_code == 200
        data = response.json()
        assert "file_list" in data
        assert data["file_list"] == ["file1.txt", "file2.txt"]


class TestQueryTimeout:
    """AC-010: Query timeout configuration."""

    def test_ac010_query_timeout_setting_exists(self):
        """Settings has query_timeout_seconds field."""
        from app.config import Settings

        fields = Settings.model_fields
        assert "query_timeout_seconds" in fields

    def test_ac010_query_timeout_default(self):
        """query_timeout_seconds defaults to 30."""
        from app.config import Settings

        assert Settings.model_fields["query_timeout_seconds"].default == 30

    def test_ac010_env_example_has_timeout_var(self):
        """`.env.example` documents QUERY_TIMEOUT_SECONDS."""
        with open(PROJECT_ROOT / ".env.example") as f:
            content = f.read()
        assert "QUERY_TIMEOUT_SECONDS" in content


class TestCursorPagination:
    """AC-003, AC-004: Cursor-based pagination."""

    async def test_ac003_cursor_pagination_returns_cursor(
        self, client, create_sync_log
    ):
        """Cursor pagination returns next_cursor in response."""
        # Create enough records to paginate
        for i in range(5):
            create_sync_log(
                source_name=f"src-{i}",
                start_time=utc_now() - timedelta(hours=i),
            )

        response = await client.get("/api/v1/sync-logs?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert "pagination" in data
        assert "next_cursor" in data["pagination"]
        assert "has_next" in data["pagination"]
        assert data["pagination"]["has_next"] is True

    async def test_ac003_cursor_pagination_next_page(self, client, create_sync_log):
        """Using next_cursor returns the next page of results."""
        logs = []
        for i in range(5):
            log = create_sync_log(
                source_name=f"src-{i}",
                start_time=utc_now() - timedelta(hours=i),
            )
            logs.append(log)

        # Get first page
        response1 = await client.get("/api/v1/sync-logs?limit=2")
        data1 = response1.json()
        cursor = data1["pagination"]["next_cursor"]
        assert cursor is not None

        # Get second page using cursor
        response2 = await client.get(f"/api/v1/sync-logs?limit=2&cursor={cursor}")
        data2 = response2.json()
        assert response2.status_code == 200
        assert len(data2["items"]) == 2

        # Verify no overlap between pages
        page1_ids = {item["id"] for item in data1["items"]}
        page2_ids = {item["id"] for item in data2["items"]}
        assert page1_ids.isdisjoint(page2_ids), "Pages should not overlap"

    async def test_ac004_cursor_backward_pagination(self, client, create_sync_log):
        """Cursor pagination supports backward navigation."""
        for i in range(5):
            create_sync_log(
                source_name=f"src-{i}",
                start_time=utc_now() - timedelta(hours=i),
            )

        # Get first page, then second
        response1 = await client.get("/api/v1/sync-logs?limit=2")
        data1 = response1.json()
        next_cursor = data1["pagination"]["next_cursor"]

        response2 = await client.get(f"/api/v1/sync-logs?limit=2&cursor={next_cursor}")
        data2 = response2.json()
        prev_cursor = data2["pagination"]["prev_cursor"]

        # Go backward
        response3 = await client.get(
            f"/api/v1/sync-logs?limit=2&cursor={prev_cursor}&direction=backward"
        )
        data3 = response3.json()
        assert response3.status_code == 200

        # Should get back the same items as page 1
        page1_ids = {item["id"] for item in data1["items"]}
        page3_ids = {item["id"] for item in data3["items"]}
        assert page1_ids == page3_ids, "Backward should return to page 1"

    async def test_ac003_cursor_with_source_filter(self, client, create_sync_log):
        """Cursor pagination works with source_name filter."""
        for i in range(4):
            create_sync_log(
                source_name="target-src",
                start_time=utc_now() - timedelta(hours=i),
            )
        create_sync_log(source_name="other-src")

        response = await client.get("/api/v1/sync-logs?limit=2&source_name=target-src")
        data = response.json()
        assert len(data["items"]) == 2
        assert all(item["source_name"] == "target-src" for item in data["items"])
        assert data["pagination"]["has_next"] is True

    async def test_cursor_invalid_returns_400(self, client):
        """Invalid cursor value returns 400 error."""
        response = await client.get("/api/v1/sync-logs?cursor=not-a-valid-cursor")
        assert response.status_code == 400

    async def test_cursor_empty_result_returns_null_cursors(self, client):
        """Empty result set returns null cursors."""
        response = await client.get("/api/v1/sync-logs?source_name=nonexistent-source")
        data = response.json()
        assert data["pagination"]["next_cursor"] is None
        assert data["pagination"]["has_next"] is False

    async def test_offset_fallback_still_works(self, client, create_sync_log):
        """Offset/limit pagination still works as deprecated fallback."""
        for i in range(5):
            create_sync_log(
                source_name=f"src-{i}",
                start_time=utc_now() - timedelta(hours=i),
            )

        response = await client.get("/api/v1/sync-logs?offset=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        # Offset mode should still include total count
        assert "total" in data

    async def test_cursor_pagination_last_page(self, client, create_sync_log):
        """Last page has has_next=False and next_cursor=None."""
        for i in range(3):
            create_sync_log(
                source_name=f"src-{i}",
                start_time=utc_now() - timedelta(hours=i),
            )

        response = await client.get("/api/v1/sync-logs?limit=10")
        data = response.json()
        assert data["pagination"]["has_next"] is False
        assert data["pagination"]["next_cursor"] is None
