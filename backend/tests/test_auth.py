def test_register_creates_user(client):
    resp = client.post("/api/v1/auth/register", json={"email": "alice@example.com", "password": "supersecret1", "full_name": "Alice"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "alice@example.com"
    assert "hashed_password" not in body


def test_register_duplicate_email_rejected(client):
    payload = {"email": "bob@example.com", "password": "supersecret1", "full_name": "Bob"}
    client.post("/api/v1/auth/register", json=payload)
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409


def test_login_success_returns_tokens(client):
    client.post("/api/v1/auth/register", json={"email": "carol@example.com", "password": "supersecret1", "full_name": "Carol"})
    resp = client.post("/api/v1/auth/login", json={"email": "carol@example.com", "password": "supersecret1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_login_wrong_password_rejected(client):
    client.post("/api/v1/auth/register", json={"email": "dave@example.com", "password": "supersecret1", "full_name": "Dave"})
    resp = client.post("/api/v1/auth/login", json={"email": "dave@example.com", "password": "wrongpass"})
    assert resp.status_code == 401


def test_login_nonexistent_user_rejected(client):
    resp = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever1"})
    assert resp.status_code == 401


def test_me_requires_valid_token(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user(client):
    client.post("/api/v1/auth/register", json={"email": "erin@example.com", "password": "supersecret1", "full_name": "Erin"})
    login_resp = client.post("/api/v1/auth/login", json={"email": "erin@example.com", "password": "supersecret1"})
    access_token = login_resp.json()["access_token"]
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "erin@example.com"


def test_refresh_token_issues_new_access_token(client):
    client.post("/api/v1/auth/register", json={"email": "frank@example.com", "password": "supersecret1", "full_name": "Frank"})
    login_resp = client.post("/api/v1/auth/login", json={"email": "frank@example.com", "password": "supersecret1"})
    refresh_token = login_resp.json()["refresh_token"]
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_refresh_rejects_access_token_used_as_refresh(client):
    client.post("/api/v1/auth/register", json={"email": "grace@example.com", "password": "supersecret1", "full_name": "Grace"})
    login_resp = client.post("/api/v1/auth/login", json={"email": "grace@example.com", "password": "supersecret1"})
    access_token = login_resp.json()["access_token"]
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401


def test_password_reset_request_always_returns_202(client):
    resp_existing = client.post("/api/v1/auth/password-reset/request", json={"email": "nobody@example.com"})
    assert resp_existing.status_code == 202


def test_password_reset_sends_email_with_working_link(client, fake_email_client):
    client.post("/api/v1/auth/register", json={"email": "henry@example.com", "password": "supersecret1", "full_name": "Henry"})
    resp = client.post("/api/v1/auth/password-reset/request", json={"email": "henry@example.com"})
    assert resp.status_code == 202
    assert len(fake_email_client.sent) == 1
    sent = fake_email_client.sent[0]
    assert sent["to"] == "henry@example.com"
    assert "reset-password?token=" in sent["body"]


def test_password_reset_no_email_sent_for_unregistered_address(client, fake_email_client):
    resp = client.post("/api/v1/auth/password-reset/request", json={"email": "nobody@example.com"})
    assert resp.status_code == 202
    assert len(fake_email_client.sent) == 0


def test_password_reset_confirm_changes_password(client, fake_email_client):
    client.post("/api/v1/auth/register", json={"email": "iris@example.com", "password": "supersecret1", "full_name": "Iris"})
    client.post("/api/v1/auth/password-reset/request", json={"email": "iris@example.com"})
    body = fake_email_client.sent[0]["body"]
    token = body.split("token=")[1].split("\n")[0].strip()
    resp = client.post("/api/v1/auth/password-reset/confirm", json={"reset_token": token, "new_password": "brandnewpass456"})
    assert resp.status_code == 200
    old_login = client.post("/api/v1/auth/login", json={"email": "iris@example.com", "password": "supersecret1"})
    assert old_login.status_code == 401
    new_login = client.post("/api/v1/auth/login", json={"email": "iris@example.com", "password": "brandnewpass456"})
    assert new_login.status_code == 200


def test_password_reset_confirm_rejects_garbage_token(client):
    resp = client.post("/api/v1/auth/password-reset/confirm", json={"reset_token": "not-a-real-token", "new_password": "brandnewpass456"})
    assert resp.status_code == 400
