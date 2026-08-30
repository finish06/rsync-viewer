from functools import lru_cache
from pydantic import field_validator
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
    # Uvicorn honours X-Forwarded-* only from these IPs (comma-separated, or "*").
    forwarded_allow_ips: str = "127.0.0.1"
    # Update awareness (cicd-release AC-006): poll the GitHub releases API.
    update_check_enabled: bool = True
    update_check_ttl_seconds: int = 21600
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

    @field_validator("app_version")
    @classmethod
    def _strip_tag_prefix(cls, value: str) -> str:
        """CI builds pass the git tag (v2.18.0); everything downstream —
        changelog "current" badge, update comparison — expects 2.18.0."""
        return value[1:] if value.startswith("v") and value[1:2].isdigit() else value

    base_url: str = "http://127.0.0.1:8000"  # Used by synthetic monitoring
    spa_dist_dir: str = "app/static/app"  # Vite build output served at /app

    @property
    def effective_encryption_key(self) -> str:
        """Return the encryption key to use. Prefers smtp_encryption_key for backward compat."""
        return self.smtp_encryption_key or self.encryption_key


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # database_url comes from env/.env
