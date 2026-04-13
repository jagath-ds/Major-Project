from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Employees, SystemLog
from app.auth.auth_utils import get_current_user

from app.utils.logger import log_event

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(current_user: dict) -> int:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admins can access this resource.")
    return int(current_user["user_id"])


@router.get("/employees")
def get_all_employees(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    users = db.query(Employees).all()

    return [
        {
            "id": user.emp_id,
            "name": user.firstname + " " + user.lastname,
            "email": user.email,
            "status": user.status
        }
        for user in users
    ]
@router.patch("/employees/{emp_id}/status")
def update_status(
    emp_id: int,
    status: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    admin_id = _require_admin(current_user)
    user = db.get(Employees, emp_id)

    if not user:
        raise HTTPException(404, "User not found")

    user.status = status
    db.commit()

    log_event(
        db,
        actor_type="admin",
        actor_id=admin_id,
        action_type="UPDATE_USER_STATUS",
        description=f"Updated status for {user.email} to {status}"
    )

    return {"message": "Status updated"}

@router.delete("/employees/{emp_id}")
def delete_employee(
    emp_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    admin_id = _require_admin(current_user)
    user = db.get(Employees, emp_id)

    if not user:
        raise HTTPException(404, "User not found")
    log_event(
    db,
    actor_type="admin",
    actor_id=admin_id,
    action_type="DELETE_USER",
    description=f"Deleted user {user.email}"
)
    db.delete(user)
    db.commit()


    return {"message": "User deleted"}

@router.get("/logs")
def get_logs(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    logs = db.query(SystemLog).order_by(SystemLog.timestamp.desc()).all()

    return [
        {
            "id": log.log_id,
            "actor": f"{log.actor_type} ({log.actor_id})",
            "action": log.action_type,
            "description": log.action_description,
            "time": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "status": log.status
        }
        for log in logs
    ]
