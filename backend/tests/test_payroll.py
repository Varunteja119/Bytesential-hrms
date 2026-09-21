from datetime import date

from app.database.models.employee import Employee, EmploymentStatus
from app.database.models.payroll import PayrollConfig
from app.database.models.rbac import Permission, Role
from app.database.models.recruitment import Job, JobStatus
from app.database.models.user import User
from app.security.password import hash_password


def _make_users(db_session) -> None:
    payroll_read = Permission(code="payroll:read")
    payroll_manage = Permission(code="payroll:manage")
    payroll_approve_hr = Permission(code="payroll:approve_hr")
    employee_write = Permission(code="employee:write")
    attendance_write = Permission(code="attendance:write")
    payroll_approve_finance = Permission(code="payroll:approve_finance")
    db_session.add_all([payroll_read, payroll_manage, payroll_approve_hr, employee_write, attendance_write, payroll_approve_finance])

    hr_role = Role(name="hr_manager", permissions=[payroll_read, payroll_manage, payroll_approve_hr, employee_write, attendance_write])
    db_session.add(hr_role)

    finance_role = Role(name="finance_manager", permissions=[payroll_read, payroll_approve_finance])
    db_session.add(finance_role)

    hr_user = User(email="hr@example.com", hashed_password=hash_password("supersecret1"), full_name="HR", roles=[hr_role])
    db_session.add(hr_user)
    finance_user = User(email="finance@example.com", hashed_password=hash_password("supersecret1"), full_name="Finance", roles=[finance_role])
    db_session.add(finance_user)

    config = PayrollConfig(pf_rate_percent=12.0, pf_wage_ceiling=15000.0, esi_rate_percent=0.75, esi_wage_threshold=21000.0, pt_state="Test", pt_amount=200.0, overtime_rate_multiplier=1.5)
    db_session.add(config)
    db_session.commit()


def _login(client, email, password="supersecret1") -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _make_active_employee(db_session, email="employee@example.com") -> str:
    hr = db_session.query(User).filter(User.email == "hr@example.com").first()
    job = Job(title="Engineer", department="Eng", description="desc", status=JobStatus.OPEN, created_by_id=hr.id)
    db_session.add(job)
    db_session.commit()
    user = User(email=email, hashed_password=hash_password("supersecret1"), full_name="Test Employee")
    db_session.add(user)
    db_session.commit()
    employee = Employee(employee_code=f"EMP-{db_session.query(Employee).count() + 1:06d}", user_id=user.id, department="Engineering",
                         designation="Software Engineer", date_of_joining=date(2026, 1, 1), employment_status=EmploymentStatus.ACTIVE)
    db_session.add(employee)
    db_session.commit()
    return str(employee.id)


