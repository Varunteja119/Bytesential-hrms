from datetime import date

from app.database.models.attendance import Attendance, AttendanceStatus
from app.database.models.employee import Employee, EmploymentStatus
from app.database.models.rbac import Permission, Role
from app.database.models.recruitment import Job, JobStatus
from app.database.models.user import User
from app.security.password import hash_password


def _make_hr_user(db_session) -> None:
    perms = [Permission(code=c) for c in ["employee:read", "employee:write", "leave:read", "leave:approve"]]
    db_session.add_all(perms)
    role = Role(name="hr", permissions=perms)
    db_session.add(role)
    user = User(email="hr@example.com", hashed_password=hash_password("supersecret1"), full_name="HR Person", roles=[role])
    db_session.add(user)
    employee_role = Role(name="employee", permissions=[])
    db_session.add(employee_role)
    db_session.commit()


def _hr_headers(client) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": "hr@example.com", "password": "supersecret1"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _make_active_employee(db_session, email="employee@example.com", password="supersecret1") -> tuple[str, str]:
    hr = db_session.query(User).filter(User.email == "hr@example.com").first()
    job = Job(title="Engineer", department="Eng", description="desc", status=JobStatus.OPEN, created_by_id=hr.id)
    db_session.add(job)
    db_session.commit()
    user = User(email=email, hashed_password=hash_password(password), full_name="Test Employee")
    db_session.add(user)
    db_session.commit()
    employee = Employee(employee_code=f"EMP-{db_session.query(Employee).count() + 1:06d}", user_id=user.id, department="Engineering",
                         designation="Software Engineer", date_of_joining=date(2026, 1, 1), employment_status=EmploymentStatus.ACTIVE)
    db_session.add(employee)
    db_session.commit()
    return str(employee.id), email


