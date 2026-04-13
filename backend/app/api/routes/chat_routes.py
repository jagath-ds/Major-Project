import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.auth_utils import get_current_user
from app.db.database import get_db
from app.schemas.chat_schema import (
    ChatExchangeResponse,
    ChatMessageCreate,
    ChatMessagesEnvelope,
    ChatSessionCreate,
    ChatSessionListItem,
    ChatSessionResponse,
)
from app.services.chat_service import (
    create_chat_session,
    delete_chat_session,
    get_chat_messages,
    list_chat_sessions,
    send_chat_message,
)

router = APIRouter(prefix="/chat", tags=["Chat"])


def _require_employee(current_user: dict) -> int:
    if current_user.get("role") != "employee":
        raise HTTPException(status_code=403, detail="Only employees can access chats.")
    return int(current_user["user_id"])


@router.post("/sessions", response_model=ChatSessionResponse)
def create_session(
    data: ChatSessionCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee_id = _require_employee(current_user)
    return create_chat_session(db, employee_id, data.title)


@router.get("/sessions", response_model=list[ChatSessionListItem])
def list_sessions(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee_id = _require_employee(current_user)
    return list_chat_sessions(db, employee_id)


@router.get("/sessions/{session_id}/messages", response_model=ChatMessagesEnvelope)
def get_session_messages(
    session_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee_id = _require_employee(current_user)
    return get_chat_messages(db, session_id, employee_id)


@router.post("/sessions/{session_id}/messages", response_model=ChatExchangeResponse)
def post_session_message(
    session_id: uuid.UUID,
    data: ChatMessageCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee_id = _require_employee(current_user)
    return send_chat_message(
        db=db,
        session_id=session_id,
        employee_id=employee_id,
        question=data.question,
        model_mode=data.model_mode,
    )


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee_id = _require_employee(current_user)
    return delete_chat_session(db, session_id, employee_id)
