import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from app.config import get_settings
from app.database import get_session
from app.api.deps import OptionalUserDep
from app.templating import templates
from app.models.smtp_config import SmtpConfig
from app.services.auth import role_at_least, ROLE_ADMIN
from app.services.email import encrypt_password, get_smtp_config, send_test_email_async
from app.services.oidc import (
    encrypt_client_secret,
    fetch_discovery,
    get_oidc_config,
)
from app.models.oidc_config import OidcConfig
from app.utils import utc_now

logger = logging.getLogger(__name__)

router = APIRouter()


# --- SMTP Settings HTMX routes ---


@router.get("/htmx/smtp-settings")
async def htmx_smtp_settings(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX partial: SMTP configuration form."""
    if not user or not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Admin only")

    config = get_smtp_config(session)
    has_encryption_key = bool(get_settings().effective_encryption_key)

    return templates.TemplateResponse(
        request,
        "partials/smtp_settings.html",
        context={
            "smtp": config,
            "has_encryption_key": has_encryption_key,
        },
    )


@router.post("/htmx/smtp-settings")
async def htmx_smtp_settings_save(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: Save SMTP configuration."""
    if not user or not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Admin only")

    if not get_settings().effective_encryption_key:
        return HTMLResponse(
            '<div class="auth-error">ENCRYPTION_KEY is not set. '
            "Configure it in your .env file before saving SMTP settings.</div>",
            status_code=400,
        )

    form = await request.form()
    host = str(form.get("host", "")).strip()
    port_str = str(form.get("port", "")).strip()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))
    encryption = str(form.get("encryption", "starttls")).strip()
    from_address = str(form.get("from_address", "")).strip()
    from_name = str(form.get("from_name", "")).strip() or "Rsync Viewer"

    # Validate required fields
    if not host or not port_str or not from_address:
        return HTMLResponse(
            '<div class="auth-error">Host, port, and from address are required.</div>',
            status_code=422,
        )

    try:
        port = int(port_str)
        if not (1 <= port <= 65535):
            raise ValueError()
    except ValueError:
        return HTMLResponse(
            '<div class="auth-error">Port must be a number between 1 and 65535.</div>',
            status_code=422,
        )

    if encryption not in ("none", "starttls", "ssl_tls"):
        return HTMLResponse(
            '<div class="auth-error">Invalid encryption method.</div>',
            status_code=422,
        )

    config = get_smtp_config(session)
    if config is None:
        config = SmtpConfig(
            host=host,
            port=port,
            username=username or None,
            encryption=encryption,
            from_address=from_address,
            from_name=from_name,
            configured_by_id=user.id,
        )
    else:
        config.host = host
        config.port = port
        config.username = username or None
        config.encryption = encryption
        config.from_address = from_address
        config.from_name = from_name
        config.configured_by_id = user.id
        config.updated_at = utc_now()

    # Only update password if a new one was provided
    if password:
        config.encrypted_password = encrypt_password(password)

    session.add(config)
    session.commit()
    session.refresh(config)

    logger.info(
        "SMTP configuration saved",
        extra={"user_id": str(user.id), "host": host},
    )

    return templates.TemplateResponse(
        request,
        "partials/smtp_settings.html",
        context={
            "smtp": config,
            "has_encryption_key": True,
            "success_message": "SMTP configuration saved.",
        },
    )


