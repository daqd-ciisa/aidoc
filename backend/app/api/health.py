"""Endpoints de salud / readiness."""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.services.qdrant import get_qdrant_client

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/health/deps")
async def health_deps() -> dict:
    """Chequea conectividad con las dependencias (Postgres, Qdrant)."""
    deps: dict[str, str] = {}

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        deps["postgres"] = "ok"
    except Exception as exc:  # noqa: BLE001 — reporte de salud, no propagar
        deps["postgres"] = f"error: {exc}"

    try:
        get_qdrant_client().get_collections()
        deps["qdrant"] = "ok"
    except Exception as exc:  # noqa: BLE001
        deps["qdrant"] = f"error: {exc}"

    healthy = all(v == "ok" for v in deps.values())
    return {"status": "ok" if healthy else "degraded", "dependencies": deps}
