# Evidencia técnica de DV-US-34

## Actualización del 27 de octubre de 2026

El flujo actual usa Roboflow, TeamSpotting y los datos del mismo vídeo MESSI;
GameState queda retirado. El paquete se verifica por SHA-256 y sustituye el
guion de Ariel solo para el partido enlazado al MP4. La reproducción publica
eventos del simulador con procedencia explícita y separación de colas.
La [evidencia híbrida](messi-hibrido-20261027.md) registra las pruebas locales,
la conversión del archivo real y sus límites. La
[prueba real posterior en Azure](messi-azure-20261027/README.md) verifica
el vídeo completo en Chrome con ambas GPU, colas y worker; el WebSocket del
proxy Vite quedó corregido y comprobado con los tres roles Roboflow.
Los apartados siguientes conservan la evolución anterior.

## Identificación

- **Historia:** DV-US-34 · Ejecutar inferencia mientras se reproduce el vídeo.
- **Estado:** recorrido visual completo verificado con MP4 sintético, modelos GPU y transportes Azure; precisión estadística no evaluada.
- **Prioridad:** P0.
- **Última actualización:** 27 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.

## Alcance implementado

El centro oficial de partidos de The Prime Moment puede reproducir un MP4
privado de Blob Storage. Mientras el vídeo está en Play, captura el fotograma
visible cada segundo y lo envía como JPEG al backend. El backend conserva la
clave, invoca la suite GPU de Roboflow y publica cada detección normalizada en
el transporte de observaciones. El consumidor la entrega al WebSocket y la
vista **Partido** muestra las observaciones recibidas junto al vídeo.

La interfaz no crea una pestaña técnica separada para esta experiencia. La
bandeja de observaciones está debajo del vídeo o de la cancha sintética, dentro
de la sesión principal de reproducción. Presenta el estado de captura, el
estado del canal, los fotogramas procesados, detecciones, acciones y los ocho
resultados más cercanos al tiempo visible. Esto permite relacionar cada salida
con lo que está sucediendo en pantalla sin abandonar el partido.

Cuando la fuente es un MP4, cada detección que contiene `bounding_box` se
dibuja sobre el vídeo con etiqueta y confianza. El feed no enumera decenas de
objetos técnicos: agrupa las observaciones por fotograma y produce resúmenes
como “22 jugadores · 2 árbitros · 1 balón”. Los resultados de Roboflow se
presentan explícitamente como evidencia visual y no como pases, goles o cambios
tácticos confirmados.

También se corrigió una mezcla engañosa: los comentarios, momentos y overlays
del partido sintético registrado por el backend ya no se superponen sobre un
MP4 distinto. Esos componentes se conservan únicamente en el fallback de
cancha sintética. El modo vídeo muestra solo resultados recibidos durante la
sesión actual; no reutiliza predicciones precalculadas como si fueran nuevas.

Pause elimina inmediatamente el temporizador del navegador y cierra la sesión
de captura en el backend. Si una solicitud ya estaba ejecutándose, el backend
comprueba nuevamente el estado después de la inferencia y descarta su salida.

## Flujo y colas

1. `Play` habilita la sesión asociada a `match_id`.
2. El navegador captura el `<video>` sin exponer `MENTOX_MODEL_API_KEY`.
3. El backend llama `POST /v1/predict?models=all` de Roboflow Suite.
4. Jugadores, balón y puntos del campo se convierten en observaciones.
5. `VISION_OBSERVATION_TRANSPORT=azure_event_hubs` las publica en
   `vision-observations`; el grupo `backend` las consume.
6. El WebSocket entrega lo consumido a la interfaz.
7. Solo un `MatchEvent` válido y fusionado puede entrar después al enrutador:
   `match-metrics` para telemetría reconstruible o `important-events` para
   jugadas durables. Una detección espacial aislada no se inventa como evento.

La última regla es deliberada: TeamSpotting ya puede producir observaciones
temporales, pero GameState y la resolución de identidad todavía deben aportar
evidencia espacial compatible antes de activar la fusión nominal completa.

## Integración de TeamSpotting