@router.post("/htmx/smtp-settings/test")
async def htmx_smtp_test_email(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: Send a test email."""
    if not user or not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Admin only")

    form = await request.form()
    test_email = str(form.get("test_email", "")).strip()
    if not test_email:
        return HTMLResponse(
            '<div class="auth-error">Please enter a test email address.</div>',
            status_code=422,
        )

    try:
        await send_test_email_async(session, to_address=test_email)
        return HTMLResponse(
            f'<div class="settings-success">Test email sent successfully to {test_email}.</div>'
        )
    except ValueError as e:
        return HTMLResponse(
            f'<div class="auth-error">{e}</div>',
            status_code=400,
        )
    except Exception as e:
        error_msg = str(e)
        logger.error("SMTP test email failed", extra={"error": error_msg})
        # Show a generic message to avoid leaking server internals
        return HTMLResponse(
            '<div class="auth-error">Test email failed: could not connect to SMTP server. Check logs for details.</div>',
            status_code=500,
        )


# --- OIDC Settings HTMX routes ---


@router.get("/htmx/settings/auth")
async def htmx_oidc_settings(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX partial: OIDC configuration form."""
    if not user or not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Admin only")

    config = get_oidc_config(session)
    has_encryption_key = bool(get_settings().effective_encryption_key)
    callback_url = str(request.base_url).rstrip("/") + "/auth/oidc/callback"

    return templates.TemplateResponse(
        request,
        "partials/oidc_settings.html",
        context={
            "oidc": config,
            "has_encryption_key": has_encryption_key,
            "oidc_callback_url": callback_url,
        },
    )


@router.post("/htmx/settings/auth")
async def htmx_oidc_settings_save(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: Save OIDC configuration."""
    if not user or not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Admin only")

    if not get_settings().effective_encryption_key:
        return HTMLResponse(
            '<div class="auth-error">ENCRYPTION_KEY is not set. '
            "Configure it in your .env file before saving OIDC settings.</div>",
            status_code=400,
        )

    form = await request.form()
    issuer_url = str(form.get("issuer_url", "")).strip()
    client_id = str(form.get("client_id", "")).strip()
    client_secret = str(form.get("client_secret", ""))
    provider_name = str(form.get("provider_name", "")).strip()
    scopes = str(form.get("scopes", "openid email profile")).strip()
    enabled = str(form.get("enabled", "")) == "on"
    hide_local_login = str(form.get("hide_local_login", "")) == "on"

    if not issuer_url or not client_id or not provider_name:
        return HTMLResponse(
            '<div class="auth-error">Issuer URL, Client ID, and Provider Name are required.</div>',
            status_code=422,
        )

    if len(issuer_url) > 512:
        return HTMLResponse(
            '<div class="auth-error">Issuer URL must be 512 characters or fewer.</div>',
            status_code=422,
        )

    config = get_oidc_config(session)
    if config is None:
        if not client_secret:
            return HTMLResponse(
                '<div class="auth-error">Client Secret is required for initial configuration.</div>',
                status_code=422,
            )
        config = OidcConfig(
            issuer_url=issuer_url,
            client_id=client_id,
            encrypted_client_secret=encrypt_client_secret(client_secret),
            provider_name=provider_name,
            scopes=scopes or "openid email profile",
            enabled=enabled,
            hide_local_login=hide_local_login,
            configured_by_id=user.id,
        )
    else:
        config.issuer_url = issuer_url
        config.client_id = client_id
        config.provider_name = provider_name
        config.scopes = scopes or "openid email profile"
        config.enabled = enabled
        config.hide_local_login = hide_local_login
        config.configured_by_id = user.id
        config.updated_at = utc_now()

        # Only update secret if a new one was provided
        if client_secret:
            config.encrypted_client_secret = encrypt_client_secret(client_secret)

    session.add(config)
    session.commit()
    session.refresh(config)

    logger.info(
        "OIDC configuration saved",
        extra={"user_id": str(user.id), "issuer_url": issuer_url},
    )

    callback_url = str(request.base_url).rstrip("/") + "/auth/oidc/callback"

    return templates.TemplateResponse(
        request,
        "partials/oidc_settings.html",
        context={
            "oidc": config,
            "has_encryption_key": True,
            "success_message": "OIDC configuration saved.",
            "oidc_callback_url": callback_url,
        },
    )


# --- Synthetic Monitoring Settings HTMX routes ---


@router.get("/htmx/synthetic-settings")
async def htmx_synthetic_settings(
    request: Request,
    user: OptionalUserDep = None,
):
    """HTMX partial: Synthetic monitoring status and configuration."""
    if not user or not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Admin only")

    from app.services.synthetic_check import get_state

    state = get_state()
    return templates.TemplateResponse(
        request,
        "partials/synthetic_settings.html",
        context={"synthetic": state},
    )


@router.post("/htmx/synthetic-settings")
async def htmx_synthetic_settings_save(
    request: Request,
    user: OptionalUserDep = None,
):
    """HTMX: Toggle synthetic monitoring enable/disable and interval."""
    if not user or not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Admin only")

    from app.services.synthetic_check import get_state

    form = await request.form()
    enabled = str(form.get("enabled", "")) == "on"
    interval_str = str(form.get("interval", "300")).strip()

    try:
        interval = int(interval_str)
        if interval < 30:
            interval = 30
    except ValueError:
        interval = 300

    state = get_state()
    state.enabled = enabled
    state.interval_seconds = interval

    logger.info(
        "Synthetic monitoring settings updated",
        extra={
            "user_id": str(user.id),
            "enabled": enabled,
            "interval": interval,
        },
    )

    return templates.TemplateResponse(
        request,
        "partials/synthetic_settings.html",
        context={
            "synthetic": state,
            "success_message": "Synthetic monitoring settings saved.",
        },
    )


@router.post("/htmx/settings/auth/test-discovery")
async def htmx_oidc_test_discovery(
    request: Request,
    user: OptionalUserDep = None,
):
    """HTMX: Test OIDC discovery against provided issuer URL."""
    if not user or not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Admin only")

    form = await request.form()
    issuer_url = str(form.get("issuer_url", "")).strip()
    if not issuer_url:
        return HTMLResponse(
            '<div class="auth-error">Issuer URL is required.</div>',
            status_code=422,
        )

    try:
        discovery = await fetch_discovery(issuer_url)
        endpoints = []
        for key in (
            "authorization_endpoint",
            "token_endpoint",
            "userinfo_endpoint",
            "jwks_uri",
        ):
            if key in discovery:
                endpoints.append(f"<li><strong>{key}:</strong> {discovery[key]}</li>")

        if not endpoints:
            return HTMLResponse(
                '<div class="auth-error">Discovery response missing required endpoints.</div>'
            )

        return HTMLResponse(
            '<div class="settings-success">'
            "<strong>Discovery successful:</strong>"
            f'<ul style="margin: 0.5rem 0 0 1rem;">{"".join(endpoints)}</ul>'
            "</div>"
        )
    except Exception as e:
        error_msg = str(e)
        logger.warning(
            "OIDC discovery failed",
            extra={"issuer_url": issuer_url, "error": error_msg},
        )
        return HTMLResponse(
            f'<div class="auth-error">Discovery failed: {error_msg}</div>'
        )
