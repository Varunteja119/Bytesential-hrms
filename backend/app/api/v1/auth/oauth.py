from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.connection.database import get_db
from app.database.models.user import User
from app.database.schemas.auth import TokenResponse
from app.security.jwt import create_access_token, create_refresh_token

router = APIRouter(prefix="/auth/oauth", tags=["auth"])

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/google/login")
async def google_login(request: Request):
    return await oauth.google.authorize_redirect(request, settings.google_redirect_uri)


@router.get("/google/callback", response_model=TokenResponse)
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
        userinfo = token["userinfo"]
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Google authentication failed")

    email = userinfo["email"]
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(email=email, full_name=userinfo.get("name", email), oauth_provider="google", oauth_sub=userinfo["sub"])
        db.add(user)
        db.commit()
        db.refresh(user)

    return TokenResponse(access_token=create_access_token(str(user.id)), refresh_token=create_refresh_token(str(user.id)))
