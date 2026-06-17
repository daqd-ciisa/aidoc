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

Multi-tenant por organización: cada usuario pertenece a una org y solo ve los datos
de la suya (`tenant_id = organization_id`).

## Levantar el entorno en una PC nueva (dev)

**Prerequisitos:** Git y Docker Desktop (en Windows, con WSL2). Nada más: Python,
Node y todas las dependencias viven dentro de los contenedores.

```bash
git clone https://github.com/AxelJrz/aidoc.git
cd aidoc
git checkout poc        # ⚠️ la plataforma vive en `poc`; `main` es el prototipo viejo
cp .env.example .env
# → editar .env (ver "Configuración mínima" abajo)
docker compose up --build
```

- App (frontend): http://localhost:5173
- API:            http://localhost:8000/api/health
- API + deps:     http://localhost:8000/api/health/deps
- Docs (OpenAPI): http://localhost:8000/docs
- MinIO console:  http://localhost:9001  (aidoc / aidoc-secret)
- Qdrant:         http://localhost:6333/dashboard

Las migraciones (`alembic upgrade head`) corren automáticamente al arrancar el backend.

### Configuración mínima del `.env`

1. **Auth (obligatorio):** `SECRET_KEY` (32+ chars aleatorios) y
   `SUPERADMIN_EMAIL`/`SUPERADMIN_PASSWORD`. Sin esto la app levanta pero el login
   no deja entrar a nadie. El super-admin se crea solo al arrancar; con él se crean
   las organizaciones (`POST /api/auth/organizations`) y cada admin de org crea a
   sus usuarios (`POST /api/auth/users`). A la app entran los usuarios de una org.
2. **Modelos (obligatorio):** `LLM_API_KEY` y `EMBEDDINGS_API_KEY` con los JWT de
   los endpoints NIM de PCAI (**requiere la VPN**; vencen ~cada 30 días). Sin red
   PCAI se puede apuntar `LLM_URL`/`EMBEDDINGS_URL` a cualquier API compatible con
   OpenAI (Ollama, OpenAI…) cuidando que `EMBED_DIMENSIONS` coincida con el modelo
   de embeddings — si cambia la dimensión hay que recrear la colección de Qdrant.
3. **Qdrant:** el default `http://qdrant:6333` usa el contenedor bundleado (cero
   config). Para compartir el Qdrant de PCAI, cambiar `QDRANT_URL` (VPN mediante).

### Primer uso

1. Entrar a http://localhost:5173 con el super-admin del `.env`.
2. Crear una organización + su admin (por API; el super-admin no tiene org y no ve
   Biblioteca/Chat). Re-loguearse con ese admin.
3. Subir documentos en **Biblioteca** (los catálogos/tarifarios con su checkbox) y
   esperar el estado *Indexado*; luego Chat y Cotizaciones.

Gotcha del dev loop: el indexado corre en el contenedor **worker** (sin reload) —
tras cambiar código de parsers/pipeline hay que `docker compose restart worker`.

### Tests (backend)

```bash
docker compose run --rm --no-deps backend sh -c \
  "pip install -q -r requirements-dev.txt && pytest -m 'not pcai' -q"
```

## Roadmap

| Fase | Estado | Entrega |
|------|--------|---------|
| 0 · Scaffolding              | ✅ | Estructura, docker-compose, FastAPI + healthchecks, Alembic, Qdrant |
| 1 · Ingesta + indexado async | ✅ | Upload manual (pdf/docx/txt/md) → indexado async (ARQ) → listar/borrar/reindexar, con dedup y citas de página |
| 2 · Chat RAG con citas       | ✅ | Chat por streaming (SSE) sobre los documentos, con citas, historial y sesiones |
| 3 · Frontend React           | ✅ | SPA Vite+TS+Tailwind: Biblioteca (upload drag&drop, estado, reindex/borrar) + Chat (streaming SSE, citas, selector de docs) |
| 4 · Auth + multi-tenant      | ✅ | JWT + roles (superadmin/admin/member), organizaciones, aislamiento por org, provisionado por admin |
| 5 · Cotizaciones             | ✅ | Guiada por precedente (multi-precedente + rerank LLM), desde cero, propuesta completa multi-sección, catálogos como fuente de partes/precios, export PDF formato CiiSA |
