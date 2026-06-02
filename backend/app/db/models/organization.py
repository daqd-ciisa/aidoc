"""Organización = tenant de la plataforma."""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UUIDMixin


class Organization(UUIDMixin, TimestampMixin, Base):
    """Tenant de la plataforma.

    Hoy existe una sola fila (``default``); el modelo ya soporta multi-tenant.
    """

    __tablename__ = "organization"

    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
