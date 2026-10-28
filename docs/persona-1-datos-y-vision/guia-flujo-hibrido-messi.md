# The Prime Moment: Roboflow, TeamSpotting y MESSI

GameState no es necesario y está desactivado por defecto, aunque queden sus
variables antiguas exportadas. Su contenedor se eliminó de Azure. No ejecute
su script de despliegue para esta demo.

## Qué hace cada fuente

- Roboflow Suite procesa el fotograma que se ve durante Play y entrega las
  observaciones de sus modelos player, ball y pitch. Pausa detiene la captura.
- TeamSpotting procesa previamente el MP4 y propone acciones con tiempos y
  confianza. Esas propuestas no confirman por sí solas jugadores ni resultados.
- MESSI entrega los eventos, jugadores y posiciones del mismo archivo de vídeo.
  Se muestran como «Datos del simulador MESSI», no como aciertos de IA.

En Partido se verá, por ejemplo, «Jugador 6 pasa a Jugador 7», con equipo,
resultado y distancia si el simulador los registró. Los números son los slots
0–10 dibujados por MESSI, no dorsales leídos mediante OCR. Un gol solo aparece
si el registro contiene ese resultado. Las velocidades de salida del balón
se indican como simuladas. No se interpolan posiciones escasas para inventar
velocidades o distancia recorrida.

## 1. Archivos necesarios

El directorio del MP4 en Blob Storage debe contener los cinco archivos que
genera nuestro script MESSI:

```text
messi/<lote>/messi-001/
  match.mp4
  events.jsonl
  tracking.jsonl
  metadata.jsonl
  manifest.json
```

El backend descarga estos archivos al iniciar, verifica tamaños y SHA-256,
normaliza los eventos y carga su plantilla. Conserva el MP4 verificado en
memoria para servir sus rangos sin volver a descargarlo por cada petición;
TeamSpotting recibe esos mismos bytes. No utiliza los nombres ni el
guion de Ariel para ese MP4. Solo `synthetic-live-001`, o el identificador
configurado, recibe el vídeo: los demás partidos mantienen su escenario.
Sin Blob configurado o si el paquete no puede verificarse, la representación
sintética de Ariel sigue disponible, sin superponer sus eventos al MP4.
Un error de paquete queda visible en `/api/v1/integration/status`.

## 2. Variables del backend

Todos los exports deben estar en la misma terminal que ejecuta Uvicorn.
Conserve los endpoints y claves específicos de Roboflow y TeamSpotting que
ya tiene el equipo; no use la clave de GameState ni guarde claves en Git.

```bash
cd /home/university/league/Mentox-Premier-league

export SOCCERNET_GAMESTATE_ENABLED=false
unset SOCCERNET_GAMESTATE_ENDPOINT SOCCERNET_GAMESTATE_API_KEY
export VISION_SIMULATOR_ENABLED=auto
export VISION_STARTUP_MATCH_ID=synthetic-live-001
export VISION_PREPARE_ON_STARTUP=true

export AZURE_BLOB_SERVICE_ENDPOINT="https://stdamonhxwjzbiyupwqc.blob.core.windows.net"
export VISION_VIDEO_CONTAINER=synthetic-videos
export VISION_VIDEO_BLOB_NAME="messi/messi-clean-2x180s-20261026/messi-001/match.mp4"

# Mantener configuradas, con sus valores privados existentes:
# ROBOFLOW_SUITE_ENDPOINT y ROBOFLOW_SUITE_API_KEY
# SOCCERNET_ENDPOINT y SOCCERNET_API_KEY
export SOCCERNET_TIMEOUT_SECONDS=1800
```

La sesión Azure CLI o identidad del backend debe tener permiso de lectura de
blobs en la cuenta original, no en la cuenta retirada de GameState. Para la
sesión local del propietario de ese Storage:

```bash
az account set --subscription "7f8bd721-c11f-4469-84db-e00203d28360"
```

Si utiliza colas reales, mantenga las variables ya configuradas:

