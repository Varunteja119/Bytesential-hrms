from app.database.models.rbac import Permission, Role
from app.database.models.user import User
from app.security.password import hash_password


def _make_user_with_permissions(db_session, email: str, permission_codes: list[str]) -> User:
    perms = [Permission(code=code) for code in permission_codes]
    db_session.add_all(perms)

    role = Role(name=f"role-for-{email}", permissions=perms)
    db_session.add(role)

    user = User(email=email, hashed_password=hash_password("supersecret1"), full_name="Test User", roles=[role])
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _login(client, email: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret1"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_user_without_permission_gets_403(client, db_session):
    _make_user_with_permissions(db_session, "noaccess@example.com", [])
    token = _login(client, "noaccess@example.com")

    resp = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_user_with_permission_gets_200(client, db_session):
    _make_user_with_permissions(db_session, "hasaccess@example.com", ["user:read"])
    token = _login(client, "hasaccess@example.com")

    resp = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_superuser_bypasses_permission_check(client, db_session):
    user = User(
        email="super@example.com",
        hashed_password=hash_password("supersecret1"),
        full_name="Super User",
        is_superuser=True,
    )
    db_session.add(user)
    db_session.commit()

    token = _login(client, "super@example.com")
    resp = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
