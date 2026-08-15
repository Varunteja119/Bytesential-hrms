"""
Recruitment schema: Job postings and Candidates.

Design: Candidate is deliberately its own entity, NOT a row in `users`/
`employees`. Per the SRS workflow (Recruitment -> Interview -> AI Resume
Screening -> HR Approval -> Offer -> Candidate Accepts -> Employee ID
generated), a person only becomes a User+Employee *after* they accept an
offer. Modeling Candidate separately means the recruitment pipeline can
hold people who never get hired without polluting the employee table,
and the eventual "convert candidate -> employee" step is an explicit,
auditable action rather than an implicit state flag.
"""
import enum

from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection.database import Base
from app.database.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class JobStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"


class CandidateStatus(str, enum.Enum):
    """Mirrors the SRS pipeline: Recruitment -> Interview -> AI Screening -> HR Approval -> Offer -> Accepted/Rejected."""

    APPLIED = "applied"
    SCREENING = "screening"          # AI resume screening in progress / scored
    INTERVIEW = "interview"
    HR_APPROVAL = "hr_approval"
    OFFERED = "offered"
    ACCEPTED = "accepted"            # triggers employee provisioning (Phase 2 next step)
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "jobs"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requirements: Mapped[str | None] = mapped_column(Text)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.DRAFT, nullable=False)

    created_by_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_by = relationship("User")

    candidates: Mapped[list["Candidate"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class Candidate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "candidates"

    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(30))

    job_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    job: Mapped["Job"] = relationship(back_populates="candidates")

    status: Mapped[CandidateStatus] = mapped_column(
        Enum(CandidateStatus), default=CandidateStatus.APPLIED, nullable=False
    )

    # Path/key into object storage (MinIO) — set once resume upload is used.
    resume_storage_key: Mapped[str | None] = mapped_column(String(500))

    # Extracted text, cached at upload time so re-screening doesn't require
    # re-downloading + re-parsing the file from storage every time.
    resume_text: Mapped[str | None] = mapped_column(Text)

    # Populated by AI Resume Screening — nullable until a candidate is screened.
    ai_score: Mapped[float | None] = mapped_column(Float)
    ai_summary: Mapped[str | None] = mapped_column(Text)

    notes: Mapped[str | None] = mapped_column(Text)
