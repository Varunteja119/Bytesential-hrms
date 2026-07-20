"""
JWT issuing/verification.

Two token types, both signed with the same secret but with a "type" claim
so a refresh token can't be replayed as an access token even if it leaks
into the wrong header:
- access token  -> short-lived (30 min), sent on every request
- refresh token -> long-lived (7 days), used only to mint new access tokens
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from jose import JWTError, jwt

from app.config.settings import settings


class TokenError(Exception):
    pass


TokenType = Literal["access", "refresh", "reset"]


def _create_token(subject: str, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(user_id: str) -> str:
    return _create_token(user_id, "access", timedelta(minutes=settings.access_token_expire_minutes))


def create_refresh_token(user_id: str) -> str:
    return _create_token(user_id, "refresh", timedelta(days=settings.refresh_token_expire_days))


def create_reset_token(user_id: str) -> str:
    # Deliberately short-lived (15 min) — this token proves "I own this inbox", nothing more.
    return _create_token(user_id, "reset", timedelta(minutes=15))


def decode_token(token: str, expected_type: TokenType) -> str:
    """Returns the user_id (sub claim). Raises TokenError on any problem."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise TokenError("Invalid or expired token") from exc

    if payload.get("type") != expected_type:
        raise TokenError(f"Expected a {expected_type} token")

    subject = payload.get("sub")
    if subject is None:
        raise TokenError("Token missing subject")
    return subject
