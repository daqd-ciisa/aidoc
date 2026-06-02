"""Conector de Google Drive (importación puntual).

Patrón cliente-amigable: el frontend obtiene un access_token (scope drive.file)
vía Google Identity Services + Picker, el usuario elige archivos, y acá los
descargamos. Los Google Docs/Sheets/Slides se exportan a un formato parseable.
"""
from __future__ import annotations

from pathlib import Path

import httpx

from app.ingestion.parsers import SUPPORTED_EXTENSIONS

SOURCE_GOOGLE_DRIVE = "google_drive"

_FILES_API = "https://www.googleapis.com/drive/v3/files"

# Tipos nativos de Google → (mimeType de export, extensión destino).
# Se exportan a formatos que ya sabemos parsear (PDF / texto).
_EXPORT_MAP = {
    "application/vnd.google-apps.document": ("application/pdf", ".pdf"),
    "application/vnd.google-apps.presentation": ("application/pdf", ".pdf"),
    "application/vnd.google-apps.spreadsheet": ("text/csv", ".txt"),
}


async def download_files(
    access_token: str, files: list[dict]
) -> tuple[list[tuple[str, bytes, str | None]], list[str], list[str]]:
    """Descarga los archivos elegidos.

    Devuelve (items, rechazados, fallidos):
    - items: (nombre, bytes, content_type) listos para ingestar.
    - rechazados: tipos no soportados (no se descargan).
    - fallidos: errores al descargar/exportar.
    """
    items: list[tuple[str, bytes, str | None]] = []
    rejected: list[str] = []
    failed: list[str] = []
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=60) as client:
        for f in files:
            fid = f.get("id")
            name = f.get("name") or (fid or "documento")
            mime = f.get("mimeType") or ""
            if not fid:
                failed.append(name)
                continue

            try:
                if mime in _EXPORT_MAP:
                    target_mime, ext = _EXPORT_MAP[mime]
                    if not name.lower().endswith(ext):
                        name = f"{name}{ext}"
                    resp = await client.get(
                        f"{_FILES_API}/{fid}/export",
                        params={"mimeType": target_mime},
                        headers=headers,
                    )
                    ctype: str | None = target_mime
                elif mime.startswith("application/vnd.google-apps"):
                    # Otros nativos (formularios, dibujos, etc.) no soportados.
                    rejected.append(name)
                    continue
                else:
                    if Path(name).suffix.lower() not in SUPPORTED_EXTENSIONS:
                        rejected.append(name)
                        continue
                    resp = await client.get(
                        f"{_FILES_API}/{fid}",
                        params={"alt": "media"},
                        headers=headers,
                    )
                    ctype = mime or None

                resp.raise_for_status()
                items.append((name, resp.content, ctype))
            except Exception:  # noqa: BLE001 — registramos el archivo como fallido
                failed.append(name)

    return items, rejected, failed
