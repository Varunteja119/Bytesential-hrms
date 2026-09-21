"""
Performance management schema.

Design mirrors payroll.py's PayrollRun/Payslip pattern: a PerformanceCycle
is the batch (e.g. "Q3 2026 Review"), PerformanceReview is one row per
employee within it -- same reasoning as payroll: HR starts one cycle,
the system generates a review row per active employee, then each moves
through its own state machine independently.

The AI recommendation step reuses the same LLM abstraction already
verified in resume_screening -- prompt in, robustly-parsed JSON out.
Per the SRS workflow ("AI recommends promotion, training and salary
hikes -> HR & Management Approval"), the recommendation is advisory:
nothing changes an employee's actual salary or title until a human
approves it at BOTH the HR and Management steps.
"""
import enum
from datetime import date as date_type, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection.database import Base
from app.database.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CycleStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class ReviewStatus(str, enum.Enum):
    PENDING_SELF_ASSESSMENT = "pending_self_assessment"
    PENDING_MANAGER_REVIEW = "pending_manager_review"
    PENDING_AI_RECOMMENDATION = "pending_ai_recommendation"
    PENDING_HR_APPROVAL = "pending_hr_approval"
    PENDING_MANAGEMENT_APPROVAL = "pending_management_approval"
    COMPLETED = "completed"


class RecommendedAction(str, enum.Enum):
    PROMOTION = "promotion"
    SALARY_HIKE = "salary_hike"
    TRAINING = "training"
    NO_CHANGE = "no_change"


class PerformanceCycle(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "performance_cycles"

    name: Mapped[str] = mapped_column(String(150), nullable=False)  # e.g. "Q3 2026 Review"
    period_start: Mapped[date_type] = mapped_column(Date, nullable=False)
    period_end: Mapped[date_type] = mapped_column(Date, nullable=False)
    status: Mapped[CycleStatus] = mapped_column(Enum(CycleStatus), default=CycleStatus.OPEN, nullable=False)
    created_by_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    reviews: Mapped[list["PerformanceReview"]] = relationship(back_populates="cycle", cascade="all, delete-orphan")


class PerformanceReview(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "performance_reviews"
    __table_args__ = (UniqueConstraint("cycle_id", "employee_id", name="uq_review_cycle_employee"),)

    cycle_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("performance_cycles.id", ondelete="CASCADE"), nullable=False)
    cycle: Mapped["PerformanceCycle"] = relationship(back_populates="reviews")

    employee_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    reviewer_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))  # employee's reporting manager, if set

    status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus), default=ReviewStatus.PENDING_SELF_ASSESSMENT, nullable=False)

    # Self-assessment (employee)
    self_assessment: Mapped[str | None] = mapped_column(Text)

    # Manager review
    manager_rating: Mapped[int | None] = mapped_column(Integer)  # 1-5
    manager_comments: Mapped[str | None] = mapped_column(Text)

    # AI recommendation (advisory only -- see module docstring)
    ai_recommended_action: Mapped[RecommendedAction | None] = mapped_column(Enum(RecommendedAction))
    ai_recommended_hike_percent: Mapped[float | None] = mapped_column(Float)
    ai_summary: Mapped[str | None] = mapped_column(Text)

    # Two-step approval, same pattern as PayrollRun's HR -> Finance chain
    hr_approved_by_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    hr_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    management_approved_by_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    management_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    final_decision_notes: Mapped[str | None] = mapped_column(Text)
