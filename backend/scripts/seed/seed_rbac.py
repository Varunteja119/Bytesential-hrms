"""
Seeds default permissions, roles, and a superuser.

Run after migrations, once per environment:
    python -m scripts.seed.seed_rbac

Idempotent — safe to re-run; it skips anything that already exists by
unique code/email, so it won't duplicate rows or clobber edits you made
through the app.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.database.connection.database import SessionLocal  # noqa: E402
from app.database.models.rbac import Permission, Role  # noqa: E402
from app.database.models.user import User  # noqa: E402
from app.security.password import hash_password  # noqa: E402

# (code, description) — extend this list as new modules land in later phases.
DEFAULT_PERMISSIONS = [
    ("user:read", "View users"),
    ("user:write", "Create/update users"),
    ("employee:read", "View employee records"),
    ("employee:write", "Create/update employee records"),
    ("leave:approve", "Approve leave requests"),
    ("payroll:approve", "Approve payroll runs"),
    ("recruitment:manage", "Manage recruitment pipeline"),
]

# role_name -> list of permission codes it grants
DEFAULT_ROLES = {
    "admin": [code for code, _ in DEFAULT_PERMISSIONS],  # all permissions
    "hr_manager": ["user:read", "employee:read", "employee:write", "leave:approve", "recruitment:manage"],
    "employee": ["employee:read"],
}


def seed_permissions(db) -> dict[str, Permission]:
    existing = {p.code: p for p in db.query(Permission).all()}
    for code, description in DEFAULT_PERMISSIONS:
        if code not in existing:
            perm = Permission(code=code, description=description)
            db.add(perm)
            existing[code] = perm
    db.commit()
    return {p.code: p for p in db.query(Permission).all()}


def seed_roles(db, permissions: dict[str, Permission]) -> dict[str, Role]:
    existing = {r.name: r for r in db.query(Role).all()}
    for role_name, perm_codes in DEFAULT_ROLES.items():
        role = existing.get(role_name)
        if role is None:
            role = Role(name=role_name, description=f"Default '{role_name}' role")
            db.add(role)
            existing[role_name] = role
        # keep role's permission set in sync with DEFAULT_ROLES on every run
        role.permissions = [permissions[code] for code in perm_codes]
    db.commit()
    return existing


def seed_superuser(db, roles: dict[str, Role]) -> None:
    email = os.getenv("SEED_SUPERUSER_EMAIL", "admin@bytesentinel.com")
    password = os.getenv("SEED_SUPERUSER_PASSWORD", "ChangeMe123!")

    user = db.query(User).filter(User.email == email).first()
    if user is not None:
        print(f"Superuser {email} already exists — skipping.")
        return

    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name="ByteSentinel Admin",
        is_superuser=True,
    )
    user.roles = [roles["admin"]]
    db.add(user)
    db.commit()
    print(f"Created superuser {email} (password from SEED_SUPERUSER_PASSWORD env, or default — change it immediately).")


def main():
    db = SessionLocal()
    try:
        permissions = seed_permissions(db)
        roles = seed_roles(db, permissions)
        seed_superuser(db, roles)
        print(f"Seeded {len(permissions)} permissions and {len(roles)} roles.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
