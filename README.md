# AIDOC — Plataforma de análisis documental conversacional

Plataforma para subir una biblioteca de documentos (PDF, DOCX, TXT…), indexarla en
una base vectorial y conversar sobre ella vía RAG, con generación de cotizaciones a
partir de plantillas.

- **Backend:** FastAPI (Python 3.11) — async, SQLAlchemy + Alembic, Qdrant, Redis/ARQ, S3/MinIO.
- **Frontend:** React + Vite + TypeScript (fase 3).
- **Modelos:** NVIDIA NIM (Qwen) sobre HPE PCAI.

> Evolución del prototipo original de aidoc (Streamlit). El código previo quedó en
> [`reference/`](reference/) como material de consulta.

## Arquitectura

```
React (Vite)  ──HTTP/SSE──>  FastAPI
                               ├── Postgres   (metadata: docs, jobs, chats, orgs)
                               ├── Qdrant      (vectores, filtrados por tenant_id)
                               ├── S3 / MinIO  (archivos originales)
                               └── Redis + worker (indexado asíncrono)
```

Single-tenant hoy (`tenant_id = "default"`), diseñado para multi-tenant sin migración.

## Levantar el entorno (dev)

```bash
cp .env.example .env
docker compose up --build
```

- App (frontend): http://localhost:5173
- API:            http://localhost:8000/api/health
- API + deps:     http://localhost:8000/api/health/deps
- Docs (OpenAPI): http://localhost:8000/docs
- MinIO console:  http://localhost:9001  (aidoc / aidoc-secret)
- Qdrant:         http://localhost:6333/dashboard

Las migraciones (`alembic upgrade head`) corren automáticamente al arrancar el backend.

## Roadmap

| Fase | Estado | Entrega |
|------|--------|---------|
| 0 · Scaffolding              | ✅ | Estructura, docker-compose, FastAPI + healthchecks, Alembic, Qdrant |
| 1 · Ingesta + indexado async | ✅ | Upload manual (pdf/docx/txt/md) → indexado async (ARQ) → listar/borrar/reindexar, con dedup y citas de página |
| 2 · Chat RAG con citas       | ✅ | Chat por streaming (SSE) sobre los documentos, con citas, historial y sesiones |
| 3 · Frontend React           | ✅ | SPA Vite+TS+Tailwind: Biblioteca (upload drag&drop, estado, reindex/borrar) + Chat (streaming SSE, citas, selector de docs) |
| 4 · Auth + multi-tenant      | ⏸️ | Descartada por ahora (uso single-tenant). `get_tenant_id()` deja el enganche listo para JWT a futuro |
| 5 · Cotizaciones             | 🟡 | Extracción estructurada desde documentos (disparada del chat) ✅ · render/export a plantilla pendiente (a definir) |
