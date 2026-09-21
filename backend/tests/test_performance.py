from datetime import date

from app.database.models.employee import Employee, EmploymentStatus
from app.database.models.payroll import SalaryStructure
from app.database.models.rbac import Permission, Role
from app.database.models.recruitment import Job, JobStatus
from app.database.models.user import User
from app.security.password import hash_password
from app.services.llm_client import get_llm_client


class FakeLLMClient:
    def __init__(self, response_text='{"action": "salary_hike", "hike_percent": 10, "summary": "Strong performer, exceeded goals."}'):
        self.response_text = response_text
        self.generate_calls = []

    def generate(self, prompt: str) -> str:
        self.generate_calls.append(prompt)
        return self.response_text

    def embed(self, text: str) -> list[float]:
        return [0.0]


def _make_hr_and_management_users(db_session) -> None:
    perf_read = Permission(code="performance:read")
    perf_manage = Permission(code="performance:manage")
    perf_review = Permission(code="performance:review")
    emp_write = Permission(code="employee:write")
    perf_approve_mgmt = Permission(code="performance:approve_management")
    db_session.add_all([perf_read, perf_manage, perf_review, emp_write, perf_approve_mgmt])

    hr_role = Role(name="hr_manager", permissions=[perf_read, perf_manage, perf_review, emp_write])
    db_session.add(hr_role)

    mgmt_role = Role(name="management", permissions=[perf_read, perf_approve_mgmt])
    db_session.add(mgmt_role)

    hr_user = User(email="hr@example.com", hashed_password=hash_password("supersecret1"), full_name="HR Person", roles=[hr_role])
    db_session.add(hr_user)
    mgmt_user = User(email="mgmt@example.com", hashed_password=hash_password("supersecret1"), full_name="Management Person", roles=[mgmt_role])
    db_session.add(mgmt_user)
    db_session.commit()


def _login(client, email, password="supersecret1") -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _make_active_employee(db_session, email="employee@example.com") -> tuple[str, str]:
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
    db_session.refresh(employee)
    db_session.add(SalaryStructure(employee_id=employee.id, basic=30000, hra=12000, other_allowances=3000, effective_from=date(2026, 1, 1)))
    db_session.commit()
    return str(employee.id), email


def _create_cycle(client, hr_headers) -> str:
    resp = client.post("/api/v1/performance/cycles", json={"name": "Q3 2026", "period_start": "2026-07-01", "period_end": "2026-09-30"}, headers=hr_headers)
    assert resp.status_code == 201
    return resp.json()["id"]


def test_create_cycle_and_generate_reviews(client, db_session):
    _make_hr_and_management_users(db_session)
    hr_headers = _login(client, "hr@example.com")
    _make_active_employee(db_session)

    cycle_id = _create_cycle(client, hr_headers)
    resp = client.post(f"/api/v1/performance/cycles/{cycle_id}/generate-reviews", headers=hr_headers)
    assert resp.status_code == 200
    reviews = resp.json()
    assert len(reviews) == 1
    assert reviews[0]["status"] == "pending_self_assessment"


def test_generate_reviews_idempotent(client, db_session):
    _make_hr_and_management_users(db_session)
    hr_headers = _login(client, "hr@example.com")
    _make_active_employee(db_session)
    cycle_id = _create_cycle(client, hr_headers)

    first = client.post(f"/api/v1/performance/cycles/{cycle_id}/generate-reviews", headers=hr_headers)
    assert len(first.json()) == 1
    second = client.post(f"/api/v1/performance/cycles/{cycle_id}/generate-reviews", headers=hr_headers)
    assert len(second.json()) == 0  # already has a review, skipped


def test_employee_cannot_skip_to_manager_review(client, db_session):
    _make_hr_and_management_users(db_session)
    hr_headers = _login(client, "hr@example.com")
    employee_id, email = _make_active_employee(db_session)
    cycle_id = _create_cycle(client, hr_headers)
    client.post(f"/api/v1/performance/cycles/{cycle_id}/generate-reviews", headers=hr_headers)

    reviews = client.get(f"/api/v1/performance/cycles/{cycle_id}/reviews", headers=hr_headers).json()
    review_id = reviews[0]["id"]

    emp_headers = _login(client, email)
    resp = client.post(f"/api/v1/performance/reviews/{review_id}/manager-review", json={"manager_rating": 5, "manager_comments": "great"}, headers=hr_headers)
    assert resp.status_code == 400  # still pending_self_assessment


