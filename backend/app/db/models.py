from .database import Base
from sqlalchemy import  Integer, String, Text,func,DateTime,ForeignKey,Boolean,JSON
from sqlalchemy.dialects.postgresql import UUID,INET
from sqlalchemy.orm import Mapped, mapped_column,relationship
from datetime import datetime
from typing import Optional
import uuid

class Document(Base):
    __tablename__ = "documents"
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), server_default="uploaded",nullable=False)
    total_chunks: Mapped[int] = mapped_column(Integer, server_default="0",nullable=False)
    uploaded_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    indexed_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class Employees(Base):
    __tablename__="employees"

    emp_id : Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
    firstname: Mapped[str] = mapped_column(String(50), nullable=False)
    lastname: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255),nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    department: Mapped[str] = mapped_column(String(50), nullable=True)
    designation: Mapped[str] = mapped_column(String(50), nullable=True)

    
class Admin(Base):
    __tablename__="admins"

    admin_id : Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
    firstname: Mapped[str] = mapped_column(String(50), nullable=False)
    lastname: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255),nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    
    
class SystemLog(Base):
    __tablename__ = "system_logs"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)  
    actor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    action_description: Mapped[str] = mapped_column(Text, nullable=True)
    affected_table: Mapped[str] = mapped_column(String(50), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())
    ip_address = mapped_column(INET, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=True)

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.emp_id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_archived: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_sessions.session_id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources_json: Mapped[Optional[list[dict]]] = mapped_column(JSON, nullable=True)
    model_mode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    grounded: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
