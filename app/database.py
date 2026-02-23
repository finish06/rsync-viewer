from typing import Generator
from sqlmodel import Session, create_engine
from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
