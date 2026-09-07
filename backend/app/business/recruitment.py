from app.core.exceptions import AppError
from app.database.models.recruitment import CandidateStatus

_TERMINAL_STATES = {CandidateStatus.ACCEPTED, CandidateStatus.REJECTED, CandidateStatus.WITHDRAWN}
_ALLOWED_TRANSITIONS = {
    CandidateStatus.APPLIED: {CandidateStatus.SCREENING, CandidateStatus.REJECTED, CandidateStatus.WITHDRAWN},
    CandidateStatus.SCREENING: {CandidateStatus.INTERVIEW, CandidateStatus.REJECTED, CandidateStatus.WITHDRAWN},
    CandidateStatus.INTERVIEW: {CandidateStatus.HR_APPROVAL, CandidateStatus.REJECTED, CandidateStatus.WITHDRAWN},
    CandidateStatus.HR_APPROVAL: {CandidateStatus.OFFERED, CandidateStatus.REJECTED, CandidateStatus.WITHDRAWN},
    CandidateStatus.OFFERED: {CandidateStatus.ACCEPTED, CandidateStatus.REJECTED, CandidateStatus.WITHDRAWN},
    CandidateStatus.ACCEPTED: set(), CandidateStatus.REJECTED: set(), CandidateStatus.WITHDRAWN: set(),
}


def validate_transition(current: CandidateStatus, target: CandidateStatus) -> None:
    if current in _TERMINAL_STATES:
        raise AppError(f"Candidate is already in a terminal state ({current.value}); no further transitions allowed.")
    if target not in _ALLOWED_TRANSITIONS[current]:
        allowed = ", ".join(s.value for s in _ALLOWED_TRANSITIONS[current]) or "none"
        raise AppError(f"Cannot move candidate from '{current.value}' to '{target.value}'. Allowed next steps: {allowed}.")
