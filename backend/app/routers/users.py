from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.schemas.user import UserResponse, UserUpdate
from backend.app.services.security import (
    get_current_user,
    hash_password,
    verify_password,
)
from backend.app.utils.exceptions import DuplicateException, UnauthorizedException
from backend.app.limiter import limiter

router = APIRouter(prefix="/users", tags=["Users"])

# Create user happens at authorization


# READ
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the current user's profile",
    responses={
        401: {"description": "Authentication is required"},
    },
)
def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """Return the profile of the authenticated user.

    The password hash is intentionally excluded from the response.
    """
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"description": "Authentication is required, or the current password is incorrect."},
        409: {"description": "An account with this email already exists."},
        422: {"description": "The update payload failed validation."},
        429: {"description": "Too many profile update requests from this client."},
    },
    summary="Update the current user's profile.",
)
@limiter.limit("10/minute")
def update_my_profile(
    request: Request,
    changes: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    """Update the authenticated user's name, email, or password.

    Changing the email or password requires the current password.
    """
    updates = changes.model_dump(
        exclude_unset=True, exclude={"current_password"}
    )

    if not updates:
        raise HTTPException(
            status_code=422, detail="Provide at least one field to update."
        )

    if "email" in updates or "password" in updates:
        if not verify_password(changes.current_password, current_user.hashed_password):
            raise UnauthorizedException("Current password is incorrect")

    if "email" in updates and updates["email"] != current_user.email:
        existing = db.query(User).filter(User.email == updates["email"]).first()
        if existing:
            raise DuplicateException("User", "email", updates["email"])

    if "password" in updates:
        current_user.hashed_password = hash_password(updates.pop("password"))

    for field, value in updates.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user
