"""Shared Jinja2 template configuration and helper functions.

Extracted from app.main to avoid circular imports when route modules
need access to templates and formatting utilities (AC-001).
"""

import re
from datetime import timedelta
from typing import Optional

from fastapi.templating import Jinja2Templates

from app.config import get_settings

DISCORD_URL_PATTERN = re.compile(
    r"^https://(discord\.com|discordapp\.com)/api/webhooks/\d+/.+"
)


def _form_str(form: object, key: str, default: str = "") -> str:
    """Extract a string value from form data, handling UploadFile edge cases."""
    value = getattr(form, "get", lambda k, d: d)(key, default)
    return str(value) if value is not None else default


def format_bytes(value: Optional[int]) -> str:
    """Format bytes to human readable format"""
    if value is None:
        return "-"
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if abs(value) < 1024.0:
            return f"{value:.2f} {unit}"
        value = int(value / 1024.0)
    return f"{value:.2f} PB"


def format_duration(delta: timedelta) -> str:
    """Format timedelta to human readable format"""
    total_seconds = int(delta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")

    return " ".join(parts)


def format_rate(sync) -> str:
    """Format average transfer rate from a sync log object."""
    if sync.is_dry_run:
        return "-"
    if sync.bytes_received is None:
        return "-"
    if not sync.start_time or not sync.end_time:
        return "-"
    duration_seconds = (sync.end_time - sync.start_time).total_seconds()
    if duration_seconds <= 0:
        return "-"
    rate = sync.bytes_received / duration_seconds
    for unit in ["B/s", "KB/s", "MB/s", "GB/s", "TB/s"]:
        if abs(rate) < 1024.0:
            return f"{rate:.2f} {unit}"
        rate /= 1024.0
    return f"{rate:.2f} PB/s"


settings = get_settings()

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["app_version"] = settings.app_version
templates.env.filters["format_bytes"] = format_bytes
templates.env.filters["format_duration"] = format_duration
templates.env.filters["format_rate"] = format_rate
