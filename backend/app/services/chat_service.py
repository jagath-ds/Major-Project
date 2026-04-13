from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import ChatMessage, ChatSession
from app.schemas.chat_schema import (
    ChatExchangeResponse,
    ChatMessageResponse,
    ChatMessagesEnvelope,
    ChatSource,
    ChatSessionListItem,
    ChatSessionResponse,
)
from app.services.rag_service import ask_question


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _build_title(question: str) -> str:
    clean_question = " ".join(question.strip().split())
    if not clean_question:
        return "New Chat"
    return clean_question[:60]


def _session_query(db: Session, employee_id: int):
    return db.query(ChatSession).filter(
        ChatSession.employee_id == employee_id,
        ChatSession.deleted_at.is_(None),
    )


def _get_owned_session(db: Session, session_id: uuid.UUID, employee_id: int) -> ChatSession:
    session = _session_query(db, employee_id).filter(
        ChatSession.session_id == session_id
    ).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return session


def _to_session_response(session: ChatSession) -> ChatSessionResponse:
    return ChatSessionResponse(
        session_id=session.session_id,
        employee_id=session.employee_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        last_message_at=session.last_message_at,
        is_archived=session.is_archived,
        deleted_at=session.deleted_at,
    )


def _to_session_list_item(session: ChatSession) -> ChatSessionListItem:
    return ChatSessionListItem(
        session_id=session.session_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        last_message_at=session.last_message_at,
    )


def _to_message_response(message: ChatMessage) -> ChatMessageResponse:
    sources = None
    if message.sources_json:
        sources = [ChatSource(**source) for source in message.sources_json]

    return ChatMessageResponse(
        message_id=message.message_id,
        session_id=message.session_id,
        role=message.role,
        content=message.content,
        sources_json=sources,
        model_mode=message.model_mode,
        grounded=message.grounded,
        created_at=message.created_at,
    )


def create_chat_session(
    db: Session,
    employee_id: int,
    title: str,
) -> ChatSessionResponse:
    chat_session = ChatSession(
        employee_id=employee_id,
        title=title.strip() or "New Chat",
    )
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
    return _to_session_response(chat_session)


def list_chat_sessions(db: Session, employee_id: int) -> list[ChatSessionListItem]:
    sessions = (
        _session_query(db, employee_id)
        .order_by(ChatSession.last_message_at.desc(), ChatSession.created_at.desc())
        .all()
    )
    return [_to_session_list_item(session) for session in sessions]


def get_chat_messages(
    db: Session,
    session_id: uuid.UUID,
    employee_id: int,
) -> ChatMessagesEnvelope:
    session = _get_owned_session(db, session_id, employee_id)
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return ChatMessagesEnvelope(
        session_id=session.session_id,
        messages=[_to_message_response(message) for message in messages],
    )


def send_chat_message(
    db: Session,
    session_id: uuid.UUID,
    employee_id: int,
    question: str,
    model_mode: str = "auto",
) -> ChatExchangeResponse:
    session = _get_owned_session(db, session_id, employee_id)
    now = _utcnow()
    clean_question = question.strip()

    if not clean_question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    user_message = ChatMessage(
        session_id=session.session_id,
        role="user",
        content=clean_question,
        model_mode=model_mode,
    )
    db.add(user_message)
    db.flush()

    if not session.title.strip() or session.title == "New Chat":
        session.title = _build_title(clean_question)

    rag_response = ask_question(clean_question, model_mode, db)

    assistant_message = ChatMessage(
        session_id=session.session_id,
        role="assistant",
        content=rag_response.answer,
        sources_json=[source.model_dump() for source in rag_response.sources],
        model_mode=model_mode,
        grounded=rag_response.grounded,
    )
    db.add(assistant_message)

    session.updated_at = now
    session.last_message_at = now

    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)
    db.refresh(session)

    return ChatExchangeResponse(
        session_id=session.session_id,
        user_message=_to_message_response(user_message),
        assistant_message=_to_message_response(assistant_message),
    )


def delete_chat_session(db: Session, session_id: uuid.UUID, employee_id: int) -> dict:
    session = _get_owned_session(db, session_id, employee_id)
    deleted_at = _utcnow()
    session.deleted_at = deleted_at
    session.updated_at = deleted_at
    db.commit()
    return {"message": "Chat session deleted successfully."}
