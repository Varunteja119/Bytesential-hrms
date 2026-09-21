import uuid
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field
from app.database.models.performance import CycleStatus, RecommendedAction, ReviewStatus


class CycleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    period_start: date
    period_end: date


class CycleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    period_start: date
    period_end: date
    status: CycleStatus
    review_count: int = 0

    @classmethod
    def from_orm_cycle(cls, cycle) -> "CycleOut":
        return cls(id=cycle.id, name=cycle.name, period_start=cycle.period_start, period_end=cycle.period_end,
                    status=cycle.status, review_count=len(cycle.reviews))


class SelfAssessmentRequest(BaseModel):
    self_assessment: str = Field(min_length=1)


class ManagerReviewRequest(BaseModel):
    manager_rating: int = Field(ge=1, le=5)
    manager_comments: str = Field(min_length=1)


class ManagementApprovalRequest(BaseModel):
    final_notes: str | None = None


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    cycle_id: uuid.UUID
    employee_id: uuid.UUID
    reviewer_id: uuid.UUID | None
    status: ReviewStatus
    self_assessment: str | None
    manager_rating: int | None
    manager_comments: str | None
    ai_recommended_action: RecommendedAction | None
    ai_recommended_hike_percent: float | None
    ai_summary: str | None
    hr_approved_by_id: uuid.UUID | None
    hr_approved_at: datetime | None
    management_approved_by_id: uuid.UUID | None
    management_approved_at: datetime | None
    final_decision_notes: str | None
