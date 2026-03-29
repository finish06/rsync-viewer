import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from app.config import get_settings
from app.csrf import generate_csrf_token
from app.database import get_session
from app.templating import templates
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.auth import create_access_token, verify_password
from app.services.oidc import (
    build_authorize_url,
    decode_id_token,
    exchange_code_for_tokens,
    get_oidc_config,
    get_or_create_oidc_user,
    validate_state,
)
from app.services.registration import RegistrationError, register_user
from app.utils import utc_now

logger = logging.getLogger(__name__)

router = APIRouter()


def _safe_return_url(url: str) -> str:
    """Validate return_url is a safe relative path (prevent open redirect)."""
    if url.startswith("/") and not url.startswith("//"):
        return url
    return "/"


@router.post("/login")
async def login_submit(
    request: Request,
    session: Session = Depends(get_session),
):
    """Handle login form submission. Set JWT in httpOnly cookie."""
    settings = get_settings()
    form = await request.form()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))
    return_url = _safe_return_url(str(form.get("return_url", "/")).strip())

    # Validate credentials
    user = session.exec(select(User).where(User.username == username)).first()

    if not user or not verify_password(password, user.password_hash):
        csrf_token = generate_csrf_token()
        response = templates.TemplateResponse(
            request,
            "login.html",
            context={
                "csrf_token": csrf_token,
                "return_url": return_url,
                "error_message": "Invalid username or password",
            },
            status_code=401,
        )
        response.set_cookie("csrf_token", csrf_token, httponly=False, samesite="lax")
        return response

    if not user.is_active:
        csrf_token = generate_csrf_token()
        response = templates.TemplateResponse(
            request,
            "login.html",
            context={
                "csrf_token": csrf_token,
                "return_url": return_url,
                "error_message": "Account is disabled",
            },
            status_code=403,
        )
        response.set_cookie("csrf_token", csrf_token, httponly=False, samesite="lax")
        return response

    # Generate JWT
    access_token = create_access_token(user.id, user.username, user.role)

    # Update last login
    user.last_login_at = utc_now()
    session.add(user)
    session.commit()

    # Redirect to return_url with JWT in cookie
    redirect = RedirectResponse(url=return_url, status_code=302)
    redirect.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        max_age=settings.jwt_access_expiry_minutes * 60,
    )
    return redirect


@router.post("/logout")
async def logout():
    """Clear access token cookie and redirect to login."""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response


# --- OIDC Authentication routes ---


@router.get("/auth/oidc/login")
async def oidc_login(
    request: Request,
    session: Session = Depends(get_session),
    return_url: Optional[str] = Query(None),
):
    """Initiate OIDC Authorization Code Flow — redirect to provider."""
    config = get_oidc_config(session)
    if not config or not config.enabled:
        return RedirectResponse(url="/login", status_code=302)

    # Build the callback URL from the current request
    redirect_uri = str(request.base_url).rstrip("/") + "/auth/oidc/callback"

    try:
        authorize_url = await build_authorize_url(
            config, redirect_uri, return_url or "/"
        )
        return RedirectResponse(url=authorize_url, status_code=302)
    except Exception as e:
        logger.error("OIDC login initiation failed", extra={"error": str(e)})
        return RedirectResponse(url="/login?error=oidc_unavailable", status_code=302)


@router.get("/auth/oidc/callback")
async def oidc_callback(
    request: Request,
    session: Session = Depends(get_session),
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """Handle OIDC provider callback — exchange code, create/link user, set session."""
    settings = get_settings()
    # Handle provider error
    if error:
        logger.warning("OIDC provider returned error", extra={"error": error})
        return RedirectResponse(url="/login?error=oidc_denied", status_code=302)

    # Validate required params
    if not code or not state:
        return RedirectResponse(url="/login?error=oidc_invalid", status_code=302)

    # Validate state (CSRF protection)
    state_data = validate_state(state)
    if not state_data:
        return RedirectResponse(url="/login?error=oidc_expired", status_code=302)

    config = get_oidc_config(session)
    if not config or not config.enabled:
        return RedirectResponse(url="/login", status_code=302)

    redirect_uri = str(request.base_url).rstrip("/") + "/auth/oidc/callback"

    try:
        # Exchange code for tokens
        token_response = await exchange_code_for_tokens(config, code, redirect_uri)
        id_token = token_response.get("id_token")
        if not id_token:
            raise ValueError("No id_token in token response")

        # Decode and validate ID token (JWKS signature verification)
        claims = await decode_id_token(id_token, state_data["nonce"], config)

        # Get or create local user
        user = get_or_create_oidc_user(session, claims, config)
        session.commit()

        # Issue local JWT session
        access_token = create_access_token(user.id, user.username, user.role)
        return_url = _safe_return_url(state_data.get("return_url", "/"))

        redirect = RedirectResponse(url=return_url, status_code=302)
        redirect.set_cookie(
            "access_token",
            access_token,
            httponly=True,
            secure=not settings.debug,
            samesite="lax",
            max_age=settings.jwt_access_expiry_minutes * 60,
        )
        return redirect

    except Exception as e:
        logger.error("OIDC callback failed", extra={"error": str(e)})
        return RedirectResponse(url="/login?error=oidc_failed", status_code=302)


@router.post("/register")
async def register_submit(
    request: Request,
    session: Session = Depends(get_session),
):
    """Handle registration form submission."""
    settings = get_settings()
    if not settings.registration_enabled:
        return templates.TemplateResponse(
            request,
            "register.html",
            context={"registration_disabled": True},
            status_code=403,
        )

    form_data = await request.form()
    username = str(form_data.get("username", "")).strip()
    email = str(form_data.get("email", "")).strip()
    password = str(form_data.get("password", ""))

    # Validate via Pydantic schema
    try:
        user_data = UserCreate(username=username, email=email, password=password)
    except Exception as e:
        csrf_token = generate_csrf_token()
        response = templates.TemplateResponse(
            request,
            "register.html",
            context={
                "csrf_token": csrf_token,
                "error_message": str(e).split("\n")[0]
                if str(e)
                else "Validation error",
                "form_username": username,
                "form_email": email,
            },
            status_code=422,
        )
        response.set_cookie("csrf_token", csrf_token, httponly=False, samesite="lax")
        return response

    # Delegate to shared registration service (AC-008)
    try:
        register_user(
            session,
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
        )
    except RegistrationError as exc:
        csrf_token = generate_csrf_token()
        response = templates.TemplateResponse(
            request,
            "register.html",
            context={
                "csrf_token": csrf_token,
                "error_message": str(exc),
                "form_username": username,
                "form_email": email,
            },
            status_code=exc.status_code,
        )
        response.set_cookie("csrf_token", csrf_token, httponly=False, samesite="lax")
        return response

    # Redirect to login with success message
    return RedirectResponse(url="/login?success=registered", status_code=302)
