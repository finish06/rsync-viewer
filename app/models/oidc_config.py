from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.utils import utc_now


class OidcConfig(SQLModel, table=True):
    __tablename__ = "oidc_config"

    id: int = Field(default=None, primary_key=True)
    issuer_url: str = Field(max_length=512)
    client_id: str = Field(max_length=255)
    encrypted_client_secret: str = Field()
    provider_name: str = Field(max_length=100)
    enabled: bool = Field(default=False)
    hide_local_login: bool = Field(default=False)
    scopes: str = Field(default="openid email profile", max_length=255)
    configured_by_id: Optional[UUID] = Field(
        default=None, foreign_key="users.id", index=True
    )
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