def _employee_headers(client, email, password="supersecret1") -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_apply_leave_success(client, db_session):
    _make_hr_user(db_session)
    _, email = _make_active_employee(db_session)
    headers = _employee_headers(client, email)
    resp = client.post("/api/v1/leave/apply", json={"leave_type": "casual", "start_date": "2026-09-01", "end_date": "2026-09-03", "reason": "Family trip"}, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["days_requested"] == 3
    assert body["status"] == "pending"


def test_apply_leave_exceeding_balance_rejected(client, db_session):
    _make_hr_user(db_session)
    _, email = _make_active_employee(db_session)
    headers = _employee_headers(client, email)
    resp = client.post("/api/v1/leave/apply", json={"leave_type": "casual", "start_date": "2026-09-01", "end_date": "2026-09-13"}, headers=headers)
    assert resp.status_code == 400
    assert "insufficient" in resp.json()["error"]["message"].lower()


def test_unpaid_leave_has_no_balance_cap(client, db_session):
    _make_hr_user(db_session)
    _, email = _make_active_employee(db_session)
    headers = _employee_headers(client, email)
    resp = client.post("/api/v1/leave/apply", json={"leave_type": "unpaid", "start_date": "2026-09-01", "end_date": "2026-09-30"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["days_requested"] == 30


def test_overlapping_leave_requests_rejected(client, db_session):
    _make_hr_user(db_session)
    _, email = _make_active_employee(db_session)
    headers = _employee_headers(client, email)
    client.post("/api/v1/leave/apply", json={"leave_type": "casual", "start_date": "2026-09-01", "end_date": "2026-09-05"}, headers=headers)
    resp = client.post("/api/v1/leave/apply", json={"leave_type": "sick", "start_date": "2026-09-03", "end_date": "2026-09-04"}, headers=headers)
    assert resp.status_code == 400
    assert "overlap" in resp.json()["error"]["message"].lower()


def test_end_date_before_start_date_rejected(client, db_session):
    _make_hr_user(db_session)
    _, email = _make_active_employee(db_session)
    headers = _employee_headers(client, email)
    resp = client.post("/api/v1/leave/apply", json={"leave_type": "casual", "start_date": "2026-09-05", "end_date": "2026-09-01"}, headers=headers)
    assert resp.status_code == 400


def test_employee_can_cancel_own_pending_request(client, db_session):
    _make_hr_user(db_session)
    _, email = _make_active_employee(db_session)
    headers = _employee_headers(client, email)
    apply_resp = client.post("/api/v1/leave/apply", json={"leave_type": "casual", "start_date": "2026-09-01", "end_date": "2026-09-02"}, headers=headers)
    request_id = apply_resp.json()["id"]
    resp = client.post(f"/api/v1/leave/{request_id}/cancel", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


def test_employee_cannot_cancel_another_employees_request(client, db_session):
    _make_hr_user(db_session)
    _, email1 = _make_active_employee(db_session, email="emp1@example.com")
    _, email2 = _make_active_employee(db_session, email="emp2@example.com")
    headers1 = _employee_headers(client, email1)
    headers2 = _employee_headers(client, email2)
    apply_resp = client.post("/api/v1/leave/apply", json={"leave_type": "casual", "start_date": "2026-09-01", "end_date": "2026-09-02"}, headers=headers1)
    request_id = apply_resp.json()["id"]
    resp = client.post(f"/api/v1/leave/{request_id}/cancel", headers=headers2)
    assert resp.status_code == 403


def test_hr_approve_deducts_balance_and_writes_attendance(client, db_session):
    _make_hr_user(db_session)
    employee_id, email = _make_active_employee(db_session)
    headers = _employee_headers(client, email)
    hr_headers = _hr_headers(client)
    apply_resp = client.post("/api/v1/leave/apply", json={"leave_type": "casual", "start_date": "2026-09-01", "end_date": "2026-09-03"}, headers=headers)
    request_id = apply_resp.json()["id"]
    resp = client.post(f"/api/v1/leave/{request_id}/approve", headers=hr_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    balance_resp = client.get("/api/v1/leave/balance/me", headers=headers)
    casual_balance = next(b for b in balance_resp.json() if b["leave_type"] == "casual")
    assert casual_balance["used_days"] == 3
    assert casual_balance["remaining_days"] == 9
    import uuid as uuid_module
    records = db_session.query(Attendance).filter(Attendance.employee_id == uuid_module.UUID(employee_id)).all()
    assert len(records) == 3
    assert all(r.status == AttendanceStatus.ON_LEAVE for r in records)


def test_hr_reject_does_not_deduct_balance(client, db_session):
    _make_hr_user(db_session)
    _, email = _make_active_employee(db_session)
    headers = _employee_headers(client, email)
    hr_headers = _hr_headers(client)
    apply_resp = client.post("/api/v1/leave/apply", json={"leave_type": "casual", "start_date": "2026-09-01", "end_date": "2026-09-03"}, headers=headers)
    request_id = apply_resp.json()["id"]
    resp = client.post(f"/api/v1/leave/{request_id}/reject", json={"rejection_reason": "Team is short-staffed that week"}, headers=hr_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert resp.json()["decision_note"] == "Team is short-staffed that week"
    balance_resp = client.get("/api/v1/leave/balance/me", headers=headers)
    casual_balance = next(b for b in balance_resp.json() if b["leave_type"] == "casual")
    assert casual_balance["used_days"] == 0


def test_cannot_approve_already_decided_request(client, db_session):
    _make_hr_user(db_session)
    _, email = _make_active_employee(db_session)
    headers = _employee_headers(client, email)
    hr_headers = _hr_headers(client)
    apply_resp = client.post("/api/v1/leave/apply", json={"leave_type": "casual", "start_date": "2026-09-01", "end_date": "2026-09-02"}, headers=headers)
    request_id = apply_resp.json()["id"]
    client.post(f"/api/v1/leave/{request_id}/approve", headers=hr_headers)
    resp = client.post(f"/api/v1/leave/{request_id}/approve", headers=hr_headers)
    assert resp.status_code == 400


def test_leave_apply_requires_active_employment(client, db_session):
    _make_hr_user(db_session)
    hr = db_session.query(User).filter(User.email == "hr@example.com").first()
    job = Job(title="Eng", department="Eng", description="d", created_by_id=hr.id)
    db_session.add(job)
    db_session.commit()
    user = User(email="pending@example.com", hashed_password=hash_password("supersecret1"), full_name="Pending")
    db_session.add(user)
    db_session.commit()
    employee = Employee(employee_code="EMP-000001", user_id=user.id, department="Eng", designation="Eng", date_of_joining=date(2026, 1, 1), employment_status=EmploymentStatus.PENDING_ACTIVATION)
    db_session.add(employee)
    db_session.commit()
    headers = _employee_headers(client, "pending@example.com")
    resp = client.post("/api/v1/leave/apply", json={"leave_type": "casual", "start_date": "2026-09-01", "end_date": "2026-09-02"}, headers=headers)
    assert resp.status_code == 400


def test_hr_can_list_all_leave_requests(client, db_session):
    _make_hr_user(db_session)
    _, email = _make_active_employee(db_session)
    headers = _employee_headers(client, email)
    hr_headers = _hr_headers(client)
    client.post("/api/v1/leave/apply", json={"leave_type": "casual", "start_date": "2026-09-01", "end_date": "2026-09-02"}, headers=headers)
    resp = client.get("/api/v1/leave", headers=hr_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_employee_without_leave_read_cannot_list_all(client, db_session):
    _make_hr_user(db_session)
    _, email = _make_active_employee(db_session)
    headers = _employee_headers(client, email)
    resp = client.get("/api/v1/leave", headers=headers)
    assert resp.status_code == 403