El backend acepta ahora `SOCCERNET_ENDPOINT` y `SOCCERNET_API_KEY`. Antes de
habilitar Play, descarga el mismo MP4 privado configurado para la interfaz y lo
envía una sola vez al servicio SoccerNet T-DEED. Sus predicciones se normalizan
como observaciones `temporal_action`, conservando tiempo de vídeo, etiqueta,
equipo visual, confianza, identificador y procedencia. Se publican mediante el
mismo transporte y WebSocket que las detecciones de Roboflow.

La interfaz presenta nombres comprensibles como “Pase detectado”, “Tiro
detectado” y “Gol detectado”, junto con equipo visual y confianza. También avisa
que atribuir un jugador requiere fusión. No transforma `left` o `right` en un
equipo nominal ni inventa pasador y receptor.

El servicio TeamSpotting amplió su límite de 90 a 240 segundos para aceptar los
MP4 sintéticos comprimidos de 180 segundos. Ariel debe reconstruir y desplegar
esa revisión antes de la prueba completa. La clave compartida por mensajería debe
rotarse y guardarse solo en `SOCCERNET_API_KEY`; no se incorporó al repositorio.

## Archivos

| Archivo | Función |
|---|---|
| `application/live_vision_capture.py` | Estado Play/Pause, cliente del modelo, límite y normalización |
| `adapters/http/integration_router.py` | Fotogramas, vídeo privado, estado y WebSocket |
| `main.py` | Arranque y cierre del productor/consumidor |
| `useVisionCapture.js` | Captura un fotograma por segundo sin solicitudes solapadas |
| `useVisionObservationChannel.js` | Recibe el canal consumido por el backend |
| `MatchCenter.jsx` | Conecta controles, vídeo y captura |
| `LiveExperiencePanels.jsx` | Presenta la bandeja de observaciones dentro de Partido |
| `experience.css` y `match.css` | Bandeja responsive y cajas sobre el vídeo |
| `compose.integration.yml` | Variables de modelo, Blob y colas |
| `test_live_vision_capture.py` | Pruebas del control y normalización |
| `application/teamspotting_analysis.py` | Cliente, descarga privada, caché y acciones temporales |
| `test_teamspotting_analysis.py` | Normalización y configuración opcional de SoccerNet |

## Matriz de aceptación

| Criterio | Evidencia | Estado |
|---|---|---|
| Vídeo privado con fallback | Ruta Blob con OAuth y `VideoSource` opcional | Verificado por código y compilación |
| Play habilita captura | Sesión por `match_id` | Verificado localmente |
| Pause detiene y descarta tardíos | Doble comprobación antes de publicar | Verificado localmente |
| Clave solo en backend | Variable y encabezado creados en Python | Verificado por diseño |
| Máximo un fotograma por segundo | Intervalo frontend y límite backend | Verificado localmente |
| Tres modelos sobre el mismo frame | `models=all` | Verificado por contrato; Azure pendiente |
| Publicación y consumo | `VisionObservationRuntime` | Event Hub real: 2 publicados, 1 aceptado, 1 duplicado y 0 fallos |
| Métricas e importantes separadas | Variables y topología DV-US-29 | Recursos y publicación real verificados |
| Observaciones junto al vídeo | Bandeja integrada en Partido; no existe una pestaña Visión IA | Verificado por código, lint y compilación |
| Cajas sincronizadas | Último fotograma dentro de una tolerancia de 2,5 segundos | Verificado por código y compilación |
| Separación de datos simulados | Los overlays sintéticos no aparecen encima de un MP4 | Verificado por código y compilación |
| Lenguaje comprensible | Detecciones agrupadas por fotograma; no inventa acciones deportivas | Verificado en español e inglés por compilación |
| Acciones de TeamSpotting | Etiqueta, equipo visual, confianza y tiempo sincronizable | Verificado localmente; endpoint Azure pendiente de clave rotada y redespliegue |

El 25 de octubre de 2026 se desplegó la topología aislada de DV-US-29. Event
Hubs y Service Bus están activos y se verificó una publicación real. Esa prueba
demuestra el transporte posterior, pero no reemplaza el recorrido visual
Play/Pause con el endpoint GPU.

## Configuración reproducible

No se debe guardar la clave en Git ni colocarla en variables `VITE_*`.

