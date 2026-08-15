import io

from docx import Document

from app.database.models.rbac import Permission, Role
from app.database.models.recruitment import Candidate, CandidateStatus, Job, JobStatus
from app.database.models.user import User
from app.security.password import hash_password
from app.services.storage import get_storage_client


class FakeStorageClient:
    def __init__(self):
        self.files: dict[str, bytes] = {}

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        self.files[key] = data

    def download(self, key: str) -> bytes:
        return self.files[key]


def _make_hr_user(db_session, extra_permissions: list[str] | None = None) -> None:
    codes = ["employee:read", "employee:write"] + (extra_permissions or [])
    perms = [Permission(code=c) for c in codes]
    db_session.add_all(perms)
    role = Role(name="hr", permissions=perms)
    db_session.add(role)
    user = User(email="hr@example.com", hashed_password=hash_password("supersecret1"), full_name="HR Person", roles=[role])
    db_session.add(user)

    # employee role is required by the provisioning logic itself
    employee_role = Role(name="employee", permissions=[])
    db_session.add(employee_role)
    db_session.commit()


def _hr_headers(client) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": "hr@example.com", "password": "supersecret1"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _make_accepted_candidate(db_session, email="newhire@example.com") -> str:
    hr = db_session.query(User).filter(User.email == "hr@example.com").first()
    job = Job(title="Engineer", department="Eng", description="desc", status=JobStatus.OPEN, created_by_id=hr.id)
    db_session.add(job)
    db_session.commit()

    candidate = Candidate(full_name="New Hire", email=email, job_id=job.id, status=CandidateStatus.ACCEPTED)
    db_session.add(candidate)
    db_session.commit()
    return str(candidate.id)


def _provision(client, headers, candidate_id, department="Engineering", designation="Software Engineer"):
    return client.post(
        "/api/v1/employees/provision",
        json={"candidate_id": candidate_id, "department": department, "designation": designation, "date_of_joining": "2026-08-01"},
        headers=headers,
    )


def test_provision_requires_accepted_candidate(client, db_session):
    _make_hr_user(db_session)
    headers = _hr_headers(client)

    hr = db_session.query(User).filter(User.email == "hr@example.com").first()
    job = Job(title="Engineer", department="Eng", description="desc", created_by_id=hr.id)
    db_session.add(job)
    db_session.commit()
    candidate = Candidate(full_name="Not Yet", email="notyet@example.com", job_id=job.id, status=CandidateStatus.APPLIED)
    db_session.add(candidate)
    db_session.commit()

    resp = _provision(client, headers, str(candidate.id))
    assert resp.status_code == 400


def test_provision_creates_employee_and_user(client, db_session, fake_email_client):
    _make_hr_user(db_session)
    headers = _hr_headers(client)
    candidate_id = _make_accepted_candidate(db_session)

    resp = _provision(client, headers, candidate_id)
    assert resp.status_code == 201
    body = resp.json()
    assert body["employee"]["employee_code"] == "EMP-000001"
    assert body["employee"]["employment_status"] == "pending_activation"
    assert len(body["temp_password"]) == 12

    # the new hire can now log in with the temp password
    login = client.post("/api/v1/auth/login", json={"email": "newhire@example.com", "password": body["temp_password"]})
    assert login.status_code == 200

    # welcome email was actually sent, with the real temp password and employee code in it
    assert len(fake_email_client.sent) == 1
    sent = fake_email_client.sent[0]
    assert sent["to"] == "newhire@example.com"
    assert body["temp_password"] in sent["body"]
    assert "EMP-000001" in sent["body"]


def test_cannot_provision_same_candidate_twice(client, db_session):
    _make_hr_user(db_session)
    headers = _hr_headers(client)
    candidate_id = _make_accepted_candidate(db_session)

    first = _provision(client, headers, candidate_id)
    assert first.status_code == 201

    second = _provision(client, headers, candidate_id)
    assert second.status_code == 400


def test_employee_can_view_and_update_own_profile(client, db_session):
    _make_hr_user(db_session)
    headers = _hr_headers(client)
    candidate_id = _make_accepted_candidate(db_session)
    temp_password = _provision(client, headers, candidate_id).json()["temp_password"]

    login = client.post("/api/v1/auth/login", json={"email": "newhire@example.com", "password": temp_password})
    employee_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = client.get("/api/v1/employees/me", headers=employee_headers)
    assert resp.status_code == 200
    assert resp.json()["profile_completed"] is False

    update = client.patch(
        "/api/v1/employees/me",
        json={"phone": "9999999999", "address": "123 Main St", "date_of_birth": "1995-01-01", "bank_account_number": "123456"},
        headers=employee_headers,
    )
    assert update.status_code == 200
    assert update.json()["profile_completed"] is True


