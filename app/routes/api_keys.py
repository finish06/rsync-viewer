import logging
import secrets as secrets_module
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from app.database import get_session
from app.api.deps import OptionalUserDep, hash_api_key as _hash_api_key
from app.templating import templates
from app.models.sync_log import ApiKey as ApiKeyModel
from app.services.auth import role_at_least
from app.utils import utc_now

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/htmx/api-keys")
async def htmx_api_keys_list(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX partial: API keys list table."""
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    statement = (
        select(ApiKeyModel)
        .where(
            ApiKeyModel.is_active.is_(True),  # type: ignore[attr-defined]
            ApiKeyModel.user_id == user.id,
        )
        .order_by(ApiKeyModel.created_at.desc())  # type: ignore[attr-defined]
    )
    api_keys = session.exec(statement).all()

    return templates.TemplateResponse(
        request,
        "partials/api_keys_list.html",
        context={"api_keys": api_keys, "user": user},
    )


@router.get("/htmx/api-keys/add")
async def htmx_api_key_add_form(
    request: Request,
    user: OptionalUserDep = None,
):
    """HTMX partial: API key creation form modal."""
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    return templates.TemplateResponse(
        request,
        "partials/api_key_form.html",
        context={"user_role": user.role, "user": user},
    )


@router.post("/htmx/api-keys")
async def htmx_api_key_create(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: create a new API key and show the raw key once."""
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    form = await request.form()
    name = str(form.get("name", "")).strip()
    role_override = str(form.get("role_override", "")).strip() or None

    if not name:
        return templates.TemplateResponse(
            request,
            "partials/api_key_form.html",
            context={
                "user_role": user.role,
                "user": user,
                "error": "Name is required.",
            },
        )

    # Validate role override
    effective_role = user.role
    if role_override:
        if not role_at_least(user.role, role_override):
            return templates.TemplateResponse(
                request,
                "partials/api_key_form.html",
                context={
                    "user_role": user.role,
                    "user": user,
                    "error": f"Cannot create key with role '{role_override}'.",
                },
            )
        effective_role = role_override

    raw_key = "rsv_" + secrets_module.token_urlsafe(32)
    key_hash = _hash_api_key(raw_key)

    api_key = ApiKeyModel(
        key_hash=key_hash,
        key_prefix=raw_key[:8],
        name=name,
        is_active=True,
        user_id=user.id,
        role_override=role_override,
        created_at=utc_now(),
    )
    session.add(api_key)
    session.commit()

    return templates.TemplateResponse(
        request,
        "partials/api_key_created.html",
        context={
            "key_name": name,
            "raw_key": raw_key,
            "effective_role": effective_role,
            "user": user,
        },
    )


@router.delete("/htmx/api-keys/{key_id}")
async def htmx_api_key_revoke(
    request: Request,
    key_id: UUID,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: revoke an API key and return updated list."""
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    api_key = session.get(ApiKeyModel, key_id)
    if not api_key or not api_key.is_active or api_key.user_id != user.id:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    session.add(api_key)
    session.commit()

    # Return updated list
    return await htmx_api_keys_list(request, session, user)
