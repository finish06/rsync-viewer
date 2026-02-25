import logging

from fastapi import APIRouter, HTTPException, status
from sqlmodel import func, select

from app.api.deps import SessionDep
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.services.auth import ROLE_ADMIN, ROLE_VIEWER, hash_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(user_data: UserCreate, session: SessionDep) -> User:
    """Register a new user. First registered user gets Admin role."""
    # Check for duplicate username
    existing_username = session.exec(
        select(User).where(User.username == user_data.username)
    ).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    # Check for duplicate email
    existing_email = session.exec(
        select(User).where(User.email == user_data.email)
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )

    # Determine role: first user gets admin, subsequent get viewer
    user_count = session.exec(select(func.count()).select_from(User)).one()
    role = ROLE_ADMIN if user_count == 0 else ROLE_VIEWER

    # Create user
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    logger.info(
        "User registered",
        extra={
            "user_id": str(user.id),
            "username": user.username,
            "role": user.role,
        },
    )

    return user
