from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from app.database.models.attendance import Attendance, AttendanceStatus
from app.database.models.employee import Employee, EmploymentStatus
from app.database.models.rbac import Permission, Role
from app.database.models.recruitment import Candidate, CandidateStatus, Job, JobStatus
from app.database.models.user import User
from app.security.password import hash_password


def _make_hr_user(db_session) -> None:
    perms = [Permission(code=c) for c in ["employee:read", "employee:write", "attendance:read", "attendance:write"]]
    db_session.add_all(perms)
    role = Role(name="hr", permissions=perms)
    db_session.add(role)
    user = User(email="hr@example.com", hashed_password=hash_password("supersecret1"), full_name="HR Person", roles=[role])
    db_session.add(user)
    db_session.commit()


def _hr_headers(client) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": "hr@example.com", "password": "supersecret1"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _make_active_employee(db_session, email="employee@example.com", password="supersecret1") -> tuple[str, str]:
    """Returns (employee_id, user_email). Bypasses the full provisioning flow -- directly
    creates an ACTIVE employee since that's the precondition attendance tests care about."""
    hr = db_session.query(User).filter(User.email == "hr@example.com").first()
    job = Job(title="Engineer", department="Eng", description="desc", status=JobStatus.OPEN, created_by_id=hr.id)
    db_session.add(job)
    db_session.commit()

    user = User(email=email, hashed_password=hash_password(password), full_name="Test Employee")
    db_session.add(user)
    db_session.commit()

    employee = Employee(
        employee_code=f"EMP-{db_session.query(Employee).count() + 1:06d}",
        user_id=user.id,
        department="Engineering",
        designation="Software Engineer",
        date_of_joining=date(2026, 1, 1),
        employment_status=EmploymentStatus.ACTIVE,
    )
    db_session.add(employee)
    db_session.commit()
    return str(employee.id), email


def _employee_headers(client, email, password="supersecret1") -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_check_in_requires_active_employment_status(client, db_session):
    _make_hr_user(db_session)
    user = User(email="pending@example.com", hashed_password=hash_password("supersecret1"), full_name="Pending Hire")
    db_session.add(user)
    db_session.commit()
    hr = db_session.query(User).filter(User.email == "hr@example.com").first()
    job = Job(title="Eng", department="Eng", description="d", created_by_id=hr.id)
    db_session.add(job)
    db_session.commit()
    employee = Employee(
        employee_code="EMP-000001", user_id=user.id, department="Eng", designation="Eng",
        date_of_joining=date(2026, 1, 1), employment_status=EmploymentStatus.PENDING_ACTIVATION,
    )
    db_session.add(employee)
    db_session.commit()

    headers = _employee_headers(client, "pending@example.com")
    resp = client.post("/api/v1/attendance/check-in", headers=headers)
    assert resp.status_code == 400
    assert "active" in resp.json()["error"]["message"].lower()


