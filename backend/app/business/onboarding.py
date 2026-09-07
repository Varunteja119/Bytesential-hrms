from typing import TypedDict
from app.core.exceptions import AppError
from app.database.models.employee import DocumentType, Employee, EmploymentStatus

REQUIRED_DOCUMENT_TYPES = {DocumentType.AADHAAR, DocumentType.PAN, DocumentType.BANK_PROOF}


def compute_onboarding_status(employee: Employee) -> dict:
    uploaded_by_type = {d.document_type: d for d in employee.documents}
    documents = [
        {"document_type": t.value, "uploaded": t in uploaded_by_type,
         "verified": uploaded_by_type[t].verified if t in uploaded_by_type else False}
        for t in sorted(REQUIRED_DOCUMENT_TYPES, key=lambda t: t.value)
    ]
    password_changed = not employee.user.must_change_password
    all_verified = all(d["verified"] for d in documents)
    return {
        "credentials_generated": True, "password_changed": password_changed,
        "profile_completed": employee.profile_completed, "documents": documents,
        "hr_verified": employee.hr_verified, "employment_status": employee.employment_status.value,
        "ready_for_activation": password_changed and employee.profile_completed and all_verified,
    }


def validate_can_activate(employee: Employee) -> None:
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
