"""Punto de entrada de la API de AIDOC."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.connectors import router as connectors_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.quotes import router as quotes_router
from app.api.sources import router as sources_router
from app.auth.bootstrap import ensure_superadmin
from app.config import settings
from app.services import storage
from app.services.qdrant import ensure_collection


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: asegurar colección de vectores y bucket de storage.
    for step in (ensure_collection, storage.ensure_bucket):
        try:
            step()
        except Exception:  # noqa: BLE001 — no abortar si una dependencia no está lista aún
            pass
    # Crear el super-admin de plataforma si está configurado por env.
    try:
        await ensure_superadmin()
    except Exception:  # noqa: BLE001 — no abortar el arranque si la DB no está lista
        pass
    yield
    # Shutdown: nada por ahora.


app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(quotes_router, prefix="/api")
app.include_router(connectors_router, prefix="/api")
app.include_router(sources_router, prefix="/api")
