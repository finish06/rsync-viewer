import logging
import re
import secrets as secrets_module

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from app.config import get_settings
from app.database import get_session
from app.api.deps import OptionalUserDep, hash_api_key as _hash_api_key
from app.templating import templates
from app.models.smtp_config import SmtpConfig
from app.models.sync_log import ApiKey as ApiKeyModel
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
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX partial: Synthetic monitoring status and configuration."""
    if not user or not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Admin only")

    from app.services.synthetic_check import get_db_config, get_state

    state = get_state()
    db_config = get_db_config(session)
    return templates.TemplateResponse(
        request,
        "partials/synthetic_settings.html",
        context={"synthetic": state, "db_config": db_config},
    )


@router.post("/htmx/synthetic-settings")
async def htmx_synthetic_settings_save(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: Toggle synthetic monitoring enable/disable and interval.

    Writes to DB and starts/stops the background task at runtime (AC-013, AC-014).
    """
    if not user or not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Admin only")

    from app.database import engine as app_engine
    from app.services.synthetic_check import (
        get_db_config,
        get_state,
        save_db_config,
        start_synthetic_monitoring,
        stop_synthetic_monitoring,
    )

    form = await request.form()
    enabled = str(form.get("enabled", "")) == "on"
    interval_str = str(form.get("interval", "300")).strip()

    try:
        interval = int(interval_str)
        if interval < 30:
            interval = 30
    except ValueError:
        interval = 300

    save_db_config(session, enabled=enabled, interval_seconds=interval)

    if enabled:
        await start_synthetic_monitoring(app_engine)
    else:
        await stop_synthetic_monitoring()

    logger.info(
        "Synthetic monitoring settings updated",
        extra={
            "user_id": str(user.id),
            "enabled": enabled,
            "interval": interval,
        },
    )

    state = get_state()
    db_config = get_db_config(session)
    return templates.TemplateResponse(
        request,
        "partials/synthetic_settings.html",
        context={
            "synthetic": state,
            "db_config": db_config,
            "success_message": "Synthetic monitoring settings updated. Changes take effect immediately.",
        },
    )


