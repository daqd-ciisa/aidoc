"""URL aprobada: fuente externa que el modelo consulta EN VIVO al validar.

A diferencia de los documentos ``reference`` (que se descargan e indexan una vez),
una ``ApprovedUrl`` es solo una URL de una fuente autoritativa (HPE QuickSpecs,
Microsoft 365 Learn…) que el pase de validación descarga al momento para
contrastar las afirmaciones técnicas de una propuesta.
"""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TenantMixin, TimestampMixin, UUIDMixin


class ApprovedUrl(UUIDMixin, TenantMixin, TimestampMixin, Base):
    """Una URL aprobada por tenant, consultada en vivo en la validación."""

    __tablename__ = "approved_url"

    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    label: Mapped[str | None] = mapped_column(String(256), nullable=True)
