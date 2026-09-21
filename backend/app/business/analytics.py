"""
Analytics and attrition risk assessment.

Two distinct kinds of function here, deliberately kept separate:

1. Aggregate analytics (headcount, attendance rate, leave utilization,
   payroll cost) -- plain SQL aggregation, no AI involved, fully
   deterministic and testable without any LLM.

2. Attrition risk assessment -- NOT a trained ML model. There's no
   historical exit dataset in this system yet to train or validate one
   against (see EmployeeExit -- it exists now, but has no data until
   real exits get recorded over time). What this actually does is ask
   the LLM to reason qualitatively over a handful of live signals
   (tenure, recent performance rating, attendance lateness, leave
   frequency) and produce an advisory risk level with reasoning. This
   is explicitly NOT a validated predictive score and should never be
   the sole basis for an employment decision -- that's stated in the
   API response itself, not just this comment, so it can't be quietly
   dropped by a frontend that doesn't read code comments.

   Deliberately exposed as a per-employee, on-demand lookup rather than
   a batch job that mass-scores the whole company -- silently ranking
   everyone's "flight risk" without their knowledge is exactly the kind
   of use that invites misuse (e.g. retaliating against someone the
   system flags). Requesting it for one employee at a time, as a named
   action a manager takes, keeps a human decision in the loop.
"""
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.database.models.attendance import Attendance
from app.database.models.employee import Employee, EmploymentStatus
from app.database.models.leave import LeaveRequest, LeaveStatus
from app.database.models.payroll import PayrollRun, Payslip
from app.database.models.performance import PerformanceReview, ReviewStatus
from app.services.llm_client import LLMClient


def get_headcount_by_department(db: Session) -> list[dict]:
    rows = (
        db.query(Employee.department, func.count(Employee.id))
        .filter(Employee.employment_status == EmploymentStatus.ACTIVE)
        .group_by(Employee.department)
        .all()
    )
    return [{"department": dept, "headcount": count} for dept, count in rows]


def get_attendance_summary(db: Session, start_date: date, end_date: date) -> dict:
    total = db.query(func.count(Attendance.id)).filter(Attendance.date >= start_date, Attendance.date <= end_date).scalar() or 0
    late = db.query(func.count(Attendance.id)).filter(Attendance.date >= start_date, Attendance.date <= end_date, Attendance.is_late.is_(True)).scalar() or 0
    return {"total_records": total, "late_count": late, "late_rate_percent": round(100 * late / total, 2) if total else 0.0}


def get_leave_utilization(db: Session, year: int) -> list[dict]:
    rows = (
        db.query(LeaveRequest.leave_type, func.sum(LeaveRequest.days_requested))
        .filter(LeaveRequest.status == LeaveStatus.APPROVED, func.extract("year", LeaveRequest.start_date) == year)
        .group_by(LeaveRequest.leave_type)
        .all()
    )
    return [{"leave_type": lt.value, "total_days_taken": int(total or 0)} for lt, total in rows]


def get_payroll_cost_trend(db: Session, year: int) -> list[dict]:
    rows = (
        db.query(PayrollRun.period_month, func.sum(Payslip.net_salary))
        .join(Payslip, Payslip.payroll_run_id == PayrollRun.id)
        .filter(PayrollRun.period_year == year)
        .group_by(PayrollRun.period_month)
        .order_by(PayrollRun.period_month)
        .all()
    )
    return [{"month": month, "total_net_salary": round(total or 0.0, 2)} for month, total in rows]


def _gather_attrition_signals(db: Session, employee: Employee) -> dict:
    today = date.today()
    tenure_days = (today - employee.date_of_joining).days

    ninety_days_ago = today - timedelta(days=90)
    recent_attendance = db.query(Attendance).filter(Attendance.employee_id == employee.id, Attendance.date >= ninety_days_ago).all()
    late_count = sum(1 for a in recent_attendance if a.is_late)

    recent_leave_days = (
        db.query(func.sum(LeaveRequest.days_requested))
        .filter(LeaveRequest.employee_id == employee.id, LeaveRequest.status == LeaveStatus.APPROVED, LeaveRequest.start_date >= ninety_days_ago)
        .scalar()
        or 0
    )

    latest_review = (
        db.query(PerformanceReview)
        .filter(PerformanceReview.employee_id == employee.id, PerformanceReview.status == ReviewStatus.COMPLETED)
        .order_by(PerformanceReview.updated_at.desc())
        .first()
    )

    return {
        "tenure_days": tenure_days,
        "late_arrivals_last_90_days": late_count,
        "leave_days_last_90_days": int(recent_leave_days),
        "latest_manager_rating": latest_review.manager_rating if latest_review else None,
        "latest_ai_recommendation": latest_review.ai_recommended_action.value if latest_review and latest_review.ai_recommended_action else None,
    }


_ATTRITION_PROMPT_TEMPLATE = """You are an HR analytics assistant providing an ADVISORY, qualitative attrition \
risk assessment -- NOT a certified prediction. Based on the signals below, respond with ONLY a JSON object \
(no other text) in this exact shape:

{{"risk_level": "low" | "medium" | "high", "reasoning": "<2-3 sentence explanation citing the specific signals>"}}

Employee signals:
- Tenure: {tenure_days} days
- Late arrivals in the last 90 days: {late_arrivals_last_90_days}
- Leave days taken in the last 90 days: {leave_days_last_90_days}
- Latest manager performance rating (1-5, or "none" if no completed review): {latest_manager_rating}
- Latest AI performance recommendation (or "none"): {latest_ai_recommendation}

Respond with ONLY the JSON object."""


def build_attrition_prompt(signals: dict) -> str:
    return _ATTRITION_PROMPT_TEMPLATE.format(**{k: (v if v is not None else "none") for k, v in signals.items()})


def parse_attrition_response(raw_response: str) -> tuple[str, str]:
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
        raise AppError(f"Could not parse an attrition assessment from the LLM response: {raw_response[:200]!r}", status_code=502)

    risk_level = parsed.get("risk_level")
    reasoning = parsed.get("reasoning")
    if risk_level not in ("low", "medium", "high"):
        raise AppError(f"LLM returned an invalid risk_level: {risk_level!r}", status_code=502)
    if not isinstance(reasoning, str) or not reasoning.strip():
        raise AppError(f"LLM response missing 'reasoning': {parsed}", status_code=502)
    return risk_level, reasoning.strip()


def assess_attrition_risk(db: Session, employee: Employee, llm: LLMClient) -> dict:
    signals = _gather_attrition_signals(db, employee)
    prompt = build_attrition_prompt(signals)
    raw_response = llm.generate(prompt)
    risk_level, reasoning = parse_attrition_response(raw_response)
    return {
        "employee_id": str(employee.id),
        "risk_level": risk_level,
        "reasoning": reasoning,
        "signals": signals,
        "disclaimer": "This is an advisory, qualitative assessment based on limited signals -- NOT a validated "
                       "predictive model. It should never be the sole basis for any employment decision.",
    }
