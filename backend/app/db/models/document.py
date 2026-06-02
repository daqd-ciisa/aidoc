"""Documento de la biblioteca + su estado de indexado."""
from __future__ import annotations

import enum

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TenantMixin, TimestampMixin, UUIDMixin


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class Document(UUIDMixin, TenantMixin, TimestampMixin, Base):
    """Un archivo subido por el usuario y su ciclo de vida de indexado."""

    __tablename__ = "document"
    __table_args__ = (
        # Dedup por contenido dentro del tenant.
        UniqueConstraint(
            "tenant_id", "content_hash", name="uq_document_tenant_id_content_hash"
        ),
    )

    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    extension: Mapped[str] = mapped_column(String(16), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    source: Mapped[str] = mapped_column(
        String(64), nullable=False, default="manual_upload"
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=DocumentStatus.PENDING.value,
        index=True,
    )
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
