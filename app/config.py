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
    jwt_access_expiry_minutes: int = 1440  # 24 hours
    jwt_refresh_expiry_days: int = 30
    jwt_algorithm: str = "HS256"
    auth_enabled: bool = False  # Auto-enables when first user registers
    registration_enabled: bool = True  # Set to false to disable new user registration
    smtp_encryption_key: str = ""  # Fernet key for encrypting SMTP credentials
    encryption_key: str = (
        ""  # Shared Fernet key (used for OIDC + SMTP if smtp_encryption_key is empty)
    )
    force_local_login: bool = False  # Safety fallback: always show local login form
    synthetic_check_enabled: bool = False  # Enable synthetic monitoring
    synthetic_check_interval_seconds: int = 300  # Seconds between checks (min 30)
    synthetic_check_api_key: str = (
        ""  # Dedicated API key; falls back to default_api_key
    )
    app_version: str = "dev"

    @property
    def effective_encryption_key(self) -> str:
        """Return the encryption key to use. Prefers smtp_encryption_key for backward compat."""
        return self.smtp_encryption_key or self.encryption_key


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # database_url comes from env/.env
