"""Endpoints de conectores de fuentes externas (Google Drive, …)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_id
from app.api.documents import DocumentRead
from app.connectors.google_drive import SOURCE_GOOGLE_DRIVE, download_files
from app.connectors.onedrive import SOURCE_ONEDRIVE
from app.connectors.onedrive import download_files as onedrive_download_files
from app.db.session import get_db
from app.ingestion.intake import ingest_documents

logger = logging.getLogger("aidoc.connectors")

router = APIRouter(prefix="/connectors", tags=["connectors"])


class DriveFile(BaseModel):
    id: str
    name: str
    mimeType: str | None = None


class DriveImportRequest(BaseModel):
    access_token: str
    files: list[DriveFile]


class ImportResult(BaseModel):
    documents: list[DocumentRead]
    duplicates: list[str]
    rejected: list[str]
    failed: list[str]


@router.post("/google/import")
async def google_import(
    req: DriveImportRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> ImportResult:
    """Importa archivos elegidos en el Picker de Google Drive al pipeline."""
    if not req.access_token.strip():
        raise HTTPException(status_code=401, detail="Falta el token de Google.")
    if not req.files:
        raise HTTPException(status_code=422, detail="No se eligió ningún archivo.")

    try:
        items, rejected, failed = await download_files(
            req.access_token, [f.model_dump() for f in req.files]
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo descargando de Google Drive")
        raise HTTPException(
            status_code=502, detail=f"Descarga de Google Drive falló: {exc}"
        ) from exc

    created, duplicates, ingest_rejected = await ingest_documents(
        db, tenant_id, items, source=SOURCE_GOOGLE_DRIVE
    )

    return ImportResult(
        documents=[DocumentRead.model_validate(d) for d in created],
        duplicates=duplicates,
        rejected=rejected + ingest_rejected,
        failed=failed,
    )


@router.post("/onedrive/import")
async def onedrive_import(
    req: DriveImportRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> ImportResult:
    """Importa archivos elegidos de OneDrive (Microsoft Graph) al pipeline."""
    if not req.access_token.strip():
        raise HTTPException(status_code=401, detail="Falta el token de Microsoft.")
    if not req.files:
        raise HTTPException(status_code=422, detail="No se eligió ningún archivo.")

    try:
        items, rejected, failed = await onedrive_download_files(
            req.access_token, [f.model_dump() for f in req.files]
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo descargando de OneDrive")
        raise HTTPException(
            status_code=502, detail=f"Descarga de OneDrive falló: {exc}"
        ) from exc

    created, duplicates, ingest_rejected = await ingest_documents(
        db, tenant_id, items, source=SOURCE_ONEDRIVE
    )

    return ImportResult(
        documents=[DocumentRead.model_validate(d) for d in created],
        duplicates=duplicates,
        rejected=rejected + ingest_rejected,
        failed=failed,
    )