```bash
export EVENT_TRANSPORT=azure_event_hubs
export VISION_OBSERVATION_TRANSPORT=azure_event_hubs
export EVENT_HUB_FULLY_QUALIFIED_NAMESPACE="eh-damon-dev-hxwjzbiyupwqc.servicebus.windows.net"
export EVENT_HUB_NAME=match-events
export EVENT_HUB_CONSUMER_GROUP=backend
export VISION_EVENT_HUB_NAME=vision-observations
export VISION_EVENT_HUB_CONSUMER_GROUP=backend
export ROUTING_TRANSPORT=azure
export METRICS_EVENT_HUB_NAME=match-metrics
export SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE="sb-damon-dev-hxwjzbiyupwqc.servicebus.windows.net"
export IMPORTANT_EVENTS_QUEUE_NAME=important-events
```

Los permisos y recursos de las colas deben existir; los exports no los crean.
Para probar sin publicar en Azure use `memory` en las tres variables de
transporte. La descarga de Blob e inferencia siguen necesitando sus servicios.

## 3. Ejecutar

Encienda solo Roboflow y TeamSpotting con sus operadores existentes, una réplica
por servicio durante la prueba. No se encendieron automáticamente como parte
de esta implementación. Después reinicie el backend:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  uvicorn match_intelligence.main:app \
  --app-dir apps/backend/src --host 127.0.0.1 --port 8000
```

En otra terminal:

```bash
cd /home/university/league/Mentox-Premier-league/apps/frontend
npm run dev -- --host 127.0.0.1
```

Abra la dirección que indique Vite, entre al partido en vivo y use Play.
La preparación sigue esperando a TeamSpotting si aún analiza el MP4.
Reutiliza el resultado durante la vida de ese backend; todavía no tiene una
caché persistente entre reinicios. Al reanudar vuelve a comprobar la salud de
los servicios para soportar el arranque desde escala cero, sin repetir el
análisis de TeamSpotting. Errores de credenciales o de vídeo se muestran;
no se disimulan con datos de otro partido.

## 4. Verificar

```bash
curl --fail-with-body http://127.0.0.1:8000/api/v1/integration/status
curl --fail-with-body "http://127.0.0.1:8000/api/v1/integration/live/observations?match_id=synthetic-live-001&start_ms=0&end_ms=1000"
curl --fail-with-body "http://127.0.0.1:8000/api/v1/integration/live/analytics?match_id=synthetic-live-001&until_video_ms=1000"
curl --fail-with-body http://127.0.0.1:8000/api/v1/agent-routing/status
```

`runtime.simulator.status` debe ser `ready`, con 170 eventos y 181 cuadros
para este primer MP4. `gamestate.status` debe ser `retired`. Roboflow,
TeamSpotting y MESSI aparecen separados en el panel.
`artifact_scope` debe ser `current_blob_video` y `duration_ms`, `180000`.
Antes de Play es correcto que `frames_received` sea cero.

Los eventos normalizados solo se entregan al filtro al avanzar el vídeo
durante Play. Consultar una ventana o preparar modelos no los envía a las
colas. Pausar detiene esa publicación; reiniciar o volver atrás no vuelve a
contarlos. La visualización reconstruye el tramo solicitado, sin depender de
haber recibido antes el WebSocket.

Al terminar, vuelva a dejar los servicios de inferencia en escala cero según
sus instructivos y compruebe que no quedan réplicas. Conservar Storage/ACR
puede seguir generando costos aunque las GPUs estén apagadas.

## Estado comprobado

La [prueba real en Azure del 27 de octubre](evidencias/messi-azure-20261027/README.md)
reprodujo el MP4 completo en Chrome: Roboflow remoto, 177 predicciones de
TeamSpotting, 164 eventos al filtro, dos jugadas importantes consumidas por
el worker y ninguna entrega pendiente. El WebSocket de Vite quedó corregido
y comprobado con observaciones reales de los tres roles Roboflow.

La conversión del MP4 real descargado y el recorrido HTTP con dobles de
inferencia están probados localmente, incluida la interfaz en Chrome,
español/inglés y móvil. Pasaron 473 pruebas de backend y una quedó omitida.
La validación completa entregó 170 observaciones sin duplicarlas al repetir
el vídeo. La prueba real comprueba funcionamiento y entrega; no mide precisión
estadística de los modelos sobre imágenes estilizadas.
[Evidencia y alcance](evidencias/messi-hibrido-20261027.md).
