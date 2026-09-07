import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.v1.employees.access import get_employee_or_404, require_self_or_permission
from app.core.exceptions import AppError
from app.database.connection.database import get_db
from app.database.models.employee import DocumentType, EmployeeDocument
from app.database.models.user import User
from app.database.schemas.employee import EmployeeDocumentOut
from app.dependencies.auth import get_current_user, require_permission
from app.services.storage import StorageClient, get_storage_client

# Deliberately kept at the /employees prefix (not /documents) — these endpoints
# were already documented and shared with the frontend team as
# /employees/{id}/documents before this module split existed. Moving the file
# into its own documents/ module (per the mandated project structure) without
# changing the URL keeps that integration work unaffected.
router = APIRouter(prefix="/employees", tags=["documents"])


@router.post("/{employee_id}/documents", response_model=EmployeeDocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    employee_id: uuid.UUID,
    document_type: str,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageClient = Depends(get_storage_client),
):
    employee = get_employee_or_404(db, employee_id)
    require_self_or_permission(employee, current_user, "employee:write")
    try:
        doc_type = DocumentType(document_type)
    except ValueError:
        raise AppError(f"Invalid document_type. Must be one of: {', '.join(t.value for t in DocumentType)}")

    content = file.file.read()
    storage_key = f"employee-documents/{employee_id}/{doc_type.value}/{file.filename}"
    storage.upload(storage_key, content, file.content_type or "application/octet-stream")

    document = EmployeeDocument(employee_id=employee_id, document_type=doc_type, storage_key=storage_key, original_filename=file.filename)
    db.add(document)
    db.commit()
    db.refresh(document)
    return EmployeeDocumentOut.model_validate(document)


@router.get("/{employee_id}/documents", response_model=list[EmployeeDocumentOut])
def list_documents(employee_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    employee = get_employee_or_404(db, employee_id)
    require_self_or_permission(employee, current_user, "employee:read")
    return [EmployeeDocumentOut.model_validate(d) for d in employee.documents]


@router.patch("/{employee_id}/documents/{document_id}/verify", response_model=EmployeeDocumentOut, dependencies=[Depends(require_permission("employee:write"))])
def verify_document(employee_id: uuid.UUID, document_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    document = db.get(EmployeeDocument, document_id)
    if document is None or document.employee_id != employee_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    document.verified = True
    document.verified_by_id = current_user.id
    db.commit()
    db.refresh(document)
    return EmployeeDocumentOut.model_validate(document)