def test_employee_cannot_edit_own_department(client, db_session):
    """Self-service schema doesn't even expose department/designation -- confirms the split is enforced at the schema level."""
    _make_hr_user(db_session)
    headers = _hr_headers(client)
    candidate_id = _make_accepted_candidate(db_session)
    temp_password = _provision(client, headers, candidate_id).json()["temp_password"]

    login = client.post("/api/v1/auth/login", json={"email": "newhire@example.com", "password": temp_password})
    employee_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = client.patch("/api/v1/employees/me", json={"department": "Finance"}, headers=employee_headers)
    # extra field is silently ignored by the schema (not an error) -- department stays unchanged
    assert resp.status_code == 200
    assert resp.json()["department"] == "Engineering"


def test_employee_cannot_view_other_employees_record(client, db_session):
    _make_hr_user(db_session)
    headers = _hr_headers(client)

    c1 = _make_accepted_candidate(db_session, email="hire1@example.com")
    e1 = _provision(client, headers, c1).json()
    c2 = _make_accepted_candidate(db_session, email="hire2@example.com")
    e2 = _provision(client, headers, c2).json()

    login1 = client.post("/api/v1/auth/login", json={"email": "hire1@example.com", "password": e1["temp_password"]})
    headers1 = {"Authorization": f"Bearer {login1.json()['access_token']}"}

    resp = client.get(f"/api/v1/employees/{e2['employee']['id']}", headers=headers1)
    assert resp.status_code == 403


def test_hr_can_update_department_and_manager(client, db_session):
    _make_hr_user(db_session)
    headers = _hr_headers(client)
    candidate_id = _make_accepted_candidate(db_session)
    employee_id = _provision(client, headers, candidate_id).json()["employee"]["id"]

    resp = client.patch(
        f"/api/v1/employees/{employee_id}",
        json={"department": "Platform Engineering", "designation": "Senior Engineer"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["department"] == "Platform Engineering"
    assert resp.json()["designation"] == "Senior Engineer"


def test_activation_blocked_until_profile_complete_and_docs_verified(client, db_session):
    _make_hr_user(db_session)
    headers = _hr_headers(client)
    candidate_id = _make_accepted_candidate(db_session)
    employee_id = _provision(client, headers, candidate_id).json()["employee"]["id"]

    # profile not complete yet -> activation blocked
    resp = client.post(f"/api/v1/employees/{employee_id}/activate", headers=headers)
    assert resp.status_code == 400


def test_full_onboarding_happy_path(client, db_session):
    from app.main import app

    fake_storage = FakeStorageClient()
    app.dependency_overrides[get_storage_client] = lambda: fake_storage

    try:
        _make_hr_user(db_session)
        headers = _hr_headers(client)
        candidate_id = _make_accepted_candidate(db_session)
        provision = _provision(client, headers, candidate_id).json()
        employee_id = provision["employee"]["id"]
        temp_password = provision["temp_password"]

        login = client.post("/api/v1/auth/login", json={"email": "newhire@example.com", "password": temp_password})
        employee_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        # 1. change password (required before activation -- see Phase 2c onboarding gate)
        client.post(
            "/api/v1/auth/change-password",
            json={"current_password": temp_password, "new_password": "brandnewpass123"},
            headers=employee_headers,
        )

        # 2. profile completion (self-service)
        client.patch(
            "/api/v1/employees/me",
            json={"phone": "9999999999", "address": "123 Main St", "date_of_birth": "1995-01-01", "bank_account_number": "123456"},
            headers=employee_headers,
        )

        # 3. document upload (self-service) -- all three required types (aadhaar, pan, bank_proof)
        document_ids = []
        for doc_type in ["aadhaar", "pan", "bank_proof"]:
            doc = Document()
            doc.add_paragraph(f"Fake {doc_type} content")
            buf = io.BytesIO()
            doc.save(buf)
            upload_resp = client.post(
                f"/api/v1/employees/{employee_id}/documents?document_type={doc_type}",
                files={"file": (f"{doc_type}.docx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
                headers=employee_headers,
            )
            assert upload_resp.status_code == 201
            document_ids.append(upload_resp.json()["id"])

        # activation still blocked -- documents not verified yet
        blocked = client.post(f"/api/v1/employees/{employee_id}/activate", headers=headers)
        assert blocked.status_code == 400

        # 4. HR verifies each document
        for document_id in document_ids:
            verify_resp = client.patch(f"/api/v1/employees/{employee_id}/documents/{document_id}/verify", headers=headers)
            assert verify_resp.status_code == 200
            assert verify_resp.json()["verified"] is True

        # 5. HR activates
        activate_resp = client.post(f"/api/v1/employees/{employee_id}/activate", headers=headers)
        assert activate_resp.status_code == 200
        assert activate_resp.json()["employment_status"] == "active"
        assert activate_resp.json()["hr_verified"] is True
    finally:
        del app.dependency_overrides[get_storage_client]
