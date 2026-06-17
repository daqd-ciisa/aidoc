"""Endpoints de conectores de fuentes externas (Google Drive, …)."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_id
from app.api.documents import DocumentRead
from app.connectors.google_drive import SOURCE_GOOGLE_DRIVE, download_files
from app.connectors.onedrive import SOURCE_ONEDRIVE
from app.connectors.onedrive import download_files as onedrive_download_files
from app.connectors.sharepoint import SOURCE_SHAREPOINT
from app.connectors.sharepoint import download_files as sharepoint_download_files
from app.connectors.web import SOURCE_URL, fetch_url
from app.db.models.document import DocumentType
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


class SharePointFile(BaseModel):
    id: str
    name: str
    site_id: str
    drive_id: str
    mimeType: str | None = None


class SharePointImportRequest(BaseModel):
    access_token: str
    files: list[SharePointFile]


class UrlImportRequest(BaseModel):
    url: str
    doc_type: str = DocumentType.REFERENCE.value


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


@router.post("/sharepoint/import")
async def sharepoint_import(
    req: SharePointImportRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> ImportResult:
    """Importa archivos elegidos de SharePoint (Microsoft Graph) al pipeline."""
    if not req.access_token.strip():
        raise HTTPException(status_code=401, detail="Falta el token de Microsoft.")
    if not req.files:
        raise HTTPException(status_code=422, detail="No se eligió ningún archivo.")

    try:
        items, rejected, failed = await sharepoint_download_files(
            req.access_token, [f.model_dump() for f in req.files]
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo descargando de SharePoint")
        raise HTTPException(
            status_code=502, detail=f"Descarga de SharePoint falló: {exc}"
        ) from exc

    created, duplicates, ingest_rejected = await ingest_documents(
        db, tenant_id, items, source=SOURCE_SHAREPOINT
    )

    return ImportResult(
        documents=[DocumentRead.model_validate(d) for d in created],
        duplicates=duplicates,
        rejected=rejected + ingest_rejected,
        failed=failed,
    )


@router.post("/url/import")
async def url_import(
    req: UrlImportRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> ImportResult:
    """Da de alta una fuente aprobada por URL (web pública): descarga, extrae el
    texto/PDF e indexa como ``reference`` (o el doc_type pedido)."""
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=422, detail="Falta la URL.")
    if not url.lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="La URL debe empezar con http(s)://")
    if req.doc_type not in {t.value for t in DocumentType}:
        raise HTTPException(status_code=422, detail=f"doc_type inválido: {req.doc_type!r}")

    try:
        item = await asyncio.to_thread(fetch_url, url)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo descargando la URL %s", url)
        raise HTTPException(status_code=502, detail=f"No se pudo importar la URL: {exc}") from exc

    created, duplicates, ingest_rejected = await ingest_documents(
        db,
        tenant_id,
        [item],
        source=SOURCE_URL,
        doc_type=req.doc_type,
        origin_url=url,
    )

    return ImportResult(
        documents=[DocumentRead.model_validate(d) for d in created],
        duplicates=duplicates,
        rejected=ingest_rejected,
        failed=[],
    )
