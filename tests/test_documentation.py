"""Tests for project documentation completeness.

Spec: specs/documentation.md
ACs: AC-001 through AC-008
"""

import os


DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")


class TestSetupGuide:
    """AC-001: A development environment setup guide exists."""

    def test_ac001_setup_guide_exists(self):
        """docs/setup.md exists."""
        assert os.path.isfile(os.path.join(DOCS_DIR, "setup.md"))

    def test_ac001_setup_guide_has_prerequisites(self):
        """Setup guide covers prerequisites."""
        with open(os.path.join(DOCS_DIR, "setup.md")) as f:
            content = f.read().lower()
        assert "prerequisite" in content or "requirements" in content

    def test_ac001_setup_guide_has_docker_section(self):
        """Setup guide covers Docker deployment."""
        with open(os.path.join(DOCS_DIR, "setup.md")) as f:
            content = f.read().lower()
        assert "docker" in content

    def test_ac001_setup_guide_has_local_dev(self):
        """Setup guide covers local development setup."""
        with open(os.path.join(DOCS_DIR, "setup.md")) as f:
            content = f.read().lower()
        assert "local" in content or "development" in content


class TestEnvironmentVariables:
    """AC-002: All environment variables documented."""

    def test_ac002_env_vars_doc_exists(self):
        """docs/environment-variables.md exists."""
        assert os.path.isfile(os.path.join(DOCS_DIR, "environment-variables.md"))

    def test_ac002_documents_database_url(self):
        """DATABASE_URL is documented."""
        with open(os.path.join(DOCS_DIR, "environment-variables.md")) as f:
            content = f.read()
        assert "DATABASE_URL" in content

    def test_ac002_documents_all_config_vars(self):
        """All Settings fields from app/config.py are documented."""
        with open(os.path.join(DOCS_DIR, "environment-variables.md")) as f:
            content = f.read()
        required_vars = [
            "DATABASE_URL",
            "SECRET_KEY",
            "DEFAULT_API_KEY",
            "LOG_LEVEL",
            "RATE_LIMIT_AUTHENTICATED",
            "MAX_REQUEST_BODY_SIZE",
            "DB_POOL_SIZE",
            "METRICS_ENABLED",
            "DATA_RETENTION_DAYS",
        ]
        for var in required_vars:
            assert var in content, f"Missing documentation for {var}"

    def test_ac002_has_defaults_column(self):
        """Environment variable docs include defaults."""
        with open(os.path.join(DOCS_DIR, "environment-variables.md")) as f:
            content = f.read().lower()
        assert "default" in content


class TestArchitectureDiagram:
    """AC-003: System architecture diagram exists."""

    def test_ac003_architecture_doc_exists(self):
        """docs/architecture.md exists."""
        assert os.path.isfile(os.path.join(DOCS_DIR, "architecture.md"))

    def test_ac003_has_mermaid_diagram(self):
        """Architecture doc contains a Mermaid diagram."""
        with open(os.path.join(DOCS_DIR, "architecture.md")) as f:
            content = f.read()
        assert "```mermaid" in content

    def test_ac003_mentions_key_components(self):
        """Architecture doc mentions FastAPI, PostgreSQL, HTMX."""
        with open(os.path.join(DOCS_DIR, "architecture.md")) as f:
            content = f.read().lower()
        assert "fastapi" in content
        assert "postgres" in content
        assert "htmx" in content


class TestDatabaseSchema:
    """AC-004: Database schema documentation."""

    def test_ac004_schema_doc_exists(self):
        """docs/database-schema.md exists."""
        assert os.path.isfile(os.path.join(DOCS_DIR, "database-schema.md"))

    def test_ac004_documents_all_tables(self):
        """Schema doc covers all database tables."""
        with open(os.path.join(DOCS_DIR, "database-schema.md")) as f:
            content = f.read().lower()
        tables = [
            "sync_logs",
            "failure_events",
            "sync_source_monitors",
            "webhook_endpoints",
            "notification_logs",
            "api_keys",
        ]
        for table in tables:
            assert table in content, f"Missing documentation for table {table}"

    def test_ac004_documents_relationships(self):
        """Schema doc describes foreign key relationships."""
        with open(os.path.join(DOCS_DIR, "database-schema.md")) as f:
            content = f.read().lower()
        assert "foreign key" in content or "relationship" in content or "references" in content


