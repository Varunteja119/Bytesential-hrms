from datetime import date
from uuid import UUID

from app.database.models.attendance import Attendance, AttendanceStatus
from app.database.models.employee import Employee, EmploymentStatus
from app.database.models.payroll import PayrollConfig
from app.database.models.rbac import Permission, Role
from app.database.models.recruitment import Job, JobStatus
from app.database.models.user import User
from app.security.password import hash_password


def _make_config(db_session) -> None:
    config = PayrollConfig(
        pf_rate_percent=12.0, pf_wage_ceiling=15000.0, esi_rate_percent=0.75,
        esi_wage_threshold=21000.0, pt_state="Test", pt_amount=200.0, overtime_rate_multiplier=1.5,
    )
    db_session.add(config)
    db_session.commit()


def _make_hr_and_finance_users(db_session) -> None:
    payroll_read = Permission(code="payroll:read")
    db_session.add(payroll_read)

    hr_perms = [Permission(code=c) for c in ["employee:read", "employee:write", "payroll:manage", "payroll:approve_hr"]]
    db_session.add_all(hr_perms)
    hr_role = Role(name="hr", permissions=hr_perms + [payroll_read])
    db_session.add(hr_role)
    hr_user = User(email="hr@example.com", hashed_password=hash_password("supersecret1"), full_name="HR Person", roles=[hr_role])
    db_session.add(hr_user)

    finance_perms = [Permission(code=c) for c in ["payroll:approve_finance"]]
    db_session.add_all(finance_perms)
    finance_role = Role(name="finance", permissions=finance_perms + [payroll_read])
    db_session.add(finance_role)
    finance_user = User(email="finance@example.com", hashed_password=hash_password("supersecret1"), full_name="Finance Person", roles=[finance_role])
    db_session.add(finance_user)
    db_session.commit()


def _hr_headers(client) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": "hr@example.com", "password": "supersecret1"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _finance_headers(client) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": "finance@example.com", "password": "supersecret1"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _make_active_employee_with_salary(client, db_session, hr_headers, email="employee@example.com", basic=30000, hra=12000, other=3000, full_month_present=True, year=2026, month=8) -> tuple[str, str]:
    hr = db_session.query(User).filter(User.email == "hr@example.com").first()
    job = Job(title="Engineer", department="Eng", description="desc", status=JobStatus.OPEN, created_by_id=hr.id)
    db_session.add(job)
    db_session.commit()

    user = User(email=email, hashed_password=hash_password("supersecret1"), full_name="Test Employee")
    db_session.add(user)
    db_session.commit()

    employee = Employee(
        employee_code=f"EMP-{db_session.query(Employee).count() + 1:06d}",
        user_id=user.id, department="Engineering", designation="Software Engineer",
        date_of_joining=date(2026, 1, 1), employment_status=EmploymentStatus.ACTIVE,
    )
    db_session.add(employee)
    db_session.commit()

    resp = client.post("/api/v1/payroll/salary-structure", json={"employee_id": str(employee.id), "basic": basic, "hra": hra, "other_allowances": other, "effective_from": "2026-01-01"}, headers=hr_headers)
    assert resp.status_code == 201

    if full_month_present:
        import calendar
        days_in_month = calendar.monthrange(year, month)[1]
        for day in range(1, days_in_month + 1):
            db_session.add(Attendance(employee_id=employee.id, date=date(year, month, day), status=AttendanceStatus.PRESENT))
        db_session.commit()

    return str(employee.id), email


def _employee_headers(client, email) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret1"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_get_and_update_config(client, db_session):
    _make_config(db_session)
    _make_hr_and_finance_users(db_session)
    hr_headers = _hr_headers(client)

    resp = client.get("/api/v1/payroll/config", headers=hr_headers)
    assert resp.status_code == 200
    assert resp.json()["pf_rate_percent"] == 12.0

    update = client.patch("/api/v1/payroll/config", json={
        "pf_rate_percent": 12.0, "pf_wage_ceiling": 15000.0, "esi_rate_percent": 0.75,
        "esi_wage_threshold": 21000.0, "pt_state": "Karnataka", "pt_amount": 200.0, "overtime_rate_multiplier": 1.5,
    }, headers=hr_headers)
    assert update.status_code == 200
    assert update.json()["pt_state"] == "Karnataka"