def test_check_in_success(client, db_session):
    _make_hr_user(db_session)
    _, email = _make_active_employee(db_session)
    headers = _employee_headers(client, email)

    resp = client.post("/api/v1/attendance/check-in", headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["check_in_time"] is not None
    assert body["check_out_time"] is None
    assert body["status"] == "present"


def test_double_check_in_rejected(client, db_session):
    _make_hr_user(db_session)
    _, email = _make_active_employee(db_session)
    headers = _employee_headers(client, email)

    client.post("/api/v1/attendance/check-in", headers=headers)
    resp = client.post("/api/v1/attendance/check-in", headers=headers)
    assert resp.status_code == 400
    assert "already checked in" in resp.json()["error"]["message"].lower()


def test_check_out_without_check_in_rejected(client, db_session):
    _make_hr_user(db_session)
    _, email = _make_active_employee(db_session)
    headers = _employee_headers(client, email)

    resp = client.post("/api/v1/attendance/check-out", headers=headers)
    assert resp.status_code == 400
    assert "must check in" in resp.json()["error"]["message"].lower()


def test_check_out_computes_work_hours(client, db_session):
    _make_hr_user(db_session)
    employee_id, email = _make_active_employee(db_session)
    headers = _employee_headers(client, email)

    client.post("/api/v1/attendance/check-in", headers=headers)

    # manipulate the check-in time directly to simulate a full 8-hour day
    # (avoids a real 8-hour sleep in the test)
    record = db_session.query(Attendance).filter(Attendance.employee_id == UUID(employee_id)).first()
    record.check_in_time = datetime.now(timezone.utc) - timedelta(hours=8)
    db_session.commit()

    resp = client.post("/api/v1/attendance/check-out", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["work_hours"] == 8.0
    assert body["status"] == "present"


def test_check_out_under_half_day_threshold_marks_half_day(client, db_session):
    _make_hr_user(db_session)
    employee_id, email = _make_active_employee(db_session)
    headers = _employee_headers(client, email)

    client.post("/api/v1/attendance/check-in", headers=headers)
    record = db_session.query(Attendance).filter(Attendance.employee_id == UUID(employee_id)).first()
    record.check_in_time = datetime.now(timezone.utc) - timedelta(hours=2)  # under the 4.0 threshold
    db_session.commit()

    resp = client.post("/api/v1/attendance/check-out", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "half_day"


def test_double_check_out_rejected(client, db_session):
    _make_hr_user(db_session)
    _, email = _make_active_employee(db_session)
    headers = _employee_headers(client, email)

    client.post("/api/v1/attendance/check-in", headers=headers)
    client.post("/api/v1/attendance/check-out", headers=headers)
    resp = client.post("/api/v1/attendance/check-out", headers=headers)
    assert resp.status_code == 400
    assert "already checked out" in resp.json()["error"]["message"].lower()


def test_employee_can_view_own_attendance(client, db_session):
    _make_hr_user(db_session)
    _, email = _make_active_employee(db_session)
    headers = _employee_headers(client, email)

    client.post("/api/v1/attendance/check-in", headers=headers)
    resp = client.get("/api/v1/attendance/me", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_employee_cannot_view_another_employees_attendance(client, db_session):
    _make_hr_user(db_session)
    employee_id_1, email1 = _make_active_employee(db_session, email="emp1@example.com")
    employee_id_2, email2 = _make_active_employee(db_session, email="emp2@example.com")
    headers1 = _employee_headers(client, email1)

    resp = client.get(f"/api/v1/attendance/{employee_id_2}", headers=headers1)
    assert resp.status_code == 403


def test_hr_can_view_any_employee_attendance(client, db_session):
    _make_hr_user(db_session)
    employee_id, email = _make_active_employee(db_session)
    employee_headers = _employee_headers(client, email)
    client.post("/api/v1/attendance/check-in", headers=employee_headers)

    hr_headers = _hr_headers(client)
    resp = client.get(f"/api/v1/attendance/{employee_id}", headers=hr_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_hr_manual_mark_creates_holiday_record(client, db_session):
    _make_hr_user(db_session)
    employee_id, _ = _make_active_employee(db_session)
    hr_headers = _hr_headers(client)

    resp = client.post(
        f"/api/v1/attendance/{employee_id}/mark",
        json={"date": "2026-08-15", "status": "holiday", "notes": "Independence Day"},
        headers=hr_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "holiday"
    assert resp.json()["notes"] == "Independence Day"


def test_hr_manual_mark_requires_permission(client, db_session):
    _make_hr_user(db_session)
    employee_id, email = _make_active_employee(db_session)
    employee_headers = _employee_headers(client, email)

    resp = client.post(
        f"/api/v1/attendance/{employee_id}/mark",
        json={"date": "2026-08-15", "status": "holiday"},
        headers=employee_headers,
    )
    assert resp.status_code == 403


def test_attendance_date_filter(client, db_session):
    _make_hr_user(db_session)
    employee_id, email = _make_active_employee(db_session)
    headers = _employee_headers(client, email)
    hr_headers = _hr_headers(client)

    client.post(f"/api/v1/attendance/{employee_id}/mark", json={"date": "2026-08-01", "status": "present"}, headers=hr_headers)
    client.post(f"/api/v1/attendance/{employee_id}/mark", json={"date": "2026-08-15", "status": "present"}, headers=hr_headers)

    resp = client.get("/api/v1/attendance/me?start_date=2026-08-10", headers=headers)
    assert resp.status_code == 200
    dates = [r["date"] for r in resp.json()]
    assert "2026-08-15" in dates
    assert "2026-08-01" not in dates
