"""Settings API for the SPA (specs/settings-ui.md AC-001–AC-008). Admin only."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import AdminDep, SessionDep, require_role
from app.config import get_settings
from app.database import engine
from app.models.oidc_config import OidcConfig
from app.models.smtp_config import SmtpConfig
from app.schemas.settings import (
    MonitoringSetupRequest,
    MonitoringSetupResponse,
    OidcDiscoveryRequest,
    OidcDiscoveryResponse,
    OidcSettingsRead,
    OidcSettingsWrite,
    SmtpSettingsRead,
    SmtpSettingsWrite,
    SmtpTestRequest,
    SmtpTestResponse,
    SyntheticSettingsRead,
    SyntheticSettingsWrite,
)
from app.services.auth import ROLE_ADMIN
from app.services.email import encrypt_password, get_smtp_config, send_test_email_async
from app.services.monitoring_setup import detect_hub_url, provision_client
from app.services.oidc import encrypt_client_secret, fetch_discovery, get_oidc_config
from app.services.synthetic_check import (
    MINIMUM_INTERVAL_SECONDS,
    get_db_config,
    get_state,
    save_db_config,
    start_synthetic_monitoring,
    stop_synthetic_monitoring,
)
from app.utils import utc_now

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)

DISCOVERY_KEYS = (
    "authorization_endpoint",
    "token_endpoint",
    "userinfo_endpoint",
    "jwks_uri",
)
ENCRYPTION_KEY_REQUIRED = (
    "ENCRYPTION_KEY is not set. Configure it in your .env file before saving secrets."
)


def _encryption_key_configured() -> bool:
    return bool(get_settings().effective_encryption_key)


def _require_encryption_key() -> None:
    if not _encryption_key_configured():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=ENCRYPTION_KEY_REQUIRED
        )


# ---------------------------------------------------------------------------
# SMTP
# ---------------------------------------------------------------------------


def _smtp_read(config: SmtpConfig | None) -> SmtpSettingsRead:
    if config is None:
        return SmtpSettingsRead(
            configured=False, encryption_key_configured=_encryption_key_configured()
        )
    return SmtpSettingsRead(
        configured=True,
        host=config.host,
        port=config.port,
        username=config.username,
        encryption=config.encryption,  # type: ignore[arg-type]
        from_address=config.from_address,
        from_name=config.from_name,
        enabled=config.enabled,
        has_password=bool(config.encrypted_password),
        encryption_key_configured=_encryption_key_configured(),
        updated_at=config.updated_at,
    )


@router.get("/smtp", response_model=SmtpSettingsRead)
async def read_smtp(session: SessionDep) -> SmtpSettingsRead:
    """Current SMTP configuration without the password."""
    return _smtp_read(get_smtp_config(session))


@router.put("/smtp", response_model=SmtpSettingsRead)
async def write_smtp(
    body: SmtpSettingsWrite, session: SessionDep, admin: AdminDep
) -> SmtpSettingsRead:
    """Create or update SMTP configuration; an empty password keeps the stored one."""
    _require_encryption_key()
    config = get_smtp_config(session)
    if config is None:
        config = SmtpConfig(
            host=body.host,
            port=body.port,
            username=body.username or None,
            encryption=body.encryption,
            from_address=body.from_address,
            from_name=body.from_name or "Rsync Viewer",
            enabled=body.enabled,
            configured_by_id=admin.id,
        )
    else:
        config.host = body.host
        config.port = body.port
        config.username = body.username or None
        config.encryption = body.encryption
        config.from_address = body.from_address
        config.from_name = body.from_name or "Rsync Viewer"
        config.enabled = body.enabled
        config.configured_by_id = admin.id
        config.updated_at = utc_now()
    if body.password:
        config.encrypted_password = encrypt_password(body.password)
    session.add(config)
    session.commit()
    session.refresh(config)
    logger.info("SMTP configuration saved", extra={"user_id": str(admin.id)})
    return _smtp_read(config)


@router.post("/smtp/test", response_model=SmtpTestResponse)
async def test_smtp(body: SmtpTestRequest, session: SessionDep) -> SmtpTestResponse:
    """Send a test email with the stored configuration."""
    try:
        await send_test_email_async(session, to_address=body.to_address)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:  # network / SMTP errors: keep internals out of the UI
        logger.error("SMTP test email failed", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Test email failed: could not connect to the SMTP server. "
            "Check the application logs for details.",
        )
    return SmtpTestResponse(sent=True, to_address=body.to_address)


# ---------------------------------------------------------------------------
# OIDC
# ---------------------------------------------------------------------------


def _callback_url(request: Request) -> str:
    return str(request.base_url).rstrip("/") + "/auth/oidc/callback"


def _oidc_read(config: OidcConfig | None, request: Request) -> OidcSettingsRead:
    if config is None:
        return OidcSettingsRead(
            configured=False,
            callback_url=_callback_url(request),
            encryption_key_configured=_encryption_key_configured(),
        )
    return OidcSettingsRead(
        configured=True,
        issuer_url=config.issuer_url,
        client_id=config.client_id,
        provider_name=config.provider_name,
        scopes=config.scopes,
        enabled=config.enabled,
        hide_local_login=config.hide_local_login,
        has_client_secret=bool(config.encrypted_client_secret),
        callback_url=_callback_url(request),
        encryption_key_configured=_encryption_key_configured(),
        updated_at=config.updated_at,
    )


@router.get("/oidc", response_model=OidcSettingsRead)
async def read_oidc(request: Request, session: SessionDep) -> OidcSettingsRead:
    """Current OIDC configuration without the client secret."""
    return _oidc_read(get_oidc_config(session), request)


@router.put("/oidc", response_model=OidcSettingsRead)
async def write_oidc(
    body: OidcSettingsWrite, request: Request, session: SessionDep, admin: AdminDep
) -> OidcSettingsRead:
    """Create or update OIDC configuration; the secret is required only initially."""
    _require_encryption_key()
    config = get_oidc_config(session)
    scopes = body.scopes.strip() or "openid email profile"
    if config is None:
        if not body.client_secret:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Client secret is required for the initial configuration.",
            )
        config = OidcConfig(
            issuer_url=body.issuer_url,
            client_id=body.client_id,
            encrypted_client_secret=encrypt_client_secret(body.client_secret),
            provider_name=body.provider_name,
            scopes=scopes,
            enabled=body.enabled,
            hide_local_login=body.hide_local_login,
            configured_by_id=admin.id,
        )
    else:
        config.issuer_url = body.issuer_url
        config.client_id = body.client_id
        config.provider_name = body.provider_name
        config.scopes = scopes
        config.enabled = body.enabled
        config.hide_local_login = body.hide_local_login
        config.configured_by_id = admin.id
        config.updated_at = utc_now()
        if body.client_secret:
            config.encrypted_client_secret = encrypt_client_secret(body.client_secret)
    session.add(config)
    session.commit()
    session.refresh(config)
    logger.info(
        "OIDC configuration saved",
        extra={"user_id": str(admin.id), "issuer_url": body.issuer_url},
    )
    return _oidc_read(config, request)


@router.post("/oidc/test-discovery", response_model=OidcDiscoveryResponse)
async def test_oidc_discovery(body: OidcDiscoveryRequest) -> OidcDiscoveryResponse:
    """Fetch the issuer's discovery document and return the endpoints we rely on."""
    try:
        discovery = await fetch_discovery(body.issuer_url)
    except Exception as exc:
        logger.warning(
            "OIDC discovery failed",
            extra={"issuer_url": body.issuer_url, "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Discovery failed: {exc}"
        )
    endpoints = {k: str(discovery[k]) for k in DISCOVERY_KEYS if k in discovery}
    if not endpoints:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discovery response is missing the required endpoints.",
        )
    return OidcDiscoveryResponse(issuer_url=body.issuer_url, endpoints=endpoints)


