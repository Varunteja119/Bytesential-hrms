"""
Performance review workflow.

State machine: pending_self_assessment -> pending_manager_review ->
pending_ai_recommendation -> pending_hr_approval -> pending_management_approval
-> completed. Each step has its own function so the API layer can't skip
stages (e.g. can't submit a manager review before self-assessment exists).

The AI recommendation is generated once, at the pending_ai_recommendation
step, from the self-assessment + manager rating/comments -- it never runs
again automatically, and nothing about it is binding: HR and Management
each explicitly approve afterward, and either could reject/override in
final_decision_notes (a full override-the-AI-recommendation UI is a
reasonable future addition, not built here -- approval currently means
"proceed with the AI's suggestion").
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.database.models.employee import Employee, EmploymentStatus
from app.database.models.payroll import SalaryStructure
from app.database.models.performance import PerformanceCycle, PerformanceReview, RecommendedAction, ReviewStatus
from app.database.models.user import User
from app.services.llm_client import LLMClient


def generate_reviews_for_cycle(db: Session, cycle: PerformanceCycle) -> list[PerformanceReview]:
    """Creates one PerformanceReview per active employee, same batch-generation
    pattern as generate_payroll_run(). Skips employees who already have a
    review in this cycle (idempotent if called twice)."""
    active_employees = db.query(Employee).filter(Employee.employment_status == EmploymentStatus.ACTIVE).all()
    existing_employee_ids = {r.employee_id for r in cycle.reviews}

    created = []
    for employee in active_employees:
        if employee.id in existing_employee_ids:
            continue
        review = PerformanceReview(
            cycle_id=cycle.id, employee_id=employee.id,
            reviewer_id=employee.reporting_manager.user_id if employee.reporting_manager else None,
        )
        db.add(review)
        created.append(review)
    db.commit()
    for r in created:
        db.refresh(r)
    return created


def submit_self_assessment(db: Session, review: PerformanceReview, employee: Employee, self_assessment: str) -> PerformanceReview:
    if review.employee_id != employee.id:
        raise AppError("You can only submit your own self-assessment.", status_code=403)
    if review.status != ReviewStatus.PENDING_SELF_ASSESSMENT:
        raise AppError(f"Cannot submit self-assessment: review is already '{review.status.value}'.")
    review.self_assessment = self_assessment
    review.status = ReviewStatus.PENDING_MANAGER_REVIEW
    db.commit()
    db.refresh(review)
    return review


def submit_manager_review(db: Session, review: PerformanceReview, rating: int, comments: str) -> PerformanceReview:
    if review.status != ReviewStatus.PENDING_MANAGER_REVIEW:
        raise AppError(f"Cannot submit manager review: review is '{review.status.value}' (expected 'pending_manager_review').")
    if not (1 <= rating <= 5):
        raise AppError("manager_rating must be between 1 and 5.")
    review.manager_rating = rating
    review.manager_comments = comments
    review.status = ReviewStatus.PENDING_AI_RECOMMENDATION
    db.commit()
    db.refresh(review)
    return review


_RECOMMENDATION_PROMPT_TEMPLATE = """You are an HR performance-review assistant. Based on the employee's \
self-assessment and their manager's rating and comments, recommend ONE action and respond with ONLY a JSON \
object (no other text) in this exact shape:

{{"action": "promotion" | "salary_hike" | "training" | "no_change", "hike_percent": <number, 0 if not applicable>, "summary": "<2-3 sentence justification>"}}

Manager Rating (1-5): {manager_rating}
Manager Comments:
{manager_comments}

Employee Self-Assessment:
{self_assessment}

