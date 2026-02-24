from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Rsync Log Viewer"
    debug: bool = False
    database_url: str
    secret_key: str = "change-me"
    default_api_key: str = "rsv_dev_key"
    log_level: str = "INFO"
    log_format: str = "json"
    rate_limit_authenticated: str = "60/minute"
    rate_limit_unauthenticated: str = "20/minute"
    max_request_body_size: int = 10_485_760  # 10MB
    hsts_enabled: bool = False
    csp_report_only: bool = True
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    query_timeout_seconds: int = 30
    metrics_enabled: bool = True
    data_retention_days: int = 0  # 0 = disabled (keep forever)
    retention_cleanup_interval_hours: int = 24
    app_version: str = "1.7.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # database_url comes from env/.env
