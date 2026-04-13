from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.query_schema import QueryRequest, QueryResponse
from app.services.rag_service import ask_question
from app.db.database import get_db
from app.auth.auth_utils import get_current_user

router = APIRouter(prefix="/query", tags=["RAG"])


def _require_employee(current_user: dict) -> int:
    if current_user.get("role") != "employee":
        raise HTTPException(status_code=403, detail="Only employees can access queries.")
    return int(current_user["user_id"])

@router.post("/", response_model=QueryResponse)
def query_rag(
    request: QueryRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_employee(current_user)
    return ask_question(request.question, request.model_mode, db)
