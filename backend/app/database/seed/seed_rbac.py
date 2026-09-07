import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.database.connection.database import SessionLocal
from app.database.models.rbac import Permission, Role
from app.database.models.user import User
from app.security.password import hash_password

DEFAULT_PERMISSIONS = [
    ("user:read", "View users"),
    ("user:write", "Create/update users"),
    ("employee:read", "View employee records"),
    ("employee:write", "Create/update employee records"),
    ("leave:read", "View leave requests and balances"),
    ("leave:approve", "Approve or reject leave requests"),
    ("payroll:read", "View payroll runs and payslips"),
    ("payroll:manage", "Generate payroll runs, edit salary structures and payroll config"),
    ("payroll:approve_hr", "HR approval step for a payroll run"),
    ("payroll:approve_finance", "Finance approval step for a payroll run"),
    ("recruitment:manage", "Manage recruitment pipeline"),
    ("attendance:read", "View attendance records"),
    ("attendance:write", "Create/correct attendance records"),
]

DEFAULT_ROLES = {
    "admin": [code for code, _ in DEFAULT_PERMISSIONS],
    "hr_manager": ["user:read", "employee:read", "employee:write", "leave:read", "leave:approve", "recruitment:manage", "attendance:read", "attendance:write", "payroll:read", "payroll:manage", "payroll:approve_hr"],
    "finance_manager": ["payroll:read", "payroll:approve_finance"],
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

    user = User(email=email, hashed_password=hash_password(password), full_name="ByteSentinel Admin", is_superuser=True)
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
