# Despliegue de AIDOC en HPE PCAI

Empaqueta AIDOC como un **Helm chart** y lo importa en PCAI (wizard *Custom
Frameworks*), siguiendo la guía de HPE (Docker → registry → Helm `.tgz` → import).

A diferencia del ejemplo de la guía (una sola app), AIDOC es **multi-servicio**:

| Servicio   | Imagen                | Expuesto | Notas |
|------------|-----------------------|----------|-------|
| frontend   | `aidoc-frontend`      | ✅ (Istio VirtualService) | nginx: sirve la SPA + proxy `/api` → backend |
| backend    | `aidoc-backend`       | interno  | FastAPI; initContainer corre `alembic upgrade head` |
| worker     | `aidoc-backend` (mismo image, `command: arq`) | interno | indexado async |
| postgres / redis / minio | oficiales | interno  | bundleados con PVC (MVP) |
| **Qdrant** | —                     | —        | ya apunta al Qdrant **de PCAI** (no se despliega) |
| modelos    | —                     | —        | endpoints NVIDIA NIM de PCAI (vía Secret) |

> ⚠️ **Sin auth (riesgo asumido).** AIDOC no tiene login (F4 descartada). Solo
> exponer si el gateway de PCAI exige SSO o es red interna/demo controlada.

## 0. Prerequisitos

`docker`, `helm`, `kubectl` y una cuenta de registry (Docker Hub o Harbor de CIISA).

## 1. Construir y subir las imágenes

Reemplazá `NS` por tu usuario de Docker Hub (o `registry/proyecto` de Harbor):

```bash
NS=tu-usuario
TAG=0.1.0

# Backend (sirve también al worker). Usa backend/Dockerfile.
docker build -t docker.io/$NS/aidoc-backend:$TAG ./backend

# Frontend de producción (nginx + build de la SPA). Usa Dockerfile.prod.
docker build -f frontend/Dockerfile.prod -t docker.io/$NS/aidoc-frontend:$TAG ./frontend

docker login
docker push docker.io/$NS/aidoc-backend:$TAG
docker push docker.io/$NS/aidoc-frontend:$TAG
```

Si el repo es **privado**, creá el pull secret y referencialo en `values.yaml`:

```bash
kubectl create secret docker-registry dockerhub-cred \
  --docker-username=$NS --docker-password=<TOKEN> --docker-email=<EMAIL>
# values.yaml -> imagePullSecrets: [{name: dockerhub-cred}]
```

## 2. Configurar `helm/aidoc/values.yaml`

- `image.namespace`: tu `NS`.
- `secrets.llmApiKey` / `secrets.embeddingsApiKey`: los **JWT de PCAI**
  (vencen ~2026-06-30). Mejor pasarlos al desplegar con `--set` que dejarlos en el archivo.
- `config.qdrantUrl`: ya viene apuntando al Qdrant de PCAI.
- `ezua.virtualService.endpoint`: el host público (ej. `aidoc.${DOMAIN_NAME}`).
- Passwords de `postgres`/`minio`: cambialos para producción.

## 3. Validar y empaquetar

```bash
helm lint   deploy/helm/aidoc
helm template aidoc deploy/helm/aidoc --set image.namespace=$NS   # revisión
helm package deploy/helm/aidoc                                    # -> aidoc-0.1.0.tgz
```

> Sin `helm` instalado podés usar la imagen oficial en Docker:
> `docker run --rm -v "$PWD/deploy/helm:/charts" alpine/helm:3.16.1 lint /charts/aidoc`

## 4. Importar en PCAI

En PCAI → **Import Framework / Custom Frameworks**:

1. **Framework Details**: nombre, descripción, ícono.
2. **Framework Chart**: subir `aidoc-0.1.0.tgz`.
3. **Framework Values**: pegar/editar el `values.yaml` (acá inyectás los JWT reales).
4. **Review** → desplegar.

PCAI hace el `docker pull`, crea los recursos y expone el frontend por Istio en el
`endpoint` configurado.

## 5. Post-deploy

- La API arranca tras `alembic upgrade head` (initContainer) y crea sola la colección
  Qdrant + el bucket MinIO (`lifespan`).
- Probar: abrir el endpoint, subir un documento, ver que pasa a `indexed` y chatear.
- Si el indexado/chat fallan con 401/403: revisar que los JWT de PCAI sigan vigentes.

## Notas / pendientes

- **Producción seria**: mover Postgres/MinIO a servicios gestionados (poner
  `postgres.enabled=false` / `minio.enabled=false` y apuntar las env por Secret),
  agregar HPA, backups de PVC y, sobre todo, **auth** antes de exponer datos reales.
- **Renovar JWT** de PCAI antes del ~2026-06-30.
