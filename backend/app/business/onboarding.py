"""
Onboarding checklist and activation gating.

This exists because the original activation check in employees/routes.py
had a real gap: it only rejected activation if there were *unverified*
documents, which is vacuously true when there are *zero* documents — an
employee with no uploads at all could be activated. This module fixes
that by defining which document types are actually mandatory and
checking presence, not just absence of pending ones.
"""
from typing import TypedDict

from app.core.exceptions import AppError
from app.database.models.employee import DocumentType, Employee, EmploymentStatus

# Per the SRS onboarding step ("Uploads Aadhaar, PAN, bank details..."), these
# three are treated as mandatory for activation. Education/experience certificates
# are collected but not gating — adjust this set if HR policy differs.
REQUIRED_DOCUMENT_TYPES: set[DocumentType] = {
    DocumentType.AADHAAR,
    DocumentType.PAN,
    DocumentType.BANK_PROOF,
}


class DocumentChecklistItem(TypedDict):
    document_type: str
    uploaded: bool
    verified: bool


class OnboardingStatus(TypedDict):
    credentials_generated: bool
    password_changed: bool
    profile_completed: bool
    documents: list[DocumentChecklistItem]
    hr_verified: bool
    employment_status: str
    ready_for_activation: bool


def compute_onboarding_status(employee: Employee) -> OnboardingStatus:
    uploaded_by_type = {d.document_type: d for d in employee.documents}

    documents: list[DocumentChecklistItem] = [
        {
            "document_type": doc_type.value,
            "uploaded": doc_type in uploaded_by_type,
            "verified": uploaded_by_type[doc_type].verified if doc_type in uploaded_by_type else False,
        }
        for doc_type in sorted(REQUIRED_DOCUMENT_TYPES, key=lambda t: t.value)
    ]

    password_changed = not employee.user.must_change_password
    all_required_docs_verified = all(d["verified"] for d in documents)

    return {
        "credentials_generated": True,  # always true by the time an Employee row exists
        "password_changed": password_changed,
        "profile_completed": employee.profile_completed,
        "documents": documents,
        "hr_verified": employee.hr_verified,
        "employment_status": employee.employment_status.value,
        "ready_for_activation": password_changed and employee.profile_completed and all_required_docs_verified,
    }


def validate_can_activate(employee: Employee) -> None:
    """Raises AppError with a specific reason if activation isn't allowed yet."""
    if employee.user.must_change_password:
        raise AppError("Cannot activate: employee has not changed their temporary password yet.")

    if not employee.profile_completed:
        raise AppError("Cannot activate: employee profile is not yet complete.")

    uploaded_by_type = {d.document_type: d for d in employee.documents}
    missing = [t for t in REQUIRED_DOCUMENT_TYPES if t not in uploaded_by_type]
    if missing:
        raise AppError(f"Cannot activate: missing required document(s): {', '.join(t.value for t in missing)}.")

    unverified = [t for t in REQUIRED_DOCUMENT_TYPES if not uploaded_by_type[t].verified]
    if unverified:
        raise AppError(f"Cannot activate: required document(s) not yet verified: {', '.join(t.value for t in unverified)}.")
