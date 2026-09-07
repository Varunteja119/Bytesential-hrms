import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database.connection.database import get_db
from app.database.models.user import User
from app.security.jwt import TokenError, decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        user_id = decode_token(token, expected_type="access")
    except TokenError:
        raise credentials_error
    try:
        user_pk = uuid.UUID(user_id)
    except ValueError:
        raise credentials_error
    user = db.get(User, user_pk)
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_permission(permission_code: str):
    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.has_permission(permission_code):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing required permission: {permission_code}")
        return current_user
    return _checker
