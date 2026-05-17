"""SQLAlchemy ORM models."""

from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship

from common.constants import AccountStatus, Presence, Role
from common.utils import utc_now
from server.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(32), unique=True, nullable=False, index=True)
    display_name = Column(String(64), nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(16), nullable=False, default=Role.MEMBER)
    status = Column(String(16), nullable=False, default=AccountStatus.PENDING)
    presence = Column(String(16), nullable=False, default=Presence.OFFLINE)
    last_seen = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    department_memberships = relationship("UserDepartment", back_populates="user", cascade="all, delete-orphan")
    sent_messages = relationship("Message", back_populates="sender", foreign_keys="Message.sender_id")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    @property
    def is_super_admin(self) -> bool:
        return self.role == Role.SUPER_ADMIN

    @property
    def is_approved(self) -> bool:
        return self.status == AccountStatus.APPROVED


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    memberships = relationship("UserDepartment", back_populates="department", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="department", cascade="all, delete-orphan")


class UserDepartment(Base):
    __tablename__ = "user_departments"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String(16), nullable=False, default=Role.MEMBER)

    # Relationships
    user = relationship("User", back_populates="department_memberships")
    department = relationship("Department", back_populates="memberships")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=True)
    recipient_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    content = Column(Text, nullable=False)
    reply_to_id = Column(Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now, index=True)

    # Relationships
    sender = relationship("User", back_populates="sent_messages", foreign_keys=[sender_id])
    department = relationship("Department", back_populates="messages")
    reply_to = relationship("Message", remote_side=[id], uselist=False)
    attachments = relationship("Attachment", back_populates="message", cascade="all, delete-orphan")


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=True)
    original_filename = Column(String(256), nullable=False)
    stored_filename = Column(String(64), nullable=False, unique=True)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(128), nullable=False)
    file_path = Column(String(512), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    message = relationship("Message", back_populates="attachments")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(512), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")


class ServerConfigEntry(Base):
    __tablename__ = "server_config"

    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=False)
