import os
from datetime import datetime, timedelta
from typing import Annotated, Generator, Optional as TypingOptional
from uuid import uuid4

import pytest
from fastapi import Header, HTTPException, status
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session, SQLModel, create_engine

from app.config import Settings, get_settings
from app.csrf import generate_csrf_token
from app.database import get_session
from app.api.deps import verify_api_key
from app.main import app
from app.models.sync_log import SyncLog
from app.models.monitor import SyncSourceMonitor  # noqa: F401 — ensure table creation
from app.models.failure_event import FailureEvent  # noqa: F401 — ensure table creation
from app.models.webhook import WebhookEndpoint  # noqa: F401 — ensure table creation
from app.models.notification_log import NotificationLog  # noqa: F401 — ensure table creation
from app.models.webhook_options import WebhookOptions  # noqa: F401 — ensure table creation
from app.utils import utc_now


# Get database URL from environment or use default test database
TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5433/rsync_viewer_test",
)


def get_test_settings() -> Settings:
    """Override settings for testing"""
    return Settings(
        app_name="Rsync Log Viewer Test",
        debug=True,
        database_url=TEST_DATABASE_URL,
        secret_key="test-secret-key",
        default_api_key="test-api-key",
    )


@pytest.fixture(scope="session")
def test_engine():
    """Create a PostgreSQL engine for tests"""
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    SQLModel.metadata.create_all(engine)
    yield engine


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create a database session for each test with rollback"""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


async def mock_verify_api_key(
    x_api_key: Annotated[TypingOptional[str], Header()] = None,
):
    """Mock API key verification for tests"""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    if x_api_key == "test-api-key":
        return None  # Valid test key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or inactive API key",
    )


@pytest.fixture(scope="function")
def client(test_engine, db_session) -> Generator[AsyncClient, None, None]:
    """Create an async test client with overridden dependencies"""

    def get_test_session():
        yield db_session

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_settings] = get_test_settings
    app.dependency_overrides[verify_api_key] = mock_verify_api_key

    csrf_token = generate_csrf_token()

    yield AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-CSRF-Token": csrf_token},
        cookies={"csrf_token": csrf_token},
    )

    app.dependency_overrides.clear()


# Sample rsync output fixtures
@pytest.fixture
def sample_rsync_output_basic() -> str:
    """Standard rsync output with all typical fields"""
    return """receiving file list ... done
photos/2024/vacation/img_001.jpg
photos/2024/vacation/img_002.jpg
photos/2024/vacation/img_003.jpg
documents/report.pdf
backup/database.sql

sent 2.87K bytes  received 291.07K bytes  117.58K bytes/sec
total size is 18.70G  speedup is 63.94"""


@pytest.fixture
def sample_rsync_output_dry_run() -> str:
    """Rsync dry run output"""
    return """receiving file list ... done
photos/2024/vacation/img_001.jpg
photos/2024/vacation/img_002.jpg

sent 150 bytes  received 1.50K bytes  1.10K bytes/sec
total size is 5.00M  speedup is 3030.30 (DRY RUN)"""


@pytest.fixture
def sample_rsync_output_terabytes() -> str:
    """Rsync output with terabyte-scale data"""
    return """receiving file list ... done
backup/full_backup_2024.tar.gz

sent 1.23M bytes  received 456.78G bytes  50.00M bytes/sec
total size is 18.70T  speedup is 63604231.94"""


@pytest.fixture
def sample_rsync_output_kilobytes() -> str:
    """Rsync output with kilobyte-scale data"""
    return """receiving file list ... done
config.yml

sent 100 bytes  received 5.5K bytes  5.6K bytes/sec
total size is 5500  speedup is 1.00"""


@pytest.fixture
def sample_rsync_output_empty() -> str:
    """Empty rsync output (no files transferred)"""
    return """receiving file list ... done

sent 20 bytes  received 50 bytes  70.00 bytes/sec
total size is 0  speedup is 0.00"""


@pytest.fixture
def sample_rsync_output_malformed() -> str:
    """Malformed/incomplete rsync output"""
    return """starting rsync process
error connecting to host
connection timed out"""


@pytest.fixture
def sample_sync_log_data() -> dict:
    """Sample data for creating a sync log via API"""
    now = utc_now()
    return {
        "source_name": "test-backup",
        "start_time": (now - timedelta(minutes=5)).isoformat(),
        "end_time": now.isoformat(),
        "raw_content": """receiving file list ... done
test_file.txt

sent 100 bytes  received 1.00K bytes  1.10K bytes/sec
total size is 1.00M  speedup is 909.09""",
    }


@pytest.fixture
def create_sync_log(db_session: Session):
    """Factory fixture to create sync logs in the database"""

    def _create(
        source_name: str = "test-source",
        start_time: datetime = None,
        end_time: datetime = None,
        raw_content: str = "test content",
        total_size_bytes: int = None,
        bytes_sent: int = None,
        bytes_received: int = None,
        transfer_speed: float = None,
        file_count: int = 0,
        file_list: list[str] = None,
        is_dry_run: bool = False,
        exit_code: int = 0,
    ) -> SyncLog:
        now = utc_now()
        sync_log = SyncLog(
            id=uuid4(),
            source_name=source_name,
            start_time=start_time or (now - timedelta(minutes=5)),
            end_time=end_time or now,
            raw_content=raw_content,
            total_size_bytes=total_size_bytes,
            bytes_sent=bytes_sent,
            bytes_received=bytes_received,
            transfer_speed=transfer_speed,
            file_count=file_count,
            file_list=file_list,
            is_dry_run=is_dry_run,
            exit_code=exit_code,
        )
        db_session.add(sync_log)
        db_session.commit()
        db_session.refresh(sync_log)
        return sync_log

    return _create
