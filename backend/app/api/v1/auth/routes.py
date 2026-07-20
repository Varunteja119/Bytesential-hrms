import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.database.connection.database import get_db
from app.database.models.user import User
from app.database.schemas.auth import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.database.schemas.user import UserOut
from app.security.jwt import (
    TokenError,
    create_access_token,
    create_refresh_token,
    create_reset_token,
    decode_token,
)
from app.security.password import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("bytesentinel.auth")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.from_orm_user(user)


@router.post("/token", response_model=TokenResponse)
@limiter.limit("5/minute")
def token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    OAuth2 password-grant endpoint (form-encoded: username/password), used by
    Swagger UI's "Authorize" button and any standard OAuth2 client library.

    This is functionally identical to /login — same checks, same tokens —
    just a different request shape. Your actual frontend should use the JSON
    /login route instead; this exists purely for OAuth2-spec compatibility.
    Note: "username" here is the user's email.
    """
    invalid_credentials = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not user.hashed_password or not verify_password(form_data.password, user.hashed_password):
        raise invalid_credentials
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is deactivated")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")  # blunts brute-force/credential-stuffing on this route specifically
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()

    # Same error for "no such user" and "wrong password" — don't leak which one it was.
    invalid_credentials = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise invalid_credentials
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is deactivated")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    invalid_refresh = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")
    try:
        user_id = decode_token(payload.refresh_token, expected_type="refresh")
        user_pk = uuid.UUID(user_id)
    except (TokenError, ValueError):
        raise invalid_refresh

    user = db.get(User, user_pk)
    if user is None or not user.is_active:
        raise invalid_refresh

    # Issue both tokens fresh (rotating the refresh token limits replay if one leaks)
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut.from_orm_user(current_user)


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/minute")
def request_password_reset(request: Request, payload: PasswordResetRequest, db: Session = Depends(get_db)):
    """
    Always returns 202 regardless of whether the email exists — a differing
    response here would let an attacker enumerate registered accounts.

    NOTE: actual email delivery isn't wired up yet (that's the notifications
    service, planned for a later phase). For now the reset link is logged
    server-side so the flow is testable end-to-end; swap this for a call
    into the email service once it exists.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if user is not None:
        reset_token = create_reset_token(str(user.id))
        logger.info("Password reset requested for %s. Token: %s", user.email, reset_token)
    return {"message": "If that email is registered, a reset link has been sent."}


@router.post("/password-reset/confirm", status_code=status.HTTP_200_OK)
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    invalid_reset = HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset token")
    try:
        user_id = decode_token(payload.reset_token, expected_type="reset")
        user_pk = uuid.UUID(user_id)
    except (TokenError, ValueError):
        raise invalid_reset

    user = db.get(User, user_pk)
    if user is None:
        raise invalid_reset

    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password updated successfully."}
