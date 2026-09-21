import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.employees.access import get_employee_or_404, get_own_employee_record, require_self_or_permission
from app.business.onboarding import compute_onboarding_status
from app.database.connection.database import get_db
from app.database.models.user import User
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/employees", tags=["onboarding"])


@router.get("/me/onboarding-status")
def get_my_onboarding_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    employee = get_own_employee_record(db, current_user)
    return compute_onboarding_status(employee)


@router.get("/{employee_id}/onboarding-status")
def get_onboarding_status(employee_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    employee = get_employee_or_404(db, employee_id)
    require_self_or_permission(employee, current_user, "employee:read")
    return compute_onboarding_status(employee)