def test_get_config(client, db_session):
    _make_users(db_session)
    headers = _login(client, "hr@example.com")
    resp = client.get("/api/v1/payroll/config", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["pf_rate_percent"] == 12.0


def test_update_config(client, db_session):
    _make_users(db_session)
    headers = _login(client, "hr@example.com")
    resp = client.patch("/api/v1/payroll/config", json={"pf_rate_percent": 12.0, "pf_wage_ceiling": 15000.0, "esi_rate_percent": 0.75, "esi_wage_threshold": 21000.0, "pt_state": "Karnataka", "pt_amount": 200.0, "overtime_rate_multiplier": 1.5}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["pt_state"] == "Karnataka"


def test_set_salary_structure(client, db_session):
    _make_users(db_session)
    headers = _login(client, "hr@example.com")
    employee_id = _make_active_employee(db_session)
    resp = client.post("/api/v1/payroll/salary-structure", json={"employee_id": employee_id, "basic": 30000, "hra": 12000, "other_allowances": 3000, "effective_from": "2026-01-01"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["basic"] == 30000.0


def test_create_payroll_run_computes_payslips(client, db_session):
    _make_users(db_session)
    headers = _login(client, "hr@example.com")
    employee_id = _make_active_employee(db_session)
    client.post("/api/v1/payroll/salary-structure", json={"employee_id": employee_id, "basic": 30000, "hra": 12000, "other_allowances": 3000, "effective_from": "2026-01-01"}, headers=headers)

    run_resp = client.post("/api/v1/payroll/runs", json={"period_year": 2026, "period_month": 8}, headers=headers)
    assert run_resp.status_code == 201
    assert run_resp.json()["status"] == "draft"
    run_id = run_resp.json()["id"]

    payslips = client.get(f"/api/v1/payroll/runs/{run_id}/payslips", headers=headers).json()
    assert len(payslips) == 1
    payslip = payslips[0]
    assert payslip["days_lop"] == 31  # no attendance marked at all -> full month LOP
    assert payslip["gross_salary"] == 0.0  # fully prorated to zero since payable_days = 0
    assert payslip["pf_deduction"] == 0.0  # PF is computed on the PRORATED basic, which is also 0 here -- correct, not a bug
    assert payslip["net_salary"] == 0.0


def test_payroll_run_with_full_attendance_computes_correct_deductions(client, db_session):
    _make_users(db_session)
    headers = _login(client, "hr@example.com")
    employee_id = _make_active_employee(db_session)
    client.post("/api/v1/payroll/salary-structure", json={"employee_id": employee_id, "basic": 30000, "hra": 12000, "other_allowances": 3000, "effective_from": "2026-01-01"}, headers=headers)

    # Mark every day in August 2026 (31 days) as present via HR manual attendance marking
    for day in range(1, 32):
        client.post(f"/api/v1/attendance/{employee_id}/mark", json={"date": f"2026-08-{day:02d}", "status": "present"}, headers=headers)

    run_id = client.post("/api/v1/payroll/runs", json={"period_year": 2026, "period_month": 8}, headers=headers).json()["id"]
    payslip = client.get(f"/api/v1/payroll/runs/{run_id}/payslips", headers=headers).json()[0]

    assert payslip["days_lop"] == 0
    assert payslip["gross_salary"] == 45000.0  # full 30000+12000+3000, no proration
    assert payslip["pf_deduction"] == 1800.0  # min(30000, 15000) * 12%
    assert payslip["esi_deduction"] == 0.0  # gross 45000 > 21000 threshold -> no ESI
    assert payslip["pt_deduction"] == 200.0
    assert payslip["net_salary"] == 43000.0  # 45000 - 1800 - 0 - 200


def test_cannot_create_duplicate_payroll_run(client, db_session):
    _make_users(db_session)
    headers = _login(client, "hr@example.com")
    client.post("/api/v1/payroll/runs", json={"period_year": 2026, "period_month": 8}, headers=headers)
    resp = client.post("/api/v1/payroll/runs", json={"period_year": 2026, "period_month": 8}, headers=headers)
    assert resp.status_code == 400


def test_full_approval_chain(client, db_session):
    _make_users(db_session)
    hr_headers = _login(client, "hr@example.com")
    finance_headers = _login(client, "finance@example.com")
    employee_id = _make_active_employee(db_session)
    client.post("/api/v1/payroll/salary-structure", json={"employee_id": employee_id, "basic": 30000, "hra": 12000, "other_allowances": 3000, "effective_from": "2026-01-01"}, headers=hr_headers)
    run_id = client.post("/api/v1/payroll/runs", json={"period_year": 2026, "period_month": 8}, headers=hr_headers).json()["id"]

    # finance can't approve before HR
    blocked = client.post(f"/api/v1/payroll/runs/{run_id}/approve-finance", headers=finance_headers)
    assert blocked.status_code == 400

    hr_approve = client.post(f"/api/v1/payroll/runs/{run_id}/approve-hr", headers=hr_headers)
    assert hr_approve.status_code == 200
    assert hr_approve.json()["status"] == "hr_approved"

    finance_approve = client.post(f"/api/v1/payroll/runs/{run_id}/approve-finance", headers=finance_headers)
    assert finance_approve.status_code == 200
    assert finance_approve.json()["status"] == "finance_approved"

    paid = client.post(f"/api/v1/payroll/runs/{run_id}/mark-paid", headers=hr_headers)
    assert paid.status_code == 200
    assert paid.json()["status"] == "paid"


def test_hr_cannot_do_finance_approval(client, db_session):
    _make_users(db_session)
    hr_headers = _login(client, "hr@example.com")
    run_id = client.post("/api/v1/payroll/runs", json={"period_year": 2026, "period_month": 8}, headers=hr_headers).json()["id"]
    client.post(f"/api/v1/payroll/runs/{run_id}/approve-hr", headers=hr_headers)
    resp = client.post(f"/api/v1/payroll/runs/{run_id}/approve-finance", headers=hr_headers)
    assert resp.status_code == 403


def test_payslip_locked_after_hr_approval(client, db_session):
    _make_users(db_session)
    hr_headers = _login(client, "hr@example.com")
    employee_id = _make_active_employee(db_session)
    client.post("/api/v1/payroll/salary-structure", json={"employee_id": employee_id, "basic": 30000, "hra": 12000, "other_allowances": 3000, "effective_from": "2026-01-01"}, headers=hr_headers)
    run_id = client.post("/api/v1/payroll/runs", json={"period_year": 2026, "period_month": 8}, headers=hr_headers).json()["id"]
    payslip_id = client.get(f"/api/v1/payroll/runs/{run_id}/payslips", headers=hr_headers).json()[0]["id"]

    # can adjust while draft
    adjust = client.patch(f"/api/v1/payroll/payslips/{payslip_id}", json={"bonus_amount": 5000}, headers=hr_headers)
    assert adjust.status_code == 200

    client.post(f"/api/v1/payroll/runs/{run_id}/approve-hr", headers=hr_headers)

    # locked after approval
    locked = client.patch(f"/api/v1/payroll/payslips/{payslip_id}", json={"bonus_amount": 9999}, headers=hr_headers)
    assert locked.status_code == 400
