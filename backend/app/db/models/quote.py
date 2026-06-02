"""Cotización generada a partir de los documentos."""
from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TenantMixin, TimestampMixin, UUIDMixin


class Quote(UUIDMixin, TenantMixin, TimestampMixin, Base):
    """Borrador de cotización extraído por el LLM.

    El render/export a la plantilla del cliente es un paso posterior (pendiente);
    acá guardamos los datos estructurados (``data``) listos para rellenarla.
    """

    __tablename__ = "quote"

    # Sesión de chat desde la que se generó (opcional).
    session_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("chat_session.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Cotización")
    # Cotización estructurada (ver app/quotes/schema.py::QuoteDraft).
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
