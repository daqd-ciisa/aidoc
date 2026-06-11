"""Contexto de CATÁLOGO para la generación de cotizaciones.

Los documentos subidos como ``doc_type="catalog"`` (catálogo de servicios,
tarifarios) son la fuente canónica de números de parte y precios unitarios.
Este módulo recupera los fragmentos del catálogo relevantes al pedido y los
arma como un bloque etiquetado que TODOS los flujos de cotización inyectan al
prompt del LLM (guiado, desde cero, propuesta y desde contexto).
"""
from __future__ import annotations

import logging

from app.chat import rag

logger = logging.getLogger("aidoc.quotes.catalog")

CATALOG_LABEL = "CATÁLOGO DE SERVICIOS"

# Filas de catálogo suficientes para cubrir un pedido típico sin inflar el
# contexto (cada chunk de Excel trae varias filas).
_CATALOG_TOP_K = 8


def catalog_context(tenant_id: str, request: str, top_k: int = _CATALOG_TOP_K) -> str:
    """Recupera los fragmentos de catálogo relevantes al pedido (SÍNCRONO).

    Devuelve el bloque listo para inyectar al prompt, o ``""`` si el tenant no
    tiene catálogos indexados. Degradación segura: un fallo de búsqueda nunca
    rompe la generación de la cotización (se sigue sin catálogo).
    """
    try:
        chunks = rag.retrieve(request, tenant_id, top_k=top_k, doc_type="catalog")
    except Exception:  # noqa: BLE001 — el catálogo es un refuerzo, no un requisito
        logger.warning("No se pudo recuperar el catálogo; se genera sin él", exc_info=True)
        return ""
    if not chunks:
        return ""
    parts = [f"({c.filename})\n{c.text}" for c in chunks]
    return f"[{CATALOG_LABEL}]\n" + "\n\n".join(parts)
