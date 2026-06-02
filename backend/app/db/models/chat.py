"""Sesiones y mensajes de chat."""
from __future__ import annotations

import enum

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TenantMixin, TimestampMixin, UUIDMixin


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatSession(UUIDMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "chat_session"

    title: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Nueva conversación"
    )


class ChatMessage(UUIDMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "chat_message"

    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_session.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Lista de citas (solo en mensajes del asistente).
    citations: Mapped[list | None] = mapped_column(JSON, nullable=True)
