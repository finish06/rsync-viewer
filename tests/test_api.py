from datetime import timedelta
from app.utils import utc_now


class TestCreateSyncLog:
    """Test POST /api/v1/sync-logs endpoint"""

    async def test_create_sync_log_success(self, client, sample_sync_log_data):
        """Test creating a sync log with valid data"""
        response = await client.post(
            "/api/v1/sync-logs",
            json=sample_sync_log_data,
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["source_name"] == sample_sync_log_data["source_name"]
        assert "id" in data
        assert data["status"] == "completed"
        assert data["bytes_sent"] == int(100)
        assert data["bytes_received"] == int(1.00 * 1024)

    async def test_create_sync_log_missing_api_key(
        self, unauth_client, sample_sync_log_data
    ):
        """Test that authentication is required"""
        response = await unauth_client.post(
            "/api/v1/sync-logs",
            json=sample_sync_log_data,
        )

        assert response.status_code == 401
        assert "required" in response.json()["detail"].lower()

    async def test_create_sync_log_invalid_api_key(self, client, sample_sync_log_data):
        """Test that invalid API key is rejected"""
        response = await client.post(
            "/api/v1/sync-logs",
            json=sample_sync_log_data,
            headers={"X-API-Key": "invalid-key"},
        )

        assert response.status_code == 401

    async def test_create_sync_log_parses_dry_run(self, client):
        """Test that dry run flag is parsed from content"""
        now = utc_now()
        data = {
            "source_name": "test",
            "start_time": (now - timedelta(minutes=1)).isoformat(),
            "end_time": now.isoformat(),
            "raw_content": "sent 100 bytes  received 200 bytes  300 bytes/sec\ntotal size is 1000  speedup is 10.00 (DRY RUN)",
        }

        response = await client.post(
            "/api/v1/sync-logs",
            json=data,
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 201
        assert response.json()["is_dry_run"] is True

    async def test_create_sync_log_missing_required_fields(self, client):
        """Test that missing required fields return validation error"""
        response = await client.post(
            "/api/v1/sync-logs",
            json={"source_name": "test"},
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 422


class TestListSyncLogs:
    """Test GET /api/v1/sync-logs endpoint"""

    async def test_list_sync_logs_empty(self, client):
        """Test listing sync logs when none exist"""
        response = await client.get("/api/v1/sync-logs")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["pagination"]["has_next"] is False

    async def test_list_sync_logs_with_data(self, client, create_sync_log):
        """Test listing sync logs returns created logs"""
        create_sync_log(source_name="source-a")
        create_sync_log(source_name="source-b")

        response = await client.get("/api/v1/sync-logs")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

    async def test_list_sync_logs_pagination(self, client, create_sync_log):
        """Test pagination parameters"""
        for i in range(5):
            create_sync_log(source_name=f"source-{i}")

        response = await client.get("/api/v1/sync-logs?offset=2&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["offset"] == 2
        assert data["limit"] == 2

    async def test_list_sync_logs_filter_by_source(self, client, create_sync_log):
        """Test filtering by source name"""
        create_sync_log(source_name="backup-server")
        create_sync_log(source_name="backup-server")
        create_sync_log(source_name="other-source")

        response = await client.get("/api/v1/sync-logs?source_name=backup-server")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        for item in data["items"]:
            assert item["source_name"] == "backup-server"

    async def test_list_sync_logs_filter_by_date_range(self, client, create_sync_log):
        """Test filtering by date range"""
        now = utc_now()
        old_date = now - timedelta(days=10)
        recent_date = now - timedelta(hours=1)

        create_sync_log(start_time=old_date, end_time=old_date + timedelta(minutes=5))
        create_sync_log(
            start_time=recent_date, end_time=recent_date + timedelta(minutes=5)
        )

        start_filter = (now - timedelta(days=1)).isoformat()
        response = await client.get(f"/api/v1/sync-logs?start_date={start_filter}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1


class TestGetSyncLog:
    """Test GET /api/v1/sync-logs/{id} endpoint"""

    async def test_get_sync_log_success(self, client, create_sync_log):
        """Test getting a specific sync log"""
        log = create_sync_log(
            source_name="test-source",
            total_size_bytes=1000000,
            file_count=5,
        )

        response = await client.get(f"/api/v1/sync-logs/{log.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(log.id)
        assert data["source_name"] == "test-source"
        assert data["total_size_bytes"] == 1000000
        assert data["file_count"] == 5
        assert "raw_content" in data

    async def test_get_sync_log_not_found(self, client):
        """Test getting a non-existent sync log"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/sync-logs/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_get_sync_log_invalid_uuid(self, client):
        """Test getting sync log with invalid UUID format"""
        response = await client.get("/api/v1/sync-logs/not-a-uuid")

        assert response.status_code == 422


class TestListSources:
    """Test GET /api/v1/sync-logs/sources endpoint"""

    async def test_list_sources_empty(self, client):
        """Test listing sources when none exist"""
        response = await client.get("/api/v1/sync-logs/sources")

        assert response.status_code == 200
        data = response.json()
        assert data["sources"] == []

    async def test_list_sources_returns_unique(self, client, create_sync_log):
        """Test that sources are unique"""
        create_sync_log(source_name="backup-1")
        create_sync_log(source_name="backup-1")
        create_sync_log(source_name="backup-2")
        create_sync_log(source_name="backup-3")

        response = await client.get("/api/v1/sync-logs/sources")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sources"]) == 3
        assert "backup-1" in data["sources"]
        assert "backup-2" in data["sources"]
        assert "backup-3" in data["sources"]

    async def test_list_sources_sorted(self, client, create_sync_log):
        """Test that sources are sorted alphabetically"""
        create_sync_log(source_name="charlie")
        create_sync_log(source_name="alpha")
        create_sync_log(source_name="bravo")

        response = await client.get("/api/v1/sync-logs/sources")

        assert response.status_code == 200
        data = response.json()
        assert data["sources"] == ["alpha", "bravo", "charlie"]


class TestHealthEndpoint:
    """Test GET /health endpoint"""

    async def test_health_check(self, client):
        """Test health check endpoint returns ok"""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