class TestDataFlow:
    """AC-005: Data flow documentation."""

    def test_ac005_data_flow_documented(self):
        """Architecture doc describes the data flow."""
        with open(os.path.join(DOCS_DIR, "architecture.md")) as f:
            content = f.read().lower()
        assert "data flow" in content or "submission" in content


class TestIngestionGuide:
    """AC-006: Rsync log ingestion configuration guide."""

    def test_ac006_ingestion_guide_exists(self):
        """docs/ingestion-guide.md exists."""
        assert os.path.isfile(os.path.join(DOCS_DIR, "ingestion-guide.md"))

    def test_ac006_has_api_example(self):
        """Ingestion guide includes API call example."""
        with open(os.path.join(DOCS_DIR, "ingestion-guide.md")) as f:
            content = f.read()
        assert "curl" in content.lower() or "api/v1/sync-logs" in content

    def test_ac006_has_script_example(self):
        """Ingestion guide includes rsync script integration."""
        with open(os.path.join(DOCS_DIR, "ingestion-guide.md")) as f:
            content = f.read().lower()
        assert "rsync" in content and ("script" in content or "bash" in content)


class TestTroubleshooting:
    """AC-007: Troubleshooting guide."""

    def test_ac007_troubleshooting_exists(self):
        """docs/troubleshooting.md exists."""
        assert os.path.isfile(os.path.join(DOCS_DIR, "troubleshooting.md"))

    def test_ac007_covers_db_issues(self):
        """Troubleshooting covers database connection issues."""
        with open(os.path.join(DOCS_DIR, "troubleshooting.md")) as f:
            content = f.read().lower()
        assert "database" in content or "connection" in content

    def test_ac007_covers_docker_issues(self):
        """Troubleshooting covers Docker networking issues."""
        with open(os.path.join(DOCS_DIR, "troubleshooting.md")) as f:
            content = f.read().lower()
        assert "docker" in content


class TestGrafanaDashboards:
    """AC-005, AC-006 from specs/metrics-export.md: Grafana dashboard templates."""

    def test_ac005_grafana_directory_exists(self):
        """grafana/ directory exists."""
        grafana_dir = os.path.join(os.path.dirname(__file__), "..", "grafana")
        assert os.path.isdir(grafana_dir)

    def test_ac005_sync_overview_dashboard_exists(self):
        """grafana/sync-overview.json exists."""
        path = os.path.join(os.path.dirname(__file__), "..", "grafana", "sync-overview.json")
        assert os.path.isfile(path)

    def test_ac006_sync_dashboard_has_panels(self):
        """Sync overview dashboard contains expected panels."""
        import json

        path = os.path.join(os.path.dirname(__file__), "..", "grafana", "sync-overview.json")
        with open(path) as f:
            dashboard = json.load(f)
        # Should have panels array
        assert "panels" in dashboard
        panel_titles = [p.get("title", "").lower() for p in dashboard["panels"]]
        panel_text = " ".join(panel_titles)
        assert "sync" in panel_text or "frequency" in panel_text or "duration" in panel_text

    def test_ac005_api_dashboard_exists(self):
        """grafana/api-performance.json exists."""
        path = os.path.join(os.path.dirname(__file__), "..", "grafana", "api-performance.json")
        assert os.path.isfile(path)

    def test_ac006_api_dashboard_has_panels(self):
        """API performance dashboard contains expected panels."""
        import json

        path = os.path.join(os.path.dirname(__file__), "..", "grafana", "api-performance.json")
        with open(path) as f:
            dashboard = json.load(f)
        assert "panels" in dashboard
        panel_titles = [p.get("title", "").lower() for p in dashboard["panels"]]
        panel_text = " ".join(panel_titles)
        assert "request" in panel_text or "latency" in panel_text or "api" in panel_text

    def test_ac005_dashboards_are_valid_json(self):
        """Both dashboard files are valid JSON with required fields."""
        import json

        grafana_dir = os.path.join(os.path.dirname(__file__), "..", "grafana")
        for name in ["sync-overview.json", "api-performance.json"]:
            path = os.path.join(grafana_dir, name)
            with open(path) as f:
                dashboard = json.load(f)
            assert "title" in dashboard, f"{name} missing title"
            assert "panels" in dashboard, f"{name} missing panels"
