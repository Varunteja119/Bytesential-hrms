from app.database.models.rbac import Permission, Role
from app.database.models.user import User
from app.security.password import hash_password


def _make_recruiter(db_session) -> None:
    perm = Permission(code="recruitment:manage")
    db_session.add(perm)
    role = Role(name="recruiter", permissions=[perm])
    db_session.add(role)
    user = User(email="recruiter@example.com", hashed_password=hash_password("supersecret1"), full_name="Recruiter", roles=[role])
    db_session.add(user)
    db_session.commit()


def _auth_headers(client) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": "recruiter@example.com", "password": "supersecret1"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _create_job(client, headers) -> str:
    resp = client.post("/api/v1/recruitment/jobs", json={"title": "Backend Engineer", "department": "Engineering", "description": "Build things."}, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


def test_create_job_requires_permission(client, db_session):
    user = User(email="noauth@example.com", hashed_password=hash_password("supersecret1"), full_name="No Auth")
    db_session.add(user)
    db_session.commit()
    login = client.post("/api/v1/auth/login", json={"email": "noauth@example.com", "password": "supersecret1"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    resp = client.post("/api/v1/recruitment/jobs", json={"title": "X", "department": "Y", "description": "Z"}, headers=headers)
    assert resp.status_code == 403


def test_create_and_list_jobs(client, db_session):
    _make_recruiter(db_session)
    headers = _auth_headers(client)
    job_id = _create_job(client, headers)
    resp = client.get("/api/v1/recruitment/jobs")
    assert resp.status_code == 200
    jobs = resp.json()
    assert any(j["id"] == job_id for j in jobs)
    assert jobs[0]["candidate_count"] == 0


def test_create_candidate_against_nonexistent_job_404s(client, db_session):
    _make_recruiter(db_session)
    headers = _auth_headers(client)
    resp = client.post("/api/v1/recruitment/candidates", json={"full_name": "Jane Doe", "email": "jane@example.com", "job_id": "00000000-0000-0000-0000-000000000000"}, headers=headers)
    assert resp.status_code == 404


def test_candidate_pipeline_happy_path(client, db_session):
    _make_recruiter(db_session)
    headers = _auth_headers(client)
    job_id = _create_job(client, headers)
    resp = client.post("/api/v1/recruitment/candidates", json={"full_name": "Jane Doe", "email": "jane@example.com", "job_id": job_id}, headers=headers)
    assert resp.status_code == 201
    candidate_id = resp.json()["id"]
    assert resp.json()["status"] == "applied"
    for target in ["screening", "interview", "hr_approval", "offered", "accepted"]:
        resp = client.patch(f"/api/v1/recruitment/candidates/{candidate_id}/status", json={"status": target}, headers=headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == target


def test_candidate_cannot_skip_pipeline_stages(client, db_session):
    _make_recruiter(db_session)
    headers = _auth_headers(client)
    job_id = _create_job(client, headers)
    resp = client.post("/api/v1/recruitment/candidates", json={"full_name": "Jane Doe", "email": "jane@example.com", "job_id": job_id}, headers=headers)
    candidate_id = resp.json()["id"]
    resp = client.patch(f"/api/v1/recruitment/candidates/{candidate_id}/status", json={"status": "offered"}, headers=headers)
    assert resp.status_code == 400


def test_terminal_state_has_no_further_transitions(client, db_session):
    _make_recruiter(db_session)
    headers = _auth_headers(client)
    job_id = _create_job(client, headers)
    resp = client.post("/api/v1/recruitment/candidates", json={"full_name": "Jane Doe", "email": "jane@example.com", "job_id": job_id}, headers=headers)
    candidate_id = resp.json()["id"]
    client.patch(f"/api/v1/recruitment/candidates/{candidate_id}/status", json={"status": "screening"}, headers=headers)
    client.patch(f"/api/v1/recruitment/candidates/{candidate_id}/status", json={"status": "rejected"}, headers=headers)
    resp = client.patch(f"/api/v1/recruitment/candidates/{candidate_id}/status", json={"status": "withdrawn"}, headers=headers)
    assert resp.status_code == 400
