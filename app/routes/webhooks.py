import json
import logging
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from app.database import get_session
from app.api.deps import OptionalUserDep
from app.templating import templates, _form_str, DISCORD_URL_PATTERN
from app.models.webhook import WebhookEndpoint
from app.models.webhook_options import WebhookOptions
from app.services.auth import role_at_least, ROLE_OPERATOR
from app.services.webhook_test import (
    build_test_headers,
    build_test_webhook_payload,
    get_webhook_options,
    send_test_webhook,
)
from app.utils import utc_now

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/htmx/webhooks")
async def htmx_webhooks_list(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX partial: webhook list table."""
    webhooks_list = session.exec(
        select(WebhookEndpoint).order_by(WebhookEndpoint.name)
    ).all()

    # Batch load options to avoid N+1
    webhook_ids = [wh.id for wh in webhooks_list]
    options_map: dict = {}
    if webhook_ids:
        all_opts = session.exec(
            select(WebhookOptions).where(
                WebhookOptions.webhook_endpoint_id.in_(webhook_ids)  # type: ignore[attr-defined]
            )
        ).all()
        options_map = {opt.webhook_endpoint_id: opt.options for opt in all_opts}

    return templates.TemplateResponse(
        request,
        "partials/webhooks_list.html",
        context={
            "webhooks": webhooks_list,
            "options_map": options_map,
        },
    )


@router.get("/htmx/webhooks/add")
async def htmx_webhook_add_form(request: Request):
    """HTMX partial: empty webhook add form."""
    return templates.TemplateResponse(
        request,
        "partials/webhook_form.html",
        context={"webhook": None, "options": None, "errors": {}},
    )


@router.post("/htmx/webhooks")
async def htmx_webhook_create(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: create a new webhook endpoint. Requires Operator+ role."""
    if not user or not role_at_least(user.role, ROLE_OPERATOR):
        raise HTTPException(status_code=403, detail="Requires operator role")
    form = await request.form()
    errors: dict[str, str] = {}

    name = _form_str(form, "name").strip()
    url = _form_str(form, "url").strip()
    webhook_type = _form_str(form, "webhook_type", "generic")
    source_filters_raw = _form_str(form, "source_filters").strip()
    headers_raw = _form_str(form, "headers").strip()
    enabled = _form_str(form, "enabled") == "on"

    # Validation
    if not name:
        errors["name"] = "Name is required."
    if not url:
        errors["url"] = "URL is required."
    elif webhook_type == "discord" and not DISCORD_URL_PATTERN.match(url):
        errors["url"] = (
            "Discord webhooks require a URL matching "
            "https://discord.com/api/webhooks/... or "
            "https://discordapp.com/api/webhooks/..."
        )

    headers = None
    if headers_raw:
        try:
            headers = json.loads(headers_raw)
        except json.JSONDecodeError:
            errors["headers"] = "Headers must be valid JSON."

    if errors:
        return templates.TemplateResponse(
            request,
            "partials/webhook_form.html",
            context={
                "webhook": None,
                "options": None,
                "errors": errors,
                "form": form,
            },
        )

    source_filters = (
        [s.strip() for s in source_filters_raw.split(",") if s.strip()]
        if source_filters_raw
        else None
    )

    webhook = WebhookEndpoint(
        name=name,
        url=url,
        headers=headers,
        webhook_type=webhook_type,
        source_filters=source_filters,
        enabled=enabled,
    )
    session.add(webhook)
    session.flush()  # Assigns webhook.id without committing

    # Create options for Discord webhooks
    if webhook_type == "discord":
        color_raw = _form_str(form, "discord_color", "#FF0045").strip()
        try:
            color_int = int(color_raw.lstrip("#"), 16)
        except ValueError:
            color_int = 16711749
        opts: dict[str, object] = {
            "color": color_int,
            "username": _form_str(form, "discord_username", "Rsync Viewer").strip()
            or "Rsync Viewer",
        }
        avatar_url_val = _form_str(form, "discord_avatar_url").strip()
        if avatar_url_val:
            opts["avatar_url"] = avatar_url_val
        footer = _form_str(form, "discord_footer").strip()
        if footer:
            opts["footer"] = footer

        wh_opts = WebhookOptions(webhook_endpoint_id=webhook.id, options=opts)
        session.add(wh_opts)

    session.commit()

    logger.info("Webhook created via UI", extra={"webhook_name": name})

    # Return updated list with closeModal trigger
    response = await htmx_webhooks_list(request, session)
    response.headers["HX-Trigger"] = "closeModal"
    return response


@router.get("/htmx/webhooks/{webhook_id}/edit")
async def htmx_webhook_edit_form(
    request: Request, webhook_id: UUID, session: Session = Depends(get_session)
):
    """HTMX partial: pre-filled webhook edit form."""
    webhook = session.get(WebhookEndpoint, webhook_id)
    if not webhook:
        return HTMLResponse("<p>Webhook not found.</p>", status_code=404)

    opts_row = session.exec(
        select(WebhookOptions).where(WebhookOptions.webhook_endpoint_id == webhook_id)
    ).first()
    options = opts_row.options if opts_row else None

    return templates.TemplateResponse(
        request,
        "partials/webhook_form.html",
        context={"webhook": webhook, "options": options, "errors": {}},
    )


@router.put("/htmx/webhooks/{webhook_id}")
async def htmx_webhook_update(
    request: Request,
    webhook_id: UUID,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: update an existing webhook endpoint. Requires Operator+ role."""
    if not user or not role_at_least(user.role, ROLE_OPERATOR):
        raise HTTPException(status_code=403, detail="Requires operator role")
    webhook = session.get(WebhookEndpoint, webhook_id)
    if not webhook:
        return HTMLResponse("<p>Webhook not found.</p>", status_code=404)

    form = await request.form()
    errors: dict[str, str] = {}

    name = _form_str(form, "name").strip()
    url = _form_str(form, "url").strip()
    webhook_type = _form_str(form, "webhook_type", "generic")
    source_filters_raw = _form_str(form, "source_filters").strip()
    headers_raw = _form_str(form, "headers").strip()
    enabled = _form_str(form, "enabled") == "on"

    if not name:
        errors["name"] = "Name is required."
    if not url:
        errors["url"] = "URL is required."
    elif webhook_type == "discord" and not DISCORD_URL_PATTERN.match(url):
        errors["url"] = (
            "Discord webhooks require a URL matching "
            "https://discord.com/api/webhooks/... or "
            "https://discordapp.com/api/webhooks/..."
        )

    headers = None
    if headers_raw:
        try:
            headers = json.loads(headers_raw)
        except json.JSONDecodeError:
            errors["headers"] = "Headers must be valid JSON."

    if errors:
        # Reload options for re-rendering the form
        opts_row = session.exec(
            select(WebhookOptions).where(
                WebhookOptions.webhook_endpoint_id == webhook_id
            )
        ).first()
        return templates.TemplateResponse(
            request,
            "partials/webhook_form.html",
            context={
                "webhook": webhook,
                "options": opts_row.options if opts_row else None,
                "errors": errors,
                "form": form,
            },
        )

    source_filters = (
        [s.strip() for s in source_filters_raw.split(",") if s.strip()]
        if source_filters_raw
        else None
    )

    webhook.name = name
    webhook.url = url
    webhook.headers = headers
    webhook.webhook_type = webhook_type
    webhook.source_filters = source_filters
    webhook.enabled = enabled
    webhook.updated_at = utc_now()
    session.add(webhook)

    # Update or create Discord options
    if webhook_type == "discord":
        color_raw = _form_str(form, "discord_color", "#FF0045").strip()
        try:
            color_int = int(color_raw.lstrip("#"), 16)
        except ValueError:
            color_int = 16711749
        opts: dict[str, object] = {
            "color": color_int,
            "username": _form_str(form, "discord_username", "Rsync Viewer").strip()
            or "Rsync Viewer",
        }
        avatar_url_val = _form_str(form, "discord_avatar_url").strip()
        if avatar_url_val:
            opts["avatar_url"] = avatar_url_val
        footer = _form_str(form, "discord_footer").strip()
        if footer:
            opts["footer"] = footer

        existing_opts = session.exec(
            select(WebhookOptions).where(
                WebhookOptions.webhook_endpoint_id == webhook_id
            )
        ).first()
        if existing_opts:
            existing_opts.options = opts
            existing_opts.updated_at = utc_now()
            session.add(existing_opts)
        else:
            new_opts = WebhookOptions(webhook_endpoint_id=webhook_id, options=opts)
            session.add(new_opts)
    else:
        # Remove options if switching away from Discord
        existing_opts = session.exec(
            select(WebhookOptions).where(
                WebhookOptions.webhook_endpoint_id == webhook_id
            )
        ).first()
        if existing_opts:
            session.delete(existing_opts)

    session.commit()

    logger.info("Webhook updated via UI", extra={"webhook_id": str(webhook_id)})

    response = await htmx_webhooks_list(request, session)
    response.headers["HX-Trigger"] = "closeModal"
    return response


@router.delete("/htmx/webhooks/{webhook_id}")
async def htmx_webhook_delete(
    request: Request,
    webhook_id: UUID,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: delete a webhook endpoint. Requires Operator+ role."""
    if not user or not role_at_least(user.role, ROLE_OPERATOR):
        raise HTTPException(status_code=403, detail="Requires operator role")
    webhook = session.get(WebhookEndpoint, webhook_id)
    if not webhook:
        return HTMLResponse("<p>Webhook not found.</p>", status_code=404)

    session.delete(webhook)
    session.commit()

    logger.info("Webhook deleted via UI", extra={"webhook_id": str(webhook_id)})

    return await htmx_webhooks_list(request, session)


@router.post("/htmx/webhooks/{webhook_id}/toggle")
async def htmx_webhook_toggle(
    request: Request,
    webhook_id: UUID,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: toggle webhook enabled/disabled. Requires Operator+ role."""
    if not user or not role_at_least(user.role, ROLE_OPERATOR):
        raise HTTPException(status_code=403, detail="Requires operator role")
    webhook = session.get(WebhookEndpoint, webhook_id)
    if not webhook:
        return HTMLResponse("<p>Webhook not found.</p>", status_code=404)

    webhook.enabled = not webhook.enabled
    webhook.updated_at = utc_now()
    session.add(webhook)
    session.commit()

    return await htmx_webhooks_list(request, session)


@router.post("/htmx/webhooks/{webhook_id}/test")
async def htmx_webhook_test(
    request: Request,
    webhook_id: UUID,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: send a test notification. Requires Operator+ role."""
    if not user or not role_at_least(user.role, ROLE_OPERATOR):
        raise HTTPException(status_code=403, detail="Requires operator role")
    webhook = session.get(WebhookEndpoint, webhook_id)
    if not webhook:
        return HTMLResponse("<p>Webhook not found.</p>", status_code=404)

    # Build test payload via shared service (AC-009)
    opts = get_webhook_options(session, webhook_id)
    payload = build_test_webhook_payload(webhook, opts)
    req_headers = build_test_headers(webhook)

    try:
        response = await send_test_webhook(webhook, payload, req_headers)
        if 200 <= response.status_code < 300:
            return HTMLResponse(
                '<span class="test-result test-success">Test sent successfully!</span>'
            )
        return HTMLResponse(
            f'<span class="test-result test-failure">Failed: HTTP {response.status_code}</span>'
        )
    except httpx.RequestError as e:
        return HTMLResponse(
            f'<span class="test-result test-failure">Failed: {e}</span>'
        )