Respond with ONLY the JSON object."""


def build_recommendation_prompt(self_assessment: str, manager_rating: int, manager_comments: str) -> str:
    return _RECOMMENDATION_PROMPT_TEMPLATE.format(manager_rating=manager_rating, manager_comments=manager_comments, self_assessment=self_assessment)


def parse_recommendation_response(raw_response: str) -> tuple[RecommendedAction, float, str]:
    """Same robust-parsing approach as resume_screening.parse_screening_response --
    tolerates markdown-fenced JSON and preambles, since real LLM output isn't
    always a clean JSON string."""
    import json
    import re

    def _try_parse(text: str) -> dict | None:
        try:
            result = json.loads(text)
            return result if isinstance(result, dict) else None
        except (json.JSONDecodeError, ValueError):
            return None

    candidate_text = raw_response.strip()
    parsed = _try_parse(candidate_text)
    if parsed is None:
        match = re.search(r"\{.*\}", candidate_text, re.DOTALL)
        if match:
            parsed = _try_parse(match.group(0))
    if parsed is None:
        raise AppError(f"Could not parse an AI recommendation from the LLM response: {raw_response[:200]!r}", status_code=502)

    action_raw = parsed.get("action")
    hike_percent = parsed.get("hike_percent")
    summary = parsed.get("summary")

    try:
        action = RecommendedAction(action_raw)
    except ValueError:
        raise AppError(f"LLM returned an invalid action: {action_raw!r}. Must be one of: {[a.value for a in RecommendedAction]}", status_code=502)
    if not isinstance(hike_percent, (int, float)):
        raise AppError(f"LLM response missing a valid numeric 'hike_percent': {parsed}", status_code=502)
    if not isinstance(summary, str) or not summary.strip():
        raise AppError(f"LLM response missing a 'summary': {parsed}", status_code=502)

    hike_percent = max(0.0, float(hike_percent))
    return action, hike_percent, summary.strip()


def generate_ai_recommendation(db: Session, review: PerformanceReview, llm: LLMClient) -> PerformanceReview:
    if review.status != ReviewStatus.PENDING_AI_RECOMMENDATION:
        raise AppError(f"Cannot generate recommendation: review is '{review.status.value}' (expected 'pending_ai_recommendation').")

    prompt = build_recommendation_prompt(review.self_assessment, review.manager_rating, review.manager_comments)
    raw_response = llm.generate(prompt)
    action, hike_percent, summary = parse_recommendation_response(raw_response)

    review.ai_recommended_action = action
    review.ai_recommended_hike_percent = hike_percent
    review.ai_summary = summary
    review.status = ReviewStatus.PENDING_HR_APPROVAL
    db.commit()
    db.refresh(review)
    return review


def approve_hr(db: Session, review: PerformanceReview, approver: User) -> PerformanceReview:
    if review.status != ReviewStatus.PENDING_HR_APPROVAL:
        raise AppError(f"Cannot HR-approve: review is '{review.status.value}' (expected 'pending_hr_approval').")
    review.hr_approved_by_id = approver.id
    review.hr_approved_at = datetime.now(timezone.utc)
    review.status = ReviewStatus.PENDING_MANAGEMENT_APPROVAL
    db.commit()
    db.refresh(review)
    return review


def approve_management(db: Session, review: PerformanceReview, approver: User, final_notes: str | None) -> PerformanceReview:
    """
    On final approval, if the recommendation was a salary hike or promotion
    with a hike percent, this creates a new SalaryStructure revision --
    the same "approval writes back into the real record" pattern as
    leave approval writing ON_LEAVE into Attendance. A 'no_change' or
    'training' recommendation doesn't touch salary at all.
    """
    if review.status != ReviewStatus.PENDING_MANAGEMENT_APPROVAL:
        raise AppError(f"Cannot management-approve: review is '{review.status.value}' (expected 'pending_management_approval').")

    review.management_approved_by_id = approver.id
    review.management_approved_at = datetime.now(timezone.utc)
    review.final_decision_notes = final_notes
    review.status = ReviewStatus.COMPLETED

    if review.ai_recommended_action in (RecommendedAction.SALARY_HIKE, RecommendedAction.PROMOTION) and review.ai_recommended_hike_percent > 0:
        current = (
            db.query(SalaryStructure)
            .filter(SalaryStructure.employee_id == review.employee_id)
            .order_by(SalaryStructure.effective_from.desc())
            .first()
        )
        if current is not None:
            multiplier = 1 + (review.ai_recommended_hike_percent / 100)
            new_structure = SalaryStructure(
                employee_id=review.employee_id,
                basic=round(current.basic * multiplier, 2),
                hra=round(current.hra * multiplier, 2),
                other_allowances=round(current.other_allowances * multiplier, 2),
                effective_from=review.cycle.period_end,
            )
            db.add(new_structure)

    db.commit()
    db.refresh(review)
    return review