def test_finance_cannot_update_config(client, db_session):
    """payroll:manage is HR-only -- finance only has approve rights, not config edit."""
    _make_config(db_session)
    _make_hr_and_finance_users(db_session)
    finance_headers = _finance_headers(client)

    resp = client.patch("/api/v1/payroll/config", json={
        "pf_rate_percent": 12.0, "pf_wage_ceiling": 15000.0, "esi_rate_percent": 0.75,
        "esi_wage_threshold": 21000.0, "pt_state": "Karnataka", "pt_amount": 200.0, "overtime_rate_multiplier": 1.5,
    }, headers=finance_headers)
    assert resp.status_code == 403


def test_generate_payroll_run_full_month(client, db_session):
    _make_config(db_session)
    _make_hr_and_finance_users(db_session)
    hr_headers = _hr_headers(client)
    _make_active_employee_with_salary(client, db_session, hr_headers)

    resp = client.post("/api/v1/payroll/runs", json={"period_year": 2026, "period_month": 8}, headers=hr_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "draft"
    assert body["payslip_count"] == 1

    payslips = client.get(f"/api/v1/payroll/runs/{body['id']}/payslips", headers=hr_headers).json()
    assert len(payslips) == 1
    assert payslips[0]["gross_salary"] == 45000.0
    assert payslips[0]["net_salary"] == 43000.0  # 45000 - 1800 PF - 0 ESI - 200 PT


def test_cannot_generate_duplicate_run_for_same_period(client, db_session):
    _make_config(db_session)
    _make_hr_and_finance_users(db_session)
    hr_headers = _hr_headers(client)
    _make_active_employee_with_salary(client, db_session, hr_headers)

    client.post("/api/v1/payroll/runs", json={"period_year": 2026, "period_month": 8}, headers=hr_headers)
    resp = client.post("/api/v1/payroll/runs", json={"period_year": 2026, "period_month": 8}, headers=hr_headers)
    assert resp.status_code == 400


def test_employee_without_salary_structure_skipped_not_failed(client, db_session):
    """An active employee with no salary structure shouldn't break the whole run."""
    _make_config(db_session)
    _make_hr_and_finance_users(db_session)
    hr_headers = _hr_headers(client)

    hr = db_session.query(User).filter(User.email == "hr@example.com").first()
    job = Job(title="Eng", department="Eng", description="d", created_by_id=hr.id)
    db_session.add(job)
    db_session.commit()
    user = User(email="nosalary@example.com", hashed_password=hash_password("supersecret1"), full_name="No Salary")
    db_session.add(user)
    db_session.commit()
    employee = Employee(employee_code="EMP-000001", user_id=user.id, department="Eng", designation="Eng", date_of_joining=date(2026, 1, 1), employment_status=EmploymentStatus.ACTIVE)
    db_session.add(employee)
    db_session.commit()

    resp = client.post("/api/v1/payroll/runs", json={"period_year": 2026, "period_month": 8}, headers=hr_headers)
    assert resp.status_code == 201
    assert resp.json()["payslip_count"] == 0  # skipped, run still succeeds


def test_full_approval_chain(client, db_session):
    _make_config(db_session)
    _make_hr_and_finance_users(db_session)
    hr_headers = _hr_headers(client)
    finance_headers = _finance_headers(client)
    _make_active_employee_with_salary(client, db_session, hr_headers)

    run_id = client.post("/api/v1/payroll/runs", json={"period_year": 2026, "period_month": 8}, headers=hr_headers).json()["id"]

    hr_approve = client.post(f"/api/v1/payroll/runs/{run_id}/approve-hr", headers=hr_headers)
    assert hr_approve.status_code == 200
    assert hr_approve.json()["status"] == "hr_approved"

    finance_approve = client.post(f"/api/v1/payroll/runs/{run_id}/approve-finance", headers=finance_headers)
    assert finance_approve.status_code == 200
    assert finance_approve.json()["status"] == "finance_approved"

    mark_paid = client.post(f"/api/v1/payroll/runs/{run_id}/mark-paid", headers=hr_headers)
    assert mark_paid.status_code == 200
    assert mark_paid.json()["status"] == "paid"
    assert mark_paid.json()["paid_at"] is not None


def test_finance_cannot_approve_before_hr(client, db_session):
    _make_config(db_session)
    _make_hr_and_finance_users(db_session)
    hr_headers = _hr_headers(client)
    finance_headers = _finance_headers(client)
    _make_active_employee_with_salary(client, db_session, hr_headers)

    run_id = client.post("/api/v1/payroll/runs", json={"period_year": 2026, "period_month": 8}, headers=hr_headers).json()["id"]

    resp = client.post(f"/api/v1/payroll/runs/{run_id}/approve-finance", headers=finance_headers)
    assert resp.status_code == 400


def test_hr_cannot_do_finance_approval(client, db_session):
    """RBAC boundary: payroll:approve_hr does not grant payroll:approve_finance."""
    _make_config(db_session)
    _make_hr_and_finance_users(db_session)
    hr_headers = _hr_headers(client)
    _make_active_employee_with_salary(client, db_session, hr_headers)

    run_id = client.post("/api/v1/payroll/runs", json={"period_year": 2026, "period_month": 8}, headers=hr_headers).json()["id"]
    client.post(f"/api/v1/payroll/runs/{run_id}/approve-hr", headers=hr_headers)

    resp = client.post(f"/api/v1/payroll/runs/{run_id}/approve-finance", headers=hr_headers)
    assert resp.status_code == 403


def test_cannot_mark_paid_before_finance_approval(client, db_session):
    _make_config(db_session)
    _make_hr_and_finance_users(db_session)
    hr_headers = _hr_headers(client)
    _make_active_employee_with_salary(client, db_session, hr_headers)

    run_id = client.post("/api/v1/payroll/runs", json={"period_year": 2026, "period_month": 8}, headers=hr_headers).json()["id"]
    client.post(f"/api/v1/payroll/runs/{run_id}/approve-hr", headers=hr_headers)

    resp = client.post(f"/api/v1/payroll/runs/{run_id}/mark-paid", headers=hr_headers)
    assert resp.status_code == 400


def test_update_payslip_recomputes_net_salary(client, db_session):
    _make_config(db_session)
    _make_hr_and_finance_users(db_session)
    hr_headers = _hr_headers(client)
    _make_active_employee_with_salary(client, db_session, hr_headers)

    run_id = client.post("/api/v1/payroll/runs", json={"period_year": 2026, "period_month": 8}, headers=hr_headers).json()["id"]
    payslip = client.get(f"/api/v1/payroll/runs/{run_id}/payslips", headers=hr_headers).json()[0]

    resp = client.patch(f"/api/v1/payroll/payslips/{payslip['id']}", json={"tds_amount": 2000, "bonus_amount": 5000}, headers=hr_headers)
    assert resp.status_code == 200
    # net = 45000 (gross) + 5000 (bonus) - 1800 (PF) - 0 (ESI) - 200 (PT) - 2000 (TDS) = 46000
    assert resp.json()["net_salary"] == 46000.0


def test_cannot_adjust_payslip_after_hr_approval(client, db_session):
    _make_config(db_session)
    _make_hr_and_finance_users(db_session)
    hr_headers = _hr_headers(client)
    _make_active_employee_with_salary(client, db_session, hr_headers)

    run_id = client.post("/api/v1/payroll/runs", json={"period_year": 2026, "period_month": 8}, headers=hr_headers).json()["id"]
    payslip = client.get(f"/api/v1/payroll/runs/{run_id}/payslips", headers=hr_headers).json()[0]
    client.post(f"/api/v1/payroll/runs/{run_id}/approve-hr", headers=hr_headers)

    resp = client.patch(f"/api/v1/payroll/payslips/{payslip['id']}", json={"tds_amount": 2000}, headers=hr_headers)
    assert resp.status_code == 400


def test_employee_can_view_own_payslips(client, db_session):
    _make_config(db_session)
    _make_hr_and_finance_users(db_session)
    hr_headers = _hr_headers(client)
    _, email = _make_active_employee_with_salary(client, db_session, hr_headers)

    client.post("/api/v1/payroll/runs", json={"period_year": 2026, "period_month": 8}, headers=hr_headers)

    employee_headers = _employee_headers(client, email)
    resp = client.get("/api/v1/payroll/payslips/me", headers=employee_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_lop_reduces_net_salary(client, db_session):
    """5 unmarked/LOP days out of 31 in August 2026 should prorate earnings down."""
    _make_config(db_session)
    _make_hr_and_finance_users(db_session)
    hr_headers = _hr_headers(client)
    employee_id, email = _make_active_employee_with_salary(client, db_session, hr_headers, full_month_present=False)

    # mark only 26 of 31 days present (5 LOP)
    for day in range(1, 27):
        db_session.add(Attendance(employee_id=UUID(employee_id), date=date(2026, 8, day), status=AttendanceStatus.PRESENT))
    db_session.commit()

    resp = client.post("/api/v1/payroll/runs", json={"period_year": 2026, "period_month": 8}, headers=hr_headers)
    run_id = resp.json()["id"]
    payslip = client.get(f"/api/v1/payroll/runs/{run_id}/payslips", headers=hr_headers).json()[0]

    assert payslip["days_lop"] == 5
    assert payslip["gross_salary"] < 45000.0  # prorated down from full month