```bash
export ROBOFLOW_SUITE_ENDPOINT="https://ca-mentox-roboflow-dev.lemonisland-c8dd17c4.northcentralus.azurecontainerapps.io"
export MENTOX_MODEL_API_KEY="<clave-del-equipo>"

export SOCCERNET_ENDPOINT="https://ca-mentox-teamspotting-dev.<entorno>.northcentralus.azurecontainerapps.io"
export SOCCERNET_API_KEY="<clave-rotada-de-teamspotting>"
export SOCCERNET_TIMEOUT_SECONDS=900

export AZURE_BLOB_SERVICE_ENDPOINT="https://stdamonhxwjzbiyupwqc.blob.core.windows.net/"
export VISION_VIDEO_CONTAINER="synthetic-videos"
export VISION_VIDEO_BLOB_NAME="messi/messi-rich-30x180s-20261025/messi-001/match.mp4"

export VISION_OBSERVATION_TRANSPORT="azure_event_hubs"
export EVENT_HUB_FULLY_QUALIFIED_NAMESPACE="eh-damon-dev-hxwjzbiyupwqc.servicebus.windows.net"
export VISION_EVENT_HUB_NAME="vision-observations"
export VISION_EVENT_HUB_CONSUMER_GROUP="backend"

export ROUTING_TRANSPORT="azure"
export EVENT_HUB_NAME="match-events"
export METRICS_EVENT_HUB_NAME="match-metrics"
export SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE="sb-damon-dev-hxwjzbiyupwqc.servicebus.windows.net"
export IMPORTANT_EVENTS_QUEUE_NAME="important-events"

docker compose -f compose.integration.yml up --build
```

Para usar credenciales de servicio en Compose también se requieren
`AZURE_TENANT_ID`, `AZURE_CLIENT_ID` y `AZURE_CLIENT_SECRET`. En desarrollo sin
Azure se puede usar `VISION_OBSERVATION_TRANSPORT=memory`; el comportamiento
Play/Pause no cambia.

## Comandos y resultados

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest -q \
  apps/backend/tests/test_live_vision_capture.py \
  apps/backend/tests/test_observation_playback.py \
  apps/backend/tests/test_vision_observation_transport.py
```

Resultado: **12 pruebas aprobadas en 0,37 segundos**.

La ampliación TeamSpotting se verificó con 16 pruebas dirigidas aprobadas y con
la compilación de producción del frontend. Esta prueba usa dobles locales; no se
registra todavía como una inferencia real contra el endpoint de Ariel.

```bash
cd apps/frontend
npm run lint
npm run build
```

Resultado: compilación aprobada. El lint terminó sin errores y conservó tres
advertencias preexistentes de `set-state-in-effect` en archivos no modificados
por esta historia.

En la revisión del 25 de octubre de 2026 también se eliminó `vision` de la
lista de pestañas del centro del partido. `VisionPanel` se reutilizó como una
bandeja compacta dentro de `pitch-wrap`; no se duplicó el canal WebSocket ni el
temporizador de captura. La decisión sigue la documentación oficial de React:
la conexión externa permanece encapsulada en un hook con limpieza al desmontar.

`python -m compileall` y `git diff --check` también finalizaron correctamente.
La suite completa avanzó hasta 40 % sin fallos, pero se interrumpió porque una
prueba posterior quedó bloqueada, comportamiento ya observado antes de esta
historia. Por ello no se registra como aprobada completa.

```bash
export EVENT_HUB_FULLY_QUALIFIED_NAMESPACE="eh-damon-dev-hxwjzbiyupwqc.servicebus.windows.net"
export VISION_EVENT_HUB_NAME="vision-observations"
export VISION_EVENT_HUB_CONSUMER_GROUP="diagnostics"

UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/vision_event_hubs_smoke.py
```

Resultado Azure: **2 publicaciones, 1 observación aceptada, 1 duplicado, 0
rechazos y 0 fallos de consumidor**. No se creó ningún `MatchEvent`, porque una
observación visual aislada aún no constituye una jugada confirmada.

## Pendientes de integración real

1. Esperar que `messi-001/match.mp4` exista y esté completo en Blob Storage.
2. Confirmar RBAC de lectura del backend sobre `synthetic-videos`.
3. Ejecutar el frontend y verificar Play, Pause y WebSocket con Roboflow T4.
4. Desplegar TeamSpotting y GameState; ambos trabajan por ventana o lote, no por
   un fotograma aislado.
5. Probar la fusión con evidencias compatibles y recién entonces validar que
   `MatchEvent` llega a `match-metrics` o `important-events`.

## Documentación externa consultada

- Context7, documentación oficial de React: sincronización de un elemento de
  vídeo con `useEffect` y limpieza de intervalos.
- Context7, documentación oficial de FastAPI: lectura asíncrona del cuerpo
  binario mediante `Request.body()`.
# Actualización: preparación del modelo antes de Play (2026-10-25)

## Objetivo

Evitar que la primera reproducción comience mientras Azure Container Apps todavía descarga pesos, inicializa CUDA o carga los modelos Roboflow. La captura debe empezar únicamente después de una sonda de disponibilidad satisfactoria.

## Criterios cubiertos

- El frontend mantiene el video pausado mientras prepara el servicio de visión.
- El backend expone `POST /api/v1/integration/live/models/prepare` y valida `/health/ready` del servicio remoto.
- Una respuesta inaccesible, vencida o distinta de `ready` produce HTTP 503 y no habilita la reproducción.
- Se admite `ROBOFLOW_SUITE_API_KEY` por servicio, con compatibilidad para `MENTOX_MODEL_API_KEY`.
- Los despliegues GPU quedan en modo de revisión única para evitar competencia por la T4.
- Ariel dispone de un script `deploy/start/status/stop` que espera la preparación real de TeamSpotting y recuerda volver a escala cero.

## Archivos

- `apps/backend/src/match_intelligence/application/live_vision_capture.py`
- `apps/backend/src/match_intelligence/adapters/http/integration_router.py`
- `apps/backend/tests/test_live_vision_capture.py`
- `apps/frontend/src/api/client.js`
- `apps/frontend/src/screens/MatchCenter.jsx`
- `infra/azure/deploy-gpu-model-common.sh`
- `infra/azure/teamspotting-ariel.sh`
- `docs/persona-1-datos-y-vision/despliegue-modelos-azure-equipo.md`

## Decisiones y límites

- La preparación comprueba disponibilidad; no ejecuta una inferencia ficticia ni publica observaciones.
- TeamSpotting se prepara desde su script porque consume clips, mientras la captura por segundo del frontend usa Roboflow Suite.
- Mantener una réplica mínima en uno elimina el arranque en frío, pero factura GPU mientras permanezca asignada. El script de Ariel incluye un apagado explícito.
- La sonda no sustituye las pruebas de inferencia con material sintético o autorizado.

## Verificación reproducible

```bash
bash -n infra/azure/deploy-gpu-model-common.sh infra/azure/teamspotting-ariel.sh

UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_live_vision_capture.py \
         apps/backend/tests/test_integrated_pipeline_api.py

npm --prefix apps/frontend run build
```

Resultados obtenidos:

- `pytest`: 10 pruebas aprobadas en los módulos seleccionados.
- `vite build`: 58 módulos transformados y compilación terminada correctamente.
- `bash -n`: scripts común y de Ariel sin errores de sintaxis.

# Actualización: preparación automática al iniciar el backend (2026-10-26)

El backend ahora inicia en segundo plano la preparación conjunta de Roboflow,
TeamSpotting y GameState cuando están configurados los tres servicios y el vídeo.
El servidor HTTP no queda bloqueado y una pulsación posterior de Play reutiliza
la tarea en curso en lugar de duplicar la inferencia.

El estado reproducible se expone en `GET /api/v1/integration/status` bajo
`runtime.model_preparation`, con los estados `idle`, `preparing`, `ready` y
`failed`. `VISION_PREPARE_ON_STARTUP=false` permite desactivar expresamente el
comportamiento; `VISION_STARTUP_MATCH_ID` cambia el partido inicial.

Verificación local realizada:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python -m compileall -q apps/backend/src

UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest -q apps/backend/tests/test_live_vision_capture.py \
            apps/backend/tests/test_teamspotting_analysis.py \
            apps/backend/tests/test_gamestate_analysis.py
```

Resultado: compilación correcta y 10 pruebas aprobadas. La suite completa se
interrumpió después del 43 % porque entró en una prueba de larga duración; no se
declara verificada en esta actualización.
