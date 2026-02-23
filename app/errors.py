"""Application error codes and custom exceptions."""

from typing import Optional

from pydantic import BaseModel, Field

from app.utils import utc_now


# Error code constants
API_KEY_REQUIRED = "API_KEY_REQUIRED"
API_KEY_INVALID = "API_KEY_INVALID"
RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
VALIDATION_ERROR = "VALIDATION_ERROR"
DATABASE_ERROR = "DATABASE_ERROR"
INTERNAL_ERROR = "INTERNAL_ERROR"
BAD_REQUEST = "BAD_REQUEST"


class ErrorResponse(BaseModel):
    """Structured error response for all API errors."""

    error_code: str = Field(..., description="Uppercase snake_case error identifier")
    message: str = Field(..., description="Human-readable error description")
    detail: Optional[str] = Field(
        None, description="Additional detail (backward compatibility)"
    )
    timestamp: str = Field(..., description="ISO 8601 timestamp when error occurred")
    path: str = Field(..., description="Request path that triggered the error")
    validation_errors: Optional[list[dict]] = Field(
        None, description="Field-level validation errors (422 only)"
    )


def make_error_response(
    error_code: str,
    message: str,
    path: str,
    detail: Optional[str] = None,
    validation_errors: Optional[list[dict]] = None,
) -> dict:
    """Build a structured error response dict."""
    return ErrorResponse(
        error_code=error_code,
        message=message,
        detail=detail or message,
        timestamp=utc_now().isoformat(),
        path=path,
        validation_errors=validation_errors,
    ).model_dump()
