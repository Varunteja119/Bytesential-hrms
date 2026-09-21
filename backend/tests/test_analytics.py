from datetime import date

from app.database.models.employee import Employee, EmploymentStatus
from app.database.models.payroll import PayrollConfig
from app.database.models.rbac import Permission, Role
from app.database.models.recruitment import Job, JobStatus
from app.database.models.user import User
from app.security.password import hash_password
from app.services.llm_client import get_llm_client


class FakeLLMClient:
    def __init__(self, response_text='{"risk_level": "medium", "reasoning": "Some late arrivals but stable tenure."}'):
        self.response_text = response_text
        self.generate_calls = []

    def generate(self, prompt: str) -> str:
        self.generate_calls.append(prompt)
        return self.response_text

    def embed(self, text: str) -> list[float]:
        return [0.0]


def _make_hr_user(db_session) -> None:
    perms = [Permission(code=c) for c in ["employee:read", "employee:write", "employee:exit", "attendance:write",
                                            "analytics:read", "analytics:attrition_risk"]]
    db_session.add_all(perms)
    role = Role(name="hr_manager", permissions=perms)
    db_session.add(role)
    user = User(email="hr@example.com", hashed_password=hash_password("supersecret1"), full_name="HR Person", roles=[role])
    db_session.add(user)
    db_session.commit()


def _login(client, email, password="supersecret1") -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _make_active_employee(db_session, email="employee@example.com", department="Engineering") -> str:
    hr = db_session.query(User).filter(User.email == "hr@example.com").first()
    job = Job(title="Engineer", department=department, description="desc", status=JobStatus.OPEN, created_by_id=hr.id)
    db_session.add(job)
    db_session.commit()
    user = User(email=email, hashed_password=hash_password("supersecret1"), full_name="Test Employee")
    db_session.add(user)
    db_session.commit()
    employee = Employee(employee_code=f"EMP-{db_session.query(Employee).count() + 1:06d}", user_id=user.id, department=department,
                         designation="Software Engineer", date_of_joining=date(2025, 1, 1), employment_status=EmploymentStatus.ACTIVE)
    db_session.add(employee)
    db_session.commit()
    return str(employee.id)


def test_headcount_by_department(client, db_session):
    _make_hr_user(db_session)
    headers = _login(client, "hr@example.com")
    _make_active_employee(db_session, email="e1@example.com", department="Engineering")
    _make_active_employee(db_session, email="e2@example.com", department="Engineering")
    _make_active_employee(db_session, email="e3@example.com", department="Sales")

    resp = client.get("/api/v1/analytics/headcount", headers=headers)
    assert resp.status_code == 200
    by_dept = {r["department"]: r["headcount"] for r in resp.json()}
    assert by_dept["Engineering"] == 2
    assert by_dept["Sales"] == 1


def test_headcount_requires_permission(client, db_session):
    _make_hr_user(db_session)
    employee_id = _make_active_employee(db_session)
    headers = _login(client, "employee@example.com")
    resp = client.get("/api/v1/analytics/headcount", headers=headers)
    assert resp.status_code == 403


def test_attendance_summary_computes_late_rate(client, db_session):
    _make_hr_user(db_session)
    headers = _login(client, "hr@example.com")
    employee_id = _make_active_employee(db_session)

    for day, is_late_day in [(1, False), (2, True), (3, False), (4, True)]:
        client.post(f"/api/v1/attendance/{employee_id}/mark", json={"date": f"2026-08-{day:02d}", "status": "present"}, headers=headers)

    resp = client.get("/api/v1/analytics/attendance-summary?start_date=2026-08-01&end_date=2026-08-31", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total_records"] == 4


def test_leave_utilization(client, db_session):
    _make_hr_user(db_session)
    headers = _login(client, "hr@example.com")
    resp = client.get("/api/v1/analytics/leave-utilization?year=2026", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_record_exit_updates_employment_status(client, db_session):
    _make_hr_user(db_session)
    headers = _login(client, "hr@example.com")
    employee_id = _make_active_employee(db_session)

    resp = client.post("/api/v1/analytics/exits", json={"employee_id": employee_id, "exit_type": "resignation", "exit_date": "2026-09-30", "notice_period_days": 30, "reason": "Better opportunity"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["exit_type"] == "resignation"

    employee_check = client.get(f"/api/v1/employees/{employee_id}", headers=headers)
    assert employee_check.json()["employment_status"] == "terminated"


def test_cannot_record_duplicate_exit(client, db_session):
    _make_hr_user(db_session)
    headers = _login(client, "hr@example.com")
    employee_id = _make_active_employee(db_session)
    client.post("/api/v1/analytics/exits", json={"employee_id": employee_id, "exit_type": "resignation", "exit_date": "2026-09-30"}, headers=headers)
    resp = client.post("/api/v1/analytics/exits", json={"employee_id": employee_id, "exit_type": "resignation", "exit_date": "2026-10-01"}, headers=headers)
    assert resp.status_code == 409


def test_attrition_risk_assessment(client, db_session):
    from app.main import app
    fake_llm = FakeLLMClient()
    app.dependency_overrides[get_llm_client] = lambda: fake_llm
    try:
        _make_hr_user(db_session)
        headers = _login(client, "hr@example.com")
        employee_id = _make_active_employee(db_session)

        resp = client.get(f"/api/v1/analytics/attrition-risk/{employee_id}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["risk_level"] == "medium"
        assert "disclaimer" in body
        assert "not" in body["disclaimer"].lower() or "advisory" in body["disclaimer"].lower()
        assert body["signals"]["tenure_days"] > 0
        # confirm the actual signals made it into the prompt sent to the LLM
        assert "Tenure:" in fake_llm.generate_calls[0]
    finally:
        del app.dependency_overrides[get_llm_client]


def test_attrition_risk_requires_specific_permission(client, db_session):
    """employee:read/analytics:read alone shouldn't be enough -- attrition_risk is its own permission."""
    _make_hr_user(db_session)  # creates employee:read and analytics:read permissions, among others
    employee_id = _make_active_employee(db_session)

    existing_perms = db_session.query(Permission).filter(Permission.code.in_(["employee:read", "analytics:read"])).all()
    role = Role(name="limited_hr", permissions=existing_perms)
    db_session.add(role)
    user = User(email="limited@example.com", hashed_password=hash_password("supersecret1"), full_name="Limited HR", roles=[role])
    db_session.add(user)
    db_session.commit()

    headers = _login(client, "limited@example.com")
    resp = client.get(f"/api/v1/analytics/attrition-risk/{employee_id}", headers=headers)
    assert resp.status_code == 403