def test_full_performance_workflow_with_salary_hike(client, db_session):
    from app.main import app

    fake_llm = FakeLLMClient()
    app.dependency_overrides[get_llm_client] = lambda: fake_llm
    try:
        _make_hr_and_management_users(db_session)
        hr_headers = _login(client, "hr@example.com")
        mgmt_headers = _login(client, "mgmt@example.com")
        employee_id, email = _make_active_employee(db_session)
        emp_headers = _login(client, email)

        cycle_id = _create_cycle(client, hr_headers)
        client.post(f"/api/v1/performance/cycles/{cycle_id}/generate-reviews", headers=hr_headers)
        review_id = client.get(f"/api/v1/performance/cycles/{cycle_id}/reviews", headers=hr_headers).json()[0]["id"]

        # 1. self-assessment
        r1 = client.post(f"/api/v1/performance/reviews/{review_id}/self-assessment", json={"self_assessment": "Exceeded all quarterly goals."}, headers=emp_headers)
        assert r1.status_code == 200
        assert r1.json()["status"] == "pending_manager_review"

        # can't self-assess twice
        r1b = client.post(f"/api/v1/performance/reviews/{review_id}/self-assessment", json={"self_assessment": "again"}, headers=emp_headers)
        assert r1b.status_code == 400

        # 2. manager review
        r2 = client.post(f"/api/v1/performance/reviews/{review_id}/manager-review", json={"manager_rating": 5, "manager_comments": "Outstanding quarter."}, headers=hr_headers)
        assert r2.status_code == 200
        assert r2.json()["status"] == "pending_ai_recommendation"

        # 3. AI recommendation
        r3 = client.post(f"/api/v1/performance/reviews/{review_id}/generate-recommendation", headers=hr_headers)
        assert r3.status_code == 200
        assert r3.json()["ai_recommended_action"] == "salary_hike"
        assert r3.json()["ai_recommended_hike_percent"] == 10.0
        assert r3.json()["status"] == "pending_hr_approval"
        # confirm the prompt actually included the real self-assessment and manager comments
        assert "Exceeded all quarterly goals" in fake_llm.generate_calls[0]
        assert "Outstanding quarter" in fake_llm.generate_calls[0]

        # 4. HR approval
        r4 = client.post(f"/api/v1/performance/reviews/{review_id}/approve-hr", headers=hr_headers)
        assert r4.status_code == 200
        assert r4.json()["status"] == "pending_management_approval"

        # management approval requires the RIGHT permission -- HR alone can't do it
        r4b = client.post(f"/api/v1/performance/reviews/{review_id}/approve-management", json={"final_notes": "x"}, headers=hr_headers)
        assert r4b.status_code == 403

        # 5. management approval
        r5 = client.post(f"/api/v1/performance/reviews/{review_id}/approve-management", json={"final_notes": "Well deserved."}, headers=mgmt_headers)
        assert r5.status_code == 200
        assert r5.json()["status"] == "completed"

        # 6. confirm the salary hike actually wrote back into SalaryStructure
        structures = db_session.query(SalaryStructure).filter(SalaryStructure.employee_id == uuid_str_to_uuid(employee_id)).order_by(SalaryStructure.effective_from).all()
        assert len(structures) == 2
        assert structures[1].basic == 33000.0  # 30000 * 1.10
        assert structures[1].effective_from == date(2026, 9, 30)
    finally:
        del app.dependency_overrides[get_llm_client]


def test_no_change_recommendation_does_not_touch_salary(client, db_session):
    from app.main import app

    fake_llm = FakeLLMClient(response_text='{"action": "no_change", "hike_percent": 0, "summary": "Met expectations."}')
    app.dependency_overrides[get_llm_client] = lambda: fake_llm
    try:
        _make_hr_and_management_users(db_session)
        hr_headers = _login(client, "hr@example.com")
        mgmt_headers = _login(client, "mgmt@example.com")
        employee_id, email = _make_active_employee(db_session)
        emp_headers = _login(client, email)

        cycle_id = _create_cycle(client, hr_headers)
        client.post(f"/api/v1/performance/cycles/{cycle_id}/generate-reviews", headers=hr_headers)
        review_id = client.get(f"/api/v1/performance/cycles/{cycle_id}/reviews", headers=hr_headers).json()[0]["id"]

        client.post(f"/api/v1/performance/reviews/{review_id}/self-assessment", json={"self_assessment": "Steady quarter."}, headers=emp_headers)
        client.post(f"/api/v1/performance/reviews/{review_id}/manager-review", json={"manager_rating": 3, "manager_comments": "Solid."}, headers=hr_headers)
        client.post(f"/api/v1/performance/reviews/{review_id}/generate-recommendation", headers=hr_headers)
        client.post(f"/api/v1/performance/reviews/{review_id}/approve-hr", headers=hr_headers)
        client.post(f"/api/v1/performance/reviews/{review_id}/approve-management", json={"final_notes": "Agreed."}, headers=mgmt_headers)

        structures = db_session.query(SalaryStructure).filter(SalaryStructure.employee_id == uuid_str_to_uuid(employee_id)).all()
        assert len(structures) == 1  # only the original -- no_change created nothing new
    finally:
        del app.dependency_overrides[get_llm_client]


def test_ai_recommendation_handles_messy_llm_response(client, db_session):
    from app.main import app

    fake_llm = FakeLLMClient(response_text='```json\n{"action": "training", "hike_percent": 0, "summary": "Needs upskilling in X."}\n```')
    app.dependency_overrides[get_llm_client] = lambda: fake_llm
    try:
        _make_hr_and_management_users(db_session)
        hr_headers = _login(client, "hr@example.com")
        employee_id, email = _make_active_employee(db_session)
        emp_headers = _login(client, email)

        cycle_id = _create_cycle(client, hr_headers)
        client.post(f"/api/v1/performance/cycles/{cycle_id}/generate-reviews", headers=hr_headers)
        review_id = client.get(f"/api/v1/performance/cycles/{cycle_id}/reviews", headers=hr_headers).json()[0]["id"]

        client.post(f"/api/v1/performance/reviews/{review_id}/self-assessment", json={"self_assessment": "x"}, headers=emp_headers)
        client.post(f"/api/v1/performance/reviews/{review_id}/manager-review", json={"manager_rating": 2, "manager_comments": "y"}, headers=hr_headers)
        resp = client.post(f"/api/v1/performance/reviews/{review_id}/generate-recommendation", headers=hr_headers)
        assert resp.status_code == 200
        assert resp.json()["ai_recommended_action"] == "training"
    finally:
        del app.dependency_overrides[get_llm_client]


def uuid_str_to_uuid(s: str):
    import uuid
    return uuid.UUID(s)
