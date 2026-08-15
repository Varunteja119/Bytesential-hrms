import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.database.models.recruitment import CandidateStatus, JobStatus


# --- Job ---

class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    department: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1)
    requirements: str | None = None


class JobUpdate(BaseModel):
    title: str | None = None
    department: str | None = None
    description: str | None = None
    requirements: str | None = None
    status: JobStatus | None = None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    department: str
    description: str
    requirements: str | None
    status: JobStatus
    candidate_count: int = 0

    @classmethod
    def from_orm_job(cls, job) -> "JobOut":
        return cls(
            id=job.id,
            title=job.title,
            department=job.department,
            description=job.description,
            requirements=job.requirements,
            status=job.status,
            candidate_count=len(job.candidates),
        )


# --- Candidate ---

class CandidateCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    phone: str | None = None
    job_id: uuid.UUID
    notes: str | None = None


class CandidateStatusUpdate(BaseModel):
    status: CandidateStatus


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: EmailStr
    phone: str | None
    job_id: uuid.UUID
    status: CandidateStatus
    resume_storage_key: str | None
    resume_text: str | None
    ai_score: float | None
    ai_summary: str | None
    notes: str | None


class SimilarCandidateOut(BaseModel):
    candidate: CandidateOut
    distance: float
