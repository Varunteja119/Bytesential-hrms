"""
Shared access-control helpers for anything that operates on an Employee
record. Split out so employees/, documents/, and onboarding/ route
modules can all use the same "is this my own record, or do I have the
permission to act on someone else's" logic without importing from each
other's route files.
"""
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database.models.employee import Employee
from app.database.models.user import User


def get_employee_or_404(db: Session, employee_id: uuid.UUID) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    return employee


def get_own_employee_record(db: Session, user: User) -> Employee:
    employee = db.query(Employee).filter(Employee.user_id == user.id).first()
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No employee record linked to your account")
    return employee


def require_self_or_permission(employee: Employee, user: User, permission_code: str) -> None:
    if employee.user_id == user.id:
        return
    if user.is_superuser or user.has_permission(permission_code):
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only access your own employee record")