# ---------------------------------------------------------------------------
# Synthetic monitoring
# ---------------------------------------------------------------------------


def _synthetic_read(session: SessionDep) -> SyntheticSettingsRead:
    config = get_db_config(session)
    state = get_state()
    return SyntheticSettingsRead(
        enabled=config.enabled,
        interval_seconds=config.interval_seconds,
        last_status=state.last_status,
        last_check_at=state.last_check_at,
        last_latency_ms=state.last_latency_ms,
        last_error=state.last_error,
    )


@router.get("/synthetic", response_model=SyntheticSettingsRead)
async def read_synthetic(session: SessionDep) -> SyntheticSettingsRead:
    """Synthetic-check configuration plus the in-process state."""
    return _synthetic_read(session)


@router.put("/synthetic", response_model=SyntheticSettingsRead)
async def write_synthetic(
    body: SyntheticSettingsWrite, session: SessionDep, admin: AdminDep
) -> SyntheticSettingsRead:
    """Persist and apply immediately (starts or stops the background task)."""
    interval = max(body.interval_seconds, MINIMUM_INTERVAL_SECONDS)
    save_db_config(session, enabled=body.enabled, interval_seconds=interval)
    if body.enabled:
        await start_synthetic_monitoring(engine)
    else:
        await stop_synthetic_monitoring()
    logger.info(
        "Synthetic monitoring settings updated",
        extra={"user_id": str(admin.id), "enabled": body.enabled, "interval": interval},
    )
    return _synthetic_read(session)


# ---------------------------------------------------------------------------
# Monitoring setup wizard
# ---------------------------------------------------------------------------


@router.post(
    "/monitoring-setup",
    response_model=MonitoringSetupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def monitoring_setup(
    body: MonitoringSetupRequest, request: Request, session: SessionDep, admin: AdminDep
) -> MonitoringSetupResponse:
    """Provision an API key and return a docker-compose snippet for an rsync client."""
    try:
        result = provision_client(
            session,
            user_id=admin.id,
            hub_url=detect_hub_url(request),
            source_name=body.source_name,
            rsync_source=body.rsync_source,
            cron_schedule=body.cron_schedule.strip() or "0 */6 * * *",
            ssh_key_path=body.ssh_key_path.strip() or "~/.ssh/id_rsa",
            rsync_args=body.rsync_args.strip() or "-avz --stats",
            sync_mode=body.sync_mode,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    logger.info(
        "Monitoring client provisioned",
        extra={"user_id": str(admin.id), "source_name": result.source_name},
    )
    return MonitoringSetupResponse(
        source_name=result.source_name,
        key_name=result.key_name,
        api_key=result.api_key,
        snippet=result.snippet,
    )
