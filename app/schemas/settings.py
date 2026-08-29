"""Request/response schemas for the settings API (specs/settings-ui.md)."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

SmtpEncryption = Literal["none", "starttls", "ssl_tls"]


class SmtpSettingsRead(BaseModel):
    configured: bool
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    encryption: SmtpEncryption = "starttls"
    from_address: Optional[str] = None
    from_name: Optional[str] = None
    enabled: bool = True
    has_password: bool = False
    encryption_key_configured: bool
    updated_at: Optional[datetime] = None


class SmtpSettingsWrite(BaseModel):
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535)
    username: Optional[str] = Field(default=None, max_length=255)
    password: Optional[str] = Field(
        default=None, description="Leave empty to keep the stored password"
    )
    encryption: SmtpEncryption = "starttls"
    from_address: str = Field(min_length=1, max_length=255)
    from_name: str = Field(default="Rsync Viewer", max_length=255)
    enabled: bool = True


class SmtpTestRequest(BaseModel):
    to_address: str = Field(min_length=3, max_length=255)


class SmtpTestResponse(BaseModel):
    sent: bool
    to_address: str


class OidcSettingsRead(BaseModel):
    configured: bool
    issuer_url: Optional[str] = None
    client_id: Optional[str] = None
    provider_name: Optional[str] = None
    scopes: str = "openid email profile"
    enabled: bool = False
    hide_local_login: bool = False
    has_client_secret: bool = False
    callback_url: str
    encryption_key_configured: bool
    updated_at: Optional[datetime] = None


class OidcSettingsWrite(BaseModel):
    issuer_url: str = Field(min_length=1, max_length=512)
    client_id: str = Field(min_length=1, max_length=255)
    client_secret: Optional[str] = Field(
        default=None, description="Required on first configuration"
    )
    provider_name: str = Field(min_length=1, max_length=100)
    scopes: str = Field(default="openid email profile", max_length=255)
    enabled: bool = False
    hide_local_login: bool = False


class OidcDiscoveryRequest(BaseModel):
    issuer_url: str = Field(min_length=1, max_length=512)


class OidcDiscoveryResponse(BaseModel):
    issuer_url: str
    endpoints: dict[str, str]


class SyntheticSettingsRead(BaseModel):
    enabled: bool
    interval_seconds: int
    last_status: str
    last_check_at: Optional[datetime] = None
    last_latency_ms: Optional[float] = None
    last_error: Optional[str] = None


class SyntheticSettingsWrite(BaseModel):
    enabled: bool
    interval_seconds: int = Field(ge=1, le=86_400)


class MonitoringSetupRequest(BaseModel):
    source_name: str = Field(min_length=1, max_length=100)
    rsync_source: str = Field(min_length=3, max_length=512)
    cron_schedule: str = Field(default="0 */6 * * *", max_length=100)
    ssh_key_path: str = Field(default="~/.ssh/id_rsa", max_length=512)
    rsync_args: str = Field(default="-avz --stats", max_length=512)
    sync_mode: Literal["pull", "push"] = "pull"


class MonitoringSetupResponse(BaseModel):
    source_name: str
    key_name: str
    api_key: str = Field(description="Shown once; not retrievable later")
    snippet: str
