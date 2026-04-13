from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import uuid


class ChatSource(BaseModel):
    document_id: str
    source_path: str
    page: int | None


class ChatSessionCreate(BaseModel):
    title: str


class ChatSessionResponse(BaseModel):
    session_id: uuid.UUID
    employee_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime
    is_archived: bool
    deleted_at: Optional[datetime] = None


class ChatSessionListItem(BaseModel):
    session_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime


class ChatMessageCreate(BaseModel):
    question: str
    model_mode: str = "auto"


class ChatMessageResponse(BaseModel):
    message_id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    sources_json: list[ChatSource] | None = None
    model_mode: str | None = None
    grounded: bool | None = None
    created_at: datetime


class ChatMessagesEnvelope(BaseModel):
    session_id: uuid.UUID
    messages: list[ChatMessageResponse]


class ChatExchangeResponse(BaseModel):
    session_id: uuid.UUID
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
