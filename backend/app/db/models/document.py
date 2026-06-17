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


class DocumentType(str, enum.Enum):
    """Naturaleza del documento dentro de la biblioteca.

    - ``document``: contenido normal (propuestas, contratos…): consultable en el
      chat y candidato a precedente de cotizaciones.
    - ``catalog``: material de referencia (catálogo de servicios, tarifario): se
      inyecta SIEMPRE como fuente de números de parte/precios al generar
      cotizaciones, y NUNCA compite como precedente.
    - ``reference``: FUENTE APROBADA externa (QuickSpecs de HPE, guías validadas
      de Aruba, Microsoft 365 Learn…): documentación autoritativa del fabricante
      para validar las afirmaciones técnicas de las propuestas. Tampoco compite
      como precedente.
    """

    DOCUMENT = "document"
    CATALOG = "catalog"
    REFERENCE = "reference"


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
    doc_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default=DocumentType.DOCUMENT.value
    )
    # Solo para fuentes aprobadas (doc_type="reference") dadas de alta por web:
    # URL de origen (trazabilidad de la fuente).
    origin_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=DocumentStatus.PENDING.value,
        index=True,
    )
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
