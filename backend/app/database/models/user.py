from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection.database import Base
from app.database.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin
from app.database.models.rbac import user_roles, Role


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255))  # null for OAuth-only accounts
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    # set when the user signs in via Google OAuth2 instead of a password
    oauth_provider: Mapped[str | None] = mapped_column(String(50))
    oauth_sub: Mapped[str | None] = mapped_column(String(255))

    roles: Mapped[list["Role"]] = relationship(secondary=user_roles, back_populates="users")

    def has_permission(self, code: str) -> bool:
        """Flattens role->permissions for a single check. Used by the RBAC dependency."""
        if self.is_superuser:
            return True
        return any(p.code == code for role in self.roles for p in role.permissions)
