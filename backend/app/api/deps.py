"""Dependencies compartidas de la API."""
from __future__ import annotations

from app.config import settings


def get_tenant_id() -> str:
    """Tenant actual.

    Single-tenant hoy: siempre el default. En la Fase 4 (auth) esto se reemplaza
    por la extracción del ``tenant_id`` desde el JWT.
    """
    return settings.DEFAULT_TENANT_ID
