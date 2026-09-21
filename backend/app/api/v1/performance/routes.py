import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.business.performance import (
    approve_hr, approve_management, generate_ai_recommendation, generate_reviews_for_cycle,
    submit_manager_review, submit_self_assessment,
)
from app.database.connection.database import get_db
from app.database.models.employee import Employee
from app.database.models.performance import PerformanceCycle, PerformanceReview
from app.database.models.user import User
from app.database.schemas.performance import (
    CycleCreate, CycleOut, ManagementApprovalRequest, ManagerReviewRequest, ReviewOut, SelfAssessmentRequest,
)
from app.dependencies.auth import get_current_user, require_permission
from app.services.llm_client import LLMClient, get_llm_client

router = APIRouter(prefix="/performance", tags=["performance"])


def _get_cycle_or_404(db: Session, cycle_id: uuid.UUID) -> PerformanceCycle:
    cycle = db.get(PerformanceCycle, cycle_id)
    if cycle is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Performance cycle not found")
    return cycle


def _get_review_or_404(db: Session, review_id: uuid.UUID) -> PerformanceReview:
    review = db.get(PerformanceReview, review_id)
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Performance review not found")
    return review


def _get_own_employee_record(db: Session, user: User) -> Employee:
    employee = db.query(Employee).filter(Employee.user_id == user.id).first()
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No employee record linked to your account")
    return employee


# --- Cycles ---

@router.post("/cycles", response_model=CycleOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("performance:manage"))])
def create_cycle(payload: CycleCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cycle = PerformanceCycle(**payload.model_dump(), created_by_id=current_user.id)
    db.add(cycle)
    db.commit()
    db.refresh(cycle)
    return CycleOut.from_orm_cycle(cycle)


@router.get("/cycles", response_model=list[CycleOut], dependencies=[Depends(require_permission("performance:read"))])
def list_cycles(db: Session = Depends(get_db)):
    return [CycleOut.from_orm_cycle(c) for c in db.query(PerformanceCycle).all()]


@router.post("/cycles/{cycle_id}/generate-reviews", response_model=list[ReviewOut], dependencies=[Depends(require_permission("performance:manage"))])
def generate_reviews(cycle_id: uuid.UUID, db: Session = Depends(get_db)):
    """Creates one review per active employee -- same batch-generation pattern as payroll runs."""
    cycle = _get_cycle_or_404(db, cycle_id)
    created = generate_reviews_for_cycle(db, cycle)
    return [ReviewOut.model_validate(r) for r in created]


@router.get("/cycles/{cycle_id}/reviews", response_model=list[ReviewOut], dependencies=[Depends(require_permission("performance:read"))])
def list_cycle_reviews(cycle_id: uuid.UUID, db: Session = Depends(get_db)):
    _get_cycle_or_404(db, cycle_id)
    reviews = db.query(PerformanceReview).filter(PerformanceReview.cycle_id == cycle_id).all()
    return [ReviewOut.model_validate(r) for r in reviews]


# --- Employee self-service ---

@router.get("/reviews/me", response_model=list[ReviewOut])
def get_my_reviews(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    employee = _get_own_employee_record(db, current_user)
    reviews = db.query(PerformanceReview).filter(PerformanceReview.employee_id == employee.id).all()
    return [ReviewOut.model_validate(r) for r in reviews]


@router.post("/reviews/{review_id}/self-assessment", response_model=ReviewOut)
def submit_self_assessment_route(review_id: uuid.UUID, payload: SelfAssessmentRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    employee = _get_own_employee_record(db, current_user)
    review = _get_review_or_404(db, review_id)
    updated = submit_self_assessment(db, review, employee, payload.self_assessment)
    return ReviewOut.model_validate(updated)


# --- Manager / HR / Management workflow ---

@router.post("/reviews/{review_id}/manager-review", response_model=ReviewOut, dependencies=[Depends(require_permission("performance:review"))])
def submit_manager_review_route(review_id: uuid.UUID, payload: ManagerReviewRequest, db: Session = Depends(get_db)):
    review = _get_review_or_404(db, review_id)
    updated = submit_manager_review(db, review, payload.manager_rating, payload.manager_comments)
    return ReviewOut.model_validate(updated)


@router.post("/reviews/{review_id}/generate-recommendation", response_model=ReviewOut, dependencies=[Depends(require_permission("performance:manage"))])
def generate_recommendation_route(review_id: uuid.UUID, db: Session = Depends(get_db), llm: LLMClient = Depends(get_llm_client)):
    review = _get_review_or_404(db, review_id)
    updated = generate_ai_recommendation(db, review, llm)
    return ReviewOut.model_validate(updated)


@router.post("/reviews/{review_id}/approve-hr", response_model=ReviewOut, dependencies=[Depends(require_permission("performance:manage"))])
def approve_hr_route(review_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    review = _get_review_or_404(db, review_id)
    updated = approve_hr(db, review, current_user)
    return ReviewOut.model_validate(updated)


@router.post("/reviews/{review_id}/approve-management", response_model=ReviewOut, dependencies=[Depends(require_permission("performance:approve_management"))])
def approve_management_route(review_id: uuid.UUID, payload: ManagementApprovalRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    review = _get_review_or_404(db, review_id)
    updated = approve_management(db, review, current_user, payload.final_notes)
    return ReviewOut.model_validate(updated)
