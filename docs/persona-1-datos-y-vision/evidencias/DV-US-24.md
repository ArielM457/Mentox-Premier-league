# Evidencia técnica de DV-US-24

## Identificación

- **Historia:** DV-US-24 · Transportar observaciones durante la transmisión.
- **Estado:** verificada localmente; infraestructura Azure desplegada y prueba de datos pendiente con la identidad autorizada.
- **Fecha:** 14 de octubre de 2026.
- **Requisitos relacionados:** DV-RF-12, DV-RF-13, DV-RF-17 a DV-RF-20, DV-RNF-02, DV-RNF-03, DV-RNF-06 y DV-RNF-07.

## Resultado

El flujo en ejecución queda separado en dos canales:

```text
MatchEvent confirmado → match-events
Observación visual → vision-observations → backend → WebSocket → frontend
```

El worker no necesita credenciales de Event Hubs cuando usa la entrada HTTP del backend. En modo Azure, esa entrada publica en `vision-observations`; el consumidor del backend valida y entrega la observación a una cola acotada. En modo `memory`, la misma entrada llega directamente a la cola local.

WebSocket es únicamente la última milla hacia el navegador. No reemplaza Event Hubs ni expone credenciales de Azure al frontend.

## Contrato de observación

Cada sobre conserva:

- `schema_version`;
- `observation_id`;
- `source`;
- `kind`;
- `timestamp_ms` del vídeo;
- `payload` original;
- `produced_at` del transporte.

No contiene `event_id` ni se transforma en `MatchEvent`. El `payload` puede conservar `track_id`; `player_id` permanece ausente o nulo sin evidencia nominal.

## Infraestructura

Se agregó `vision-observations` al namespace Standard existente, con dos particiones, un día de retención y grupos `backend` y `diagnostics`.

La primera previsualización de `main.bicep` mostró diferencias administradas por Azure en recursos existentes. Para evitar cambios laterales se creó `vision-observations.bicep`, que referencia el namespace como `existing` y crea únicamente los tres recursos necesarios.

Resultados:

- compilación Bicep: aprobada;
- `validate`: aprobado;
- `what-if`: únicamente tres creaciones y recursos existentes ignorados;
- despliegue `mentox-vision-observations`: `Succeeded`;
- prueba desde la identidad de Codex: rechazo esperado por falta de `Send`;
- prueba con el principal autorizado: pendiente.

## Componentes

| Archivo | Responsabilidad |
|---|---|
| `realtime_observations.py` | Sobre, deduplicación, historial y colas acotadas |
| `azure_vision_observations.py` | Productor y consumidor asíncronos de Event Hubs |
| `vision_runtime.py` | Selección `memory`/`azure_event_hubs` y ciclo de vida |
| `integration_router.py` | Entrada HTTP, estado y WebSocket |
| `realtime_replay_worker.py` | Utilidad CLI opcional para validar el canal sin interfaz |
| `observation_playback.py` | Reproducción de diagnóstico gobernada por Play, pausa y salto |
| `roboflow-sports/run_inference.py` | Publicación opcional al terminar cada detección y medición del retraso |
| `vision_event_hubs_smoke.py` | Ida y vuelta real, duplicado y barrera contra `MatchEvent` |
| `vision-observations.bicep` | Despliegue incremental seguro |

## Configuración

Modo local:

```bash
export VISION_OBSERVATION_TRANSPORT=memory
```

Modo Azure:

```bash
export VISION_OBSERVATION_TRANSPORT=azure_event_hubs
export EVENT_HUB_FULLY_QUALIFIED_NAMESPACE="<namespace>.servicebus.windows.net"
export VISION_EVENT_HUB_NAME="vision-observations"
export VISION_EVENT_HUB_CONSUMER_GROUP="backend"
```

La identidad se obtiene mediante `DefaultAzureCredential`; no se guardan claves en Git.

## Prueba local

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 pytest -q
```

Resultado histórico de DV-US-24: `161 passed in 0.82s`. La ampliación de control
de reproducción y su total vigente se registran en DV-US-25.

También aprobaron las dos compilaciones Bicep, `py_compile`, `node --check`, `docker-compose config --quiet` y `git diff --check`.

## Prueba real pendiente

Desde la terminal que conserva las variables del principal de servicio autorizado:

```bash
export EVENT_HUB_FULLY_QUALIFIED_NAMESPACE="eh-damon-dev-hxwjzbiyupwqc.servicebus.windows.net"
export VISION_EVENT_HUB_NAME="vision-observations"
export VISION_EVENT_HUB_CONSUMER_GROUP="diagnostics"

UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/vision_event_hubs_smoke.py
```

Se esperan dos publicaciones, un aceptado, un duplicado, cero rechazos, cero fallos y cero `MatchEvent` creados.

## Límites

- Event Hubs desacopla y retiene, pero no acelera los modelos.
- Roboflow ya puede emitir por cuadro; su retraso en CPU seguirá creciendo respecto al vídeo.
- SoccerNet todavía entrega acciones después de procesar y agregar clips; convertirlo en spotting incremental requiere recalibrar ventanas y NMS.
- La fusión continua debe esperar observaciones compatibles dentro de una ventana y emitir candidatos, no hechos.
- La cola del backend es memoria efímera; Event Hubs conserva el registro transportado durante un día.

## Context7

Se consultó la documentación vigente del SDK de Azure para Python. La implementación utiliza clientes asíncronos, `DefaultAzureCredential`, `send_batch`, callbacks `on_event`/`on_error`, posición `@latest`, cierre explícito y checkpoint posterior al procesamiento.
