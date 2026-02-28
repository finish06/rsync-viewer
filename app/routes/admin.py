import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select, func

from app.database import get_session
from app.api.deps import OptionalUserDep
from app.templating import templates
from app.models.user import User
from app.services.auth import role_at_least, ROLE_ADMIN, VALID_ROLES

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/admin/users")
async def admin_users_page(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """Render admin user management page (admin only)."""
    if not user or not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")

    users_list = session.exec(select(User).order_by(User.created_at.desc())).all()  # type: ignore[attr-defined]
    return templates.TemplateResponse(
        request,
        "admin_users.html",
        context={"users": users_list, "user": user, "current_user": user},
    )


@router.get("/htmx/admin/users")
async def htmx_admin_user_list(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX partial: admin user list table."""
    if not user or not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")

    users_list = session.exec(select(User).order_by(User.created_at.desc())).all()  # type: ignore[attr-defined]
    return templates.TemplateResponse(
        request,
        "partials/admin_user_list.html",
        context={"users": users_list, "current_user": user},
    )


@router.put("/htmx/admin/users/{user_id}/role")
async def htmx_admin_change_role(
    request: Request,
    user_id: UUID,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: change a user's role."""
    if not user or not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")

    form = await request.form()
    new_role = str(form.get("role", "")).strip()

    if new_role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role: {new_role}")
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    target = session.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.role == "admin" and new_role != "admin":
        admin_count = session.exec(
            select(func.count()).where(User.role == "admin", User.is_active.is_(True))  # type: ignore[attr-defined]
        ).one()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last admin")

    target.role = new_role
    session.add(target)
    session.commit()

    return await htmx_admin_user_list(request, session, user)


@router.put("/htmx/admin/users/{user_id}/toggle-status")
async def htmx_admin_toggle_status(
    request: Request,
    user_id: UUID,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: toggle user active status."""
    if not user or not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own status")

    target = session.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.is_active = not target.is_active
    session.add(target)
    session.commit()

    return await htmx_admin_user_list(request, session, user)


@router.delete("/htmx/admin/users/{user_id}")
async def htmx_admin_delete_user(
    request: Request,
    user_id: UUID,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: delete a user."""
    if not user or not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    target = session.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.role == "admin":
        admin_count = session.exec(
            select(func.count()).where(User.role == "admin", User.is_active.is_(True))  # type: ignore[attr-defined]
        ).one()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last admin")

    session.delete(target)
    session.commit()

    return await htmx_admin_user_list(request, session, user)
