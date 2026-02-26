import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserCreate(BaseModel):
    """Schema for user registration."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Unique username (3-50 characters, alphanumeric and underscores)",
        examples=["admin"],
    )
    email: str = Field(
        ...,
        max_length=255,
        description="Valid email address",
        examples=["admin@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (min 8 chars, must include uppercase, lowercase, and digit)",
        examples=["SecurePass123!"],
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError(
                "Username must contain only letters, numbers, and underscores"
            )
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserResponse(BaseModel):
    """Schema for user response (no password)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    role: str
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime


class UserLogin(BaseModel):
    """Schema for user login."""

    username: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1, description="Password")


class TokenResponse(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str


class RoleUpdate(BaseModel):
    """Schema for changing a user's role."""

    role: str = Field(
        ...,
        description="New role (admin, operator, or viewer)",
        examples=["operator"],
    )


class StatusUpdate(BaseModel):
    """Schema for enabling/disabling a user."""

    is_active: bool = Field(..., description="Whether the user account is active")


class PasswordResetRequest(BaseModel):
    """Schema for requesting a password reset."""

    email: str = Field(..., description="Email address of the account to reset")


class PasswordResetConfirm(BaseModel):
    """Schema for confirming a password reset."""

    token: str = Field(..., description="The reset token")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (min 8 chars, must include uppercase, lowercase, and digit)",
    )

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        return v


class PasswordResetResponse(BaseModel):
    """Schema for password reset response."""

    message: str
    reset_token: Optional[str] = None  # Only in debug/console mode


class ApiKeyCreate(BaseModel):
    """Schema for creating a new API key."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human-readable name for this key",
        examples=["My Script Key"],
    )
    role_override: Optional[str] = Field(
        default=None,
        description="Optional role override (must be <= user's role)",
        examples=["viewer"],
    )


class ApiKeyResponse(BaseModel):
    """Schema for API key response (list view — no raw key)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    key_prefix: str
    is_active: bool
    role_override: Optional[str] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None
    user_id: Optional[UUID] = None


class ApiKeyCreatedResponse(BaseModel):
    """Schema for newly created API key (includes raw key, shown once)."""

    id: UUID
    name: str
    key: str  # plaintext key — shown ONCE at creation
    key_prefix: str
    role: str  # effective role (role_override or user's role)
    created_at: datetime