@router.get("/htmx/synthetic-history")
async def htmx_synthetic_history(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX partial: Synthetic check history timeline and stats (AC-017)."""
    if not user or not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Admin only")

    from app.services.synthetic_check import get_check_history, get_uptime_percentage

    history = get_check_history(session, limit=50)
    uptime = get_uptime_percentage(session, hours=24)
    recent = history[:10]

    return templates.TemplateResponse(
        request,
        "partials/synthetic_history.html",
        context={
            "history": history,
            "recent": recent,
            "uptime": uptime,
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


# --- Monitoring Setup Wizard HTMX routes ---


def _sanitize_source_name(name: str) -> str:
    """Sanitize source name to kebab-case for use in container/key names."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    return name.strip("-")


def _parse_rsync_source(rsync_source: str) -> tuple[str, str, str] | None:
    """Parse user@host:/path into (user, host, path). Returns None if invalid."""
    match = re.match(r"^([^@]+)@([^:]+):(.+)$", rsync_source.strip())
    if not match:
        return None
    return match.group(1), match.group(2), match.group(3)


def _detect_hub_url(request: Request) -> str:
    """Detect the hub URL from the request, respecting reverse proxy headers."""
    proto = request.headers.get("X-Forwarded-Proto", request.url.scheme)
    host = request.headers.get(
        "X-Forwarded-Host", request.headers.get("host", "localhost:8000")
    )
    return f"{proto}://{host}"


def _unique_key_name(session: Session, user_id, base_name: str) -> str:
    """Return a unique API key name, appending -2, -3, etc. if needed."""
    name = base_name
    suffix = 1
    while True:
        existing = session.exec(
            select(ApiKeyModel).where(
                ApiKeyModel.user_id == user_id,
                ApiKeyModel.name == name,
                ApiKeyModel.is_active.is_(True),  # type: ignore[attr-defined]
            )
        ).first()
        if not existing:
            return name
        suffix += 1
        name = f"{base_name}-{suffix}"


def _generate_compose_snippet(
    *,
    source_name: str,
    remote_user: str,
    remote_host: str,
    remote_path: str,
    hub_url: str,
    api_key: str,
    cron_schedule: str,
    rsync_args: str,
    sync_mode: str,
    ssh_key_path: str,
) -> str:
    """Build a Docker Compose YAML snippet for an rsync-client container."""
    from datetime import date

    data_mount = "./data:/data:ro" if sync_mode == "push" else "./data:/data"

    return f"""\
# Rsync Client — {source_name}
# Generated by Rsync Log Viewer on {date.today().isoformat()}
# Add this to your docker-compose.yml

services:
  rsync-client-{source_name}:
    image: ghcr.io/finish06/rsync-client:latest
    container_name: rsync-{source_name}
    restart: unless-stopped
    environment:
      - REMOTE_HOST={remote_host}
      - REMOTE_USER={remote_user}
      - REMOTE_PATH={remote_path}
      - RSYNC_VIEWER_URL={hub_url}
      - RSYNC_VIEWER_API_KEY={api_key}
      - RSYNC_SOURCE_NAME={source_name}
      - CRON_SCHEDULE={cron_schedule}
      - RSYNC_ARGS={rsync_args}
      - SYNC_MODE={sync_mode}
    volumes:
      - {ssh_key_path}:/home/rsync/.ssh/id_rsa:ro
      - {data_mount}
"""


@router.get("/htmx/monitoring-setup")
async def htmx_monitoring_setup(
    request: Request,
    user: OptionalUserDep = None,
):
    """HTMX partial: Monitoring tab with rsync client wizard and synthetic settings."""
    if not user or not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Admin only")

    from app.services.synthetic_check import get_state

    state = get_state()
    return templates.TemplateResponse(
        request,
        "partials/monitoring_setup.html",
        context={"synthetic": state},
    )


@router.post("/htmx/monitoring-setup/generate")
async def htmx_monitoring_generate(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: Generate Docker Compose snippet and auto-provision API key."""
    if not user or not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Admin only")

    from app.services.synthetic_check import get_state

    form = await request.form()
    source_name_raw = str(form.get("source_name", "")).strip()
    rsync_source = str(form.get("rsync_source", "")).strip()
    cron_schedule = str(form.get("cron_schedule", "")).strip() or "0 */6 * * *"
    ssh_key_path = str(form.get("ssh_key_path", "")).strip() or "~/.ssh/id_rsa"
    rsync_args = str(form.get("rsync_args", "")).strip() or "-avz --stats"
    sync_mode = str(form.get("sync_mode", "")).strip() or "pull"

    # Validate required fields
    errors = {}
    if not source_name_raw:
        errors["source_name"] = "Source name is required."
    if not rsync_source:
        errors["rsync_source"] = "Rsync source is required."

    # Validate rsync source format
    parsed = None
    if rsync_source and not errors.get("rsync_source"):
        parsed = _parse_rsync_source(rsync_source)
        if not parsed:
            errors["rsync_source"] = "Invalid format. Expected: user@host:/path"

    if errors:
        state = get_state()
        return templates.TemplateResponse(
            request,
            "partials/monitoring_setup.html",
            context={
                "synthetic": state,
                "errors": errors,
                "form_data": {
                    "source_name": source_name_raw,
                    "rsync_source": rsync_source,
                    "cron_schedule": cron_schedule,
                    "ssh_key_path": ssh_key_path,
                    "rsync_args": rsync_args,
                    "sync_mode": sync_mode,
                },
            },
        )

    source_name = _sanitize_source_name(source_name_raw)
    remote_user, remote_host, remote_path = parsed  # type: ignore[misc]

    # Auto-provision API key
    base_key_name = f"rsync-client-{source_name}"
    key_name = _unique_key_name(session, user.id, base_key_name)
    raw_key = "rsv_" + secrets_module.token_urlsafe(32)
    key_hash = _hash_api_key(raw_key)

    api_key = ApiKeyModel(
        key_hash=key_hash,
        key_prefix=raw_key[:8],
        name=key_name,
        is_active=True,
        user_id=user.id,
        created_at=utc_now(),
    )
    session.add(api_key)
    session.commit()

    hub_url = _detect_hub_url(request)

    snippet = _generate_compose_snippet(
        source_name=source_name,
        remote_user=remote_user,
        remote_host=remote_host,
        remote_path=remote_path,
        hub_url=hub_url,
        api_key=raw_key,
        cron_schedule=cron_schedule,
        rsync_args=rsync_args,
        sync_mode=sync_mode,
        ssh_key_path=ssh_key_path,
    )

    state = get_state()
    return templates.TemplateResponse(
        request,
        "partials/monitoring_compose_result.html",
        context={
            "synthetic": state,
            "snippet": snippet,
            "key_name": key_name,
            "source_name": source_name,
        },
    )
