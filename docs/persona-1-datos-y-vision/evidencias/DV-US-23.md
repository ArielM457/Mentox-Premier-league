# Evidencia técnica de DV-US-23

## Identificación

- **Historia:** DV-US-23 · Integrar el pipeline en el backend oficial.
- **Estado:** backend y API HTTP verificados localmente; Compose y frontend fuera de esta prueba.
- **Fecha:** 23 de octubre de 2026.
- **Requisitos relacionados:** DV-RF-10, DV-RF-17 a DV-RF-20, DV-RNF-02 y DV-RNF-03.

## Resultado

El backend oficial incorpora un router que carga y cachea las exportaciones reales de Roboflow Sports, SoccerNet y DV-US-21. La interfaz técnica consume este router y presenta observaciones alrededor del tiempo actual del vídeo permitido.

La separación se mantiene: eventos sintéticos, observaciones y candidatos aparecen en canales diferentes. El candidato conserva sus fuentes, track 140 y `player_id=None`; el contador de `MatchEvent` visual permanece en cero.

## API

| Ruta | Uso |
|---|---|
| `GET /api/v1/integration/status` | Medio, modelos, tiempos, candidatos y configuración del runtime |
| `GET /api/v1/integration/timeline` | Detecciones, acciones y candidatos dentro de una ventana temporal |
| `GET /media/integration-video.mp4` | Vídeo permitido |
| `/api/integration/video-sync/*` | Reproducción, pausa, salto, reinicio y registro técnico |

La consulta limita la respuesta espacial a un máximo configurable de 500 elementos e informa si fue truncada.

## Archivos

| Archivo | Cambio |
|---|---|
| `application/integrated_pipeline.py` | Carga, validación del medio, resumen y ventanas temporales |
| `adapters/http/integration_router.py` | Endpoints oficiales |
| `main.py` | Registro del router en FastAPI |
| `video_sync_diagnostic/*` | Cliente técnico conectado y vídeo autorizado |
| `test_integrated_pipeline_api.py` | Contrato HTTP y barrera contra hechos inventados |
| `Dockerfile.integration` | Imagen Python 3.12 |
| `compose.integration.yml` | Servicio, variables y volúmenes de solo lectura |

## Ejecución

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  uvicorn video_sync_diagnostic.app:app \
  --app-dir experiments --host 127.0.0.1 --port 8018
```

Abra `http://127.0.0.1:8018` y salte a 19,7 segundos.

### Aceptación del backend sin frontend

```bash
bash experiments/run-backend-integration.sh
```

El lanzador ejecuta los modelos, recalcula siempre la fusión, valida las
huellas de entrada, corre la suite, inicia FastAPI temporalmente y consulta por
HTTP el estado y la línea temporal. La guía completa está en
`docs/persona-1-datos-y-vision/guia-integracion-backend.md`.

La revalidación del 23 de octubre, usando los artefactos existentes para evitar
repetir la inferencia, obtuvo:

| Comprobación | Resultado |
|---|---:|
| Estado HTTP | `ready` |
| Detecciones espaciales | 16.018 |
| Acciones temporales | 127 |
| Candidatos de fusión | 1 |
| `MatchEvent` visual publicado | 0 |
| Suite del backend | 162 aprobadas |

El archivo `backend-integration-api.json` conserva la respuesta resumida y el
paquete `evidencias-generadas/mentox-modelos-20261023T143058Z.tar.gz` reúne los
artefactos sin incluir el vídeo ni secretos.

## Docker

```bash
docker-compose -f compose.integration.yml config
docker-compose -f compose.integration.yml up --build
```

La configuración Compose fue validada. La construcción requiere `sudo` para acceder al daemon en este equipo y queda como prueba manual. Los artefactos se montan como solo lectura y no forman parte de la imagen.

## Pruebas

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_integrated_pipeline_api.py \
         experiments/video_sync_diagnostic/test_app.py -q
```

Resultado específico: `9 passed in 0.31s`.

La suite vigente finalizó con `162 passed in 2.96s` durante el recorrido
consolidado. Uvicorn inició correctamente en `127.0.0.1:8023` y respondió las
dos consultas de aceptación. También aprobaron la compilación Python, la
sintaxis Bash y `git diff --check`.

## Cobertura

| Criterio | Evidencia | Estado |
|---|---|---|
| Estado de los componentes | `/status` y prueba HTTP | Cumplido |
| Ventana del mismo medio | SHA-256 común y `/timeline` | Cumplido |
| Trazabilidad e identidad ausente | Fuentes, track 140 y sin jugador | Cumplido |
| Ningún candidato es hecho | `match_events_published=0` | Cumplido |
| Interfaz conectada | Página consume la API oficial | Cumplido localmente |
| Inicio directo o Compose | Inicio directo y consultas HTTP reales | Cumplido directamente; Compose pendiente |

## Limitaciones

- Las inferencias son previas; no son tiempo real.
- Roboflow tardó aproximadamente 11,5 minutos en CPU y SoccerNet 1,5 minutos.
- El frontend no se ejecutó en esta aceptación por decisión de alcance.
- Event Hubs y Blob se muestran como configuración; sus operaciones reales están verificadas en DV-US-22.

## Context7

Se consultó la documentación vigente de FastAPI. Se aplicó `APIRouter` con `include_router` y se evitaron controladores `on_event` obsoletos. Los documentos se cargan de forma perezosa y se cachean al primer acceso.
