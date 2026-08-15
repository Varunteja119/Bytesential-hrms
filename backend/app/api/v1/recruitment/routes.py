import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.business.recruitment import validate_transition
from app.business.resume_screening import build_screening_prompt, parse_screening_response
from app.core.dependencies import get_current_user, require_permission
from app.database.connection.database import get_db
from app.database.models.recruitment import Candidate, CandidateStatus, Job
from app.database.models.user import User
from app.database.schemas.recruitment import (
    CandidateCreate,
    CandidateOut,
    CandidateStatusUpdate,
    JobCreate,
    JobOut,
    JobUpdate,
    SimilarCandidateOut,
)
from app.services.llm_client import LLMClient, get_llm_client
from app.services.resume_parser import extract_text
from app.services.storage import StorageClient, get_storage_client
from app.services.vector_store import VectorStore, get_vector_store

router = APIRouter(prefix="/recruitment", tags=["recruitment"])


def _get_job_or_404(db: Session, job_id: uuid.UUID) -> Job:
    job = db.query(Job).options(joinedload(Job.candidates)).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job


def _get_candidate_or_404(db: Session, candidate_id: uuid.UUID) -> Candidate:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found")
    return candidate


# --- Jobs ---

@router.post(
    "/jobs",
    response_model=JobOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("recruitment:manage"))],
)
def create_job(payload: JobCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = Job(**payload.model_dump(), created_by_id=current_user.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return JobOut.from_orm_job(job)


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    # Deliberately no permission guard: open job listings are typically public-facing
    # (candidates need to see what's open). Tighten this once a public careers page
    # / anonymous-access model is defined.
    jobs = db.query(Job).options(joinedload(Job.candidates)).all()
    return [JobOut.from_orm_job(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    return JobOut.from_orm_job(_get_job_or_404(db, job_id))


@router.patch(
    "/jobs/{job_id}",
    response_model=JobOut,
    dependencies=[Depends(require_permission("recruitment:manage"))],
)
def update_job(job_id: uuid.UUID, payload: JobUpdate, db: Session = Depends(get_db)):
    job = _get_job_or_404(db, job_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    db.commit()
    db.refresh(job)
    return JobOut.from_orm_job(job)


# --- Candidates ---

@router.post(
    "/candidates",
    response_model=CandidateOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("recruitment:manage"))],
)
def create_candidate(payload: CandidateCreate, db: Session = Depends(get_db)):
    """
    Creates a candidate application against a job.

    NOTE: resume upload isn't wired here yet — `resume_storage_key` stays
    null until the AI Resume Screening step adds MinIO upload handling.
    This endpoint is guarded by recruitment:manage for now (an HR-entered
    application); a public "apply here" endpoint without auth is a
    separate, deliberate decision for later, not an oversight.
    """
    _get_job_or_404(db, payload.job_id)  # 404s cleanly instead of a raw FK violation

    candidate = Candidate(**payload.model_dump())
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return CandidateOut.model_validate(candidate)


@router.get(
    "/candidates",
    response_model=list[CandidateOut],
    dependencies=[Depends(require_permission("recruitment:manage"))],
)
def list_candidates(job_id: uuid.UUID | None = None, db: Session = Depends(get_db)):
    query = db.query(Candidate)
    if job_id is not None:
        query = query.filter(Candidate.job_id == job_id)
    return [CandidateOut.model_validate(c) for c in query.all()]


@router.get(
    "/candidates/{candidate_id}",
    response_model=CandidateOut,
    dependencies=[Depends(require_permission("recruitment:manage"))],
)
def get_candidate(candidate_id: uuid.UUID, db: Session = Depends(get_db)):
    return CandidateOut.model_validate(_get_candidate_or_404(db, candidate_id))


@router.patch(
    "/candidates/{candidate_id}/status",
    response_model=CandidateOut,
    dependencies=[Depends(require_permission("recruitment:manage"))],
)
def update_candidate_status(candidate_id: uuid.UUID, payload: CandidateStatusUpdate, db: Session = Depends(get_db)):
    candidate = _get_candidate_or_404(db, candidate_id)
    validate_transition(candidate.status, payload.status)  # raises AppError (400) on an illegal move
    candidate.status = payload.status
    db.commit()
    db.refresh(candidate)
    return CandidateOut.model_validate(candidate)


# --- AI Resume Screening ---

@router.post(
    "/candidates/{candidate_id}/resume",
    response_model=CandidateOut,
    dependencies=[Depends(require_permission("recruitment:manage"))],
)
def upload_resume(
    candidate_id: uuid.UUID,
    file: UploadFile,
    db: Session = Depends(get_db),
    storage: StorageClient = Depends(get_storage_client),
):
    """
    Uploads the resume to object storage and extracts+caches its text
    immediately (rather than at screening time) so screening doesn't need
    to re-download and re-parse the file on every run.
    """
    candidate = _get_candidate_or_404(db, candidate_id)

    content = file.file.read()
    extracted_text = extract_text(file.filename, content)  # raises AppError on unsupported/unparseable files

    storage_key = f"resumes/{candidate_id}/{file.filename}"
    storage.upload(storage_key, content, file.content_type or "application/octet-stream")

    candidate.resume_storage_key = storage_key
    candidate.resume_text = extracted_text
    db.commit()
    db.refresh(candidate)
    return CandidateOut.model_validate(candidate)


@router.post(
    "/candidates/{candidate_id}/screen",
    response_model=CandidateOut,
    dependencies=[Depends(require_permission("recruitment:manage"))],
)
def screen_candidate(
    candidate_id: uuid.UUID,
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
    vector_store: VectorStore = Depends(get_vector_store),
):
    """
    Runs AI screening: scores the candidate's resume against the job's
    requirements via the LLM, stores the score+summary, and indexes the
    resume's embedding in the vector store for similarity search.

    Requires the resume to already be uploaded (resume_text populated).
    """
    candidate = _get_candidate_or_404(db, candidate_id)
    if not candidate.resume_text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Candidate has no uploaded resume to screen yet.")

    job = _get_job_or_404(db, candidate.job_id)

    prompt = build_screening_prompt(job.title, job.requirements or "", candidate.resume_text)
    raw_response = llm.generate(prompt)
    score, summary = parse_screening_response(raw_response)  # raises AppError (502) on unparseable LLM output

    candidate.ai_score = score
    candidate.ai_summary = summary
    if candidate.status.value == "applied":
        candidate.status = CandidateStatus.SCREENING  # advance the pipeline automatically on first screen
    db.commit()
    db.refresh(candidate)

    embedding = llm.embed(candidate.resume_text)
    vector_store.upsert_candidate_embedding(str(candidate.id), embedding)

    return CandidateOut.model_validate(candidate)


@router.get(
    "/jobs/{job_id}/similar-candidates",
    response_model=list[SimilarCandidateOut],
    dependencies=[Depends(require_permission("recruitment:manage"))],
)
def find_similar_candidates(
    job_id: uuid.UUID,
    limit: int = 5,
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
    vector_store: VectorStore = Depends(get_vector_store),
):
    """
    Embeds the job's description+requirements and finds the closest-matching
    screened candidates across ALL jobs by resume embedding — useful for
    "we have an opening, who in our existing candidate pool might fit?"
    rather than only ranking within one job's applicant list.
    """
    job = _get_job_or_404(db, job_id)
    query_text = f"{job.title}\n{job.requirements or job.description}"
    embedding = llm.embed(query_text)

    matches = vector_store.find_similar_candidates(embedding, n_results=limit)

    results = []
    for match in matches:
        candidate = db.get(Candidate, uuid.UUID(match["candidate_id"]))
        if candidate is not None:
            results.append(SimilarCandidateOut(candidate=CandidateOut.model_validate(candidate), distance=match["distance"]))
    return results
