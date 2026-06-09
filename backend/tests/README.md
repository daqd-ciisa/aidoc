# Tests E2E — AIDOC

Dos capas (ver la estrategia de la Fase 5):

| Capa | Archivo | Qué prueba | Depende de PCAI |
|------|---------|------------|-----------------|
| **1 · Plumbing** | `test_e2e_smoke.py` | El flujo completo con LLM/embeddings **falseados** (deterministas). Cañería real: FastAPI, parsers, chunker, Qdrant (en memoria), storage (en memoria), persistencia, SSE, cotizaciones, PDF. | ❌ No |
| **2 · Real** | `test_e2e_pcai.py` | El mismo flujo contra los endpoints **reales** de PCAI (NIM). Aserciones laxas/estructurales. | ✅ Sí (gated) |

La Capa 1 corre sin tokens ni red → ideal para CI y para no depender de los JWT de PCAI (que caducan).

## Correr la Capa 1

Dentro del contenedor backend (tiene todas las deps de la app):

```bash
docker compose exec backend pip install -r requirements-dev.txt   # solo la 1ª vez
docker compose exec backend python -m pytest tests/ -m "not pcai" -v
```

O en un venv local con las deps del backend instaladas:

```bash
cd backend
pip install -r requirements-dev.txt
pytest -m "not pcai"
```

> Nota: `pip install` dentro de un contenedor en marcha se pierde al recrearlo
> (`docker compose down`/`--force-recreate`). Para CI, instalá `requirements-dev.txt`
> en el step de tests; no van en la imagen de producción a propósito.

## Correr la Capa 2 (PCAI real)

Requiere VPN, tokens vigentes en `.env` y el stack arriba:

```bash
AIDOC_RUN_PCAI=1 AIDOC_BASE_URL=http://localhost:8000 \
AIDOC_USER=admin@org.com AIDOC_PASS=... \
pytest -m pcai
```

## Cómo está armado (Capa 1)

- `conftest.py` — setea `DATABASE_URL` a SQLite efímero **antes** de importar la app,
  parchea Qdrant (`:memory:`), storage (dict), embeddings y LLM (fakes), y reemplaza
  la cola ARQ por indexado **inline** (corre la tarea real del worker, sin Redis).
- `fakes.py` — `FakeEmbeddings` (vector determinista 1024-d) y `FakeChatLLM`
  (respuestas canónicas por tarea: chat, extracción, resumen, rerank).
- `test_e2e_smoke.py` — login → upload → indexado → chat SSE → cotización guiada →
  PDF, más aislamiento por tenant.

Para extender la Capa 2, replicá los pasos del smoke usando `httpx` contra
`AIDOC_BASE_URL` y aserciones estructurales (hay respuesta, ≥1 cita, latencia < 10 s).
