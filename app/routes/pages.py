import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.config import get_settings
from app.csrf import generate_csrf_token
from app.database import get_session
from app.api.deps import OptionalUserDep
from app.templating import templates
from app.services.oidc import get_oidc_config

logger = logging.getLogger(__name__)

router = APIRouter()


# "/" is served by app.routes.spa (specs/insight-ui.md AC-024).


@router.get("/analytics")
async def analytics_page():
    """Legacy link: the analytics tab became the SPA Trends page."""
    return RedirectResponse(url="/app/trends", status_code=302)


@router.get("/notifications")
async def notifications_page(request: Request, user: OptionalUserDep = None):
    """Webhook delivery history — server-rendered, reached from the SPA menu."""
    return templates.TemplateResponse(
        request, "notifications.html", context={"user": user}
    )


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


# Settings moved into the SPA (specs/settings-ui.md AC-020). The old URLs stay
# as redirects so bookmarks and the legacy Jinja nav keep working; the SPA
# handles the ``#changelog`` fragment itself since fragments never reach us.
@router.get("/settings")
async def settings_redirect() -> RedirectResponse:
    return RedirectResponse(url="/app/settings", status_code=302)


@router.get("/admin/users")
async def admin_users_redirect() -> RedirectResponse:
    return RedirectResponse(url="/app/settings/users", status_code=302)


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
