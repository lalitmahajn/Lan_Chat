"""Pydantic schemas shared between server and client."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ─── Auth ─────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=64)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ─── User ─────────────────────────────────────────────────────────────────────

class UserSchema(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    status: str
    presence: str = "offline"
    last_seen: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserBrief(BaseModel):
    """Minimal user info for member lists and message display."""
    id: int
    username: str
    display_name: str
    presence: str = "offline"

    model_config = {"from_attributes": True}


# ─── Department ───────────────────────────────────────────────────────────────

class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = None


class DepartmentSchema(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    member_count: Optional[int] = None
    user_role: Optional[str] = None  # role of requesting user in this dept

    model_config = {"from_attributes": True}


class DepartmentMemberAdd(BaseModel):
    user_id: int
    role: str = "member"  # 'member' or 'admin'


# ─── Attachment ───────────────────────────────────────────────────────────────

class AttachmentSchema(BaseModel):
    id: int
    original_filename: str
    file_size: int
    mime_type: str

    model_config = {"from_attributes": True}


# ─── Message ──────────────────────────────────────────────────────────────────

class MessageSchema(BaseModel):
    id: int
    sender: UserBrief
    department_id: Optional[int] = None
    recipient_id: Optional[int] = None
    content: str
    reply_to_id: Optional[int] = None
    reply_to: Optional["MessageBrief"] = None
    attachments: list[AttachmentSchema] = []
    is_deleted: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageBrief(BaseModel):
    """Compact message reference for reply previews."""
    id: int
    sender: UserBrief
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageSend(BaseModel):
    """Client payload for sending a message."""
    department_id: Optional[int] = None
    recipient_id: Optional[int] = None
    content: str = Field(..., min_length=1, max_length=4000)
    reply_to_id: Optional[int] = None
    attachment_ids: list[int] = []


class MessageDelete(BaseModel):
    message_id: int


# ─── WebSocket Events ────────────────────────────────────────────────────────

class WSEvent(BaseModel):
    """Generic WebSocket event envelope."""
    event: str
    data: dict = {}


class TypingEvent(BaseModel):
    department_id: Optional[int] = None
    recipient_id: Optional[int] = None


class PresenceEvent(BaseModel):
    status: str  # 'online' or 'away'


# ─── Pagination ───────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    items: list = []
    total: int = 0
    page: int = 1
    page_size: int = 50
    has_more: bool = False


# ─── Admin ────────────────────────────────────────────────────────────────────

class ServerConfigUpdate(BaseModel):
    server_name: Optional[str] = None
    max_file_size_mb: Optional[int] = None
    retention_days: Optional[int] = None
    idle_timeout_minutes: Optional[int] = None


# Resolve forward ref
MessageSchema.model_rebuild()
