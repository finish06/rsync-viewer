import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from app.config import get_settings
from app.csrf import generate_csrf_token
from app.database import get_session
from app.api.deps import OptionalUserDep
from app.templating import templates
from app.models.sync_log import SyncLog
from app.services.auth import role_at_least, ROLE_OPERATOR
from app.services.synthetic_check import SYNTHETIC_SOURCE_NAME, get_db_config
from app.services.changelog_parser import parse_changelog
from app.services.oidc import get_oidc_config

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def index(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """Main dashboard page"""

    # Get unique sources for filter dropdown (AC-011: exclude synthetic)
    sources = session.exec(
        select(SyncLog.source_name)
        .where(SyncLog.source_name != SYNTHETIC_SOURCE_NAME)
        .distinct()
        .order_by(SyncLog.source_name)
    ).all()

    # Check if synthetic monitoring is enabled (AC-004/AC-005)
    synthetic_monitoring_enabled = get_db_config(session).enabled

    return templates.TemplateResponse(
        request,
        "index.html",
        context={
            "sources": sources,
            "user": user,
            "synthetic_monitoring_enabled": synthetic_monitoring_enabled,
        },
    )


@router.get("/analytics")
async def analytics_page():
    """Redirect to dashboard analytics tab."""
    return RedirectResponse(url="/?tab=analytics", status_code=302)


@router.get("/login")
async def login_page(
    request: Request,
    session: Session = Depends(get_session),
    return_url: Optional[str] = Query(None),
    success: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """Render login page."""
    settings = get_settings()
    csrf_token = generate_csrf_token()
    success_message = None
    if success == "registered":
        success_message = "Account created successfully. Please log in."

    error_message = None
    if error == "oidc_unavailable":
        error_message = (
            "Unable to reach authentication provider. Please try again later."
        )
    elif error == "oidc_denied":
        error_message = "Authentication was denied by the provider."
    elif error == "oidc_expired":
        error_message = "Login session expired. Please try again."
    elif error == "oidc_failed":
        error_message = "Authentication failed. Please try again."
    elif error == "oidc_invalid":
        error_message = "Invalid authentication response. Please try again."

    # Check OIDC configuration
    oidc_config = get_oidc_config(session)
    oidc_enabled = bool(oidc_config and oidc_config.enabled)
    oidc_provider_name = oidc_config.provider_name if oidc_config else ""
    hide_local_login = bool(
        oidc_enabled
        and oidc_config
        and oidc_config.hide_local_login
        and not settings.force_local_login
    )

    response = templates.TemplateResponse(
        request,
        "login.html",
        context={
            "csrf_token": csrf_token,
            "return_url": return_url or "",
            "success_message": success_message,
            "error_message": error_message,
            "oidc_enabled": oidc_enabled,
            "oidc_provider_name": oidc_provider_name,
            "hide_local_login": hide_local_login,
        },
    )
    response.set_cookie("csrf_token", csrf_token, httponly=False, samesite="lax")
    return response


@router.get("/register")
async def register_page(request: Request):
    """Render registration page."""
    settings = get_settings()
    if not settings.registration_enabled:
        return templates.TemplateResponse(
            request,
            "register.html",
            context={"registration_disabled": True},
        )

    csrf_token = generate_csrf_token()
    response = templates.TemplateResponse(
        request,
        "register.html",
        context={"csrf_token": csrf_token},
    )
    response.set_cookie("csrf_token", csrf_token, httponly=False, samesite="lax")
    return response


@router.get("/settings")
async def settings_page(request: Request, user: OptionalUserDep = None):
    """Settings page — requires Operator+ role."""
    if user and not role_at_least(user.role, ROLE_OPERATOR):
        raise HTTPException(status_code=403, detail="Requires operator role")
    changelog_versions = parse_changelog(path=Path("CHANGELOG.md"))
    return templates.TemplateResponse(
        request,
        "settings.html",
        context={"changelog_available": len(changelog_versions) > 0, "user": user},
    )


@router.get("/htmx/changelog")
async def htmx_changelog_list(request: Request, show_all: bool = False):
    """HTMX partial: changelog version accordion list."""
    versions = [
        v
        for v in parse_changelog(path=Path("CHANGELOG.md"))
        if v.version != "Unreleased"
    ]
    current_settings = get_settings()
    has_more = len(versions) > 5 and not show_all
    display_versions = versions if show_all else versions[:5]
    return templates.TemplateResponse(
        request,
        "partials/changelog_list.html",
        context={
            "versions": display_versions,
            "app_version": current_settings.app_version,
            "has_more": has_more,
        },
    )


@router.get("/htmx/changelog/{version}")
async def htmx_changelog_detail(request: Request, version: str):
    """HTMX partial: expanded version content with grouped sections."""
    versions = parse_changelog(path=Path("CHANGELOG.md"))
    target = next((v for v in versions if v.version == version), None)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Version {version} not found")
    return templates.TemplateResponse(
        request,
        "partials/changelog_detail.html",
        context={"version": target},
    )


@router.get("/forgot-password")
async def forgot_password_page(request: Request):
    """Render forgot password page."""
    csrf_token = generate_csrf_token()
    response = templates.TemplateResponse(
        request,
        "forgot_password.html",
        context={"csrf_token": csrf_token},
    )
    response.set_cookie("csrf_token", csrf_token, httponly=False, samesite="lax")
    return response


@router.get("/reset-password")
async def reset_password_page(
    request: Request,
    token: Optional[str] = Query(None),
):
    """Render reset password page."""
    csrf_token = generate_csrf_token()
    response = templates.TemplateResponse(
        request,
        "reset_password.html",
        context={"csrf_token": csrf_token, "token": token or ""},
    )
    response.set_cookie("csrf_token", csrf_token, httponly=False, samesite="lax")
    return response
