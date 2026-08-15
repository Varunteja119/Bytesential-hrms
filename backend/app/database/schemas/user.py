import uuid

from pydantic import BaseModel, ConfigDict, EmailStr


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # lets us return an ORM object directly

    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    must_change_password: bool
    roles: list[str] = []

    @classmethod
    def from_orm_user(cls, user) -> "UserOut":
        # roles is a relationship of Role objects; flatten to names for the API response
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            must_change_password=user.must_change_password,
            roles=[r.name for r in user.roles],
        )
