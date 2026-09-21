from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies.auth import require_permission
from app.database.connection.database import get_db
from app.database.models.user import User
from app.database.schemas.user import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut], dependencies=[Depends(require_permission("user:read"))])
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [UserOut.from_orm_user(u) for u in users]
