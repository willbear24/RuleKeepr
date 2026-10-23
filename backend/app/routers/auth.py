from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from backend.app.utils.exceptions import DuplicateException, UnauthorizedException
from backend.app.utils.notifications import send_email
from backend.app.services.security import (
    create_access_token,
    hash_password,
    verify_password
)
from backend.app.limiter import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=201,
    responses={
        409: {"description": "An account with this email already exists"},
        429: {"description": "Too many registrations attempts with this client."},
        422: {"description": "The registration payload failed validation."},
    },
    summary="Register a new user",
)
@limiter.limit("10/minute") # Prevents account creation and registration email abuse
def register(
    request: Request,
    credentials: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a user account and send a welcome email in the background.

    A JWT access token is returned immediately after the account is saved.
    Passwords are hashed before they are stored.

    Raises:
        409: The email address is already registered.
        422: The name, email, or password failed validation.
    """
    existing = db.query(User).filter(User.email == credentials.email).first()

    if existing:
        raise DuplicateException("User", "email", credentials.email)

    user = User(
        name=credentials.name,
        email=credentials.email,
        hashed_password=hash_password(credentials.password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Example background task, sends an email to a new user welcoming them to the platform.
    background_tasks.add_task(
        send_email,
        user.email,
        "Welcome to the RuleKeepr",
        f"Hi {user.name}, your account has been created successfully.",
    )

    token = create_access_token(data={"sub": str(user.id)})

    return {
        "access_token": token,
        "token_type": "bearer",
    }

@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"description": "The email or password is incorrect."},
        429: {"description": "Too many login attempts from this client."},
        422: {"description": "The login payload failed validation."},
    },
    summary="Log in a user",
)
@limiter.limit("5/minute") # Prevents more than 5 login attempts a minute blocking password brute force attempts
def login(
    request: Request,
    credentials: LoginRequest,
    db: Session = Depends(get_db),
):
    """Authenticate a user and return a JWT access token.

    The token should be sent in the `Authorization` header as
    `Bearer <access_token>` when calling protected task endpoints.

    Raises:
        401: The email or password is incorrect.
        422: The login payload failed validation.
    """
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise UnauthorizedException("Invalid email or password")

    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}






