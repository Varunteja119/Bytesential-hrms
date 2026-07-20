"""
Auth + RBAC as FastAPI dependencies.

Pattern: `get_current_user` decodes the JWT and loads the User row.
`require_permission("employee:read")` wraps that and additionally checks
User.has_permission(). Routes declare what they need, e.g.:

    @router.get("/employees", dependencies=[Depends(require_permission("employee:read"))])

This keeps permission checks declarative and out of the business logic.
"""
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database.connection.database import get_db
from app.database.models.user import User
from app.security.jwt import TokenError, decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = decode_token(token, expected_type="access")
    except TokenError:
        raise credentials_error

    try:
        # the UUID column type needs an actual uuid.UUID, not the raw string
        # the JWT "sub" claim carries — and a tampered/garbage sub shouldn't 500.
        user_pk = uuid.UUID(user_id)
    except ValueError:
        raise credentials_error

    user = db.get(User, user_pk)
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_permission(permission_code: str):
    """Returns a dependency callable — usage: Depends(require_permission('payroll:approve'))"""

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.has_permission(permission_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission_code}",
            )
        return current_user

    return _checker
