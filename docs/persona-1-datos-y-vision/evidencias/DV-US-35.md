# DV-US-35 · Consumir eventos importantes con un worker

## Estado

**Verificada en integración el 25 de octubre de 2026.**

Se implementó un consumidor Python de `important-events` con `PeekLock`,
renovación automática, validación estricta de `RoutingOutcome`, idempotencia y
asentamiento explícito. El worker completa éxitos y duplicados, abandona fallos
recuperables y envía contratos inválidos a DLQ.

## Alcance y límites

El manejador actual valida y registra el `AgentDispatch`. Esto completa el
transporte durable y el despacho, pero todavía no ejecuta CrewAI ni publica una
narración en el WebSocket. Los ejecutores de `danger_simulation`,
`moment_selector`, `narrator` y `recap` se conectarán mediante
`ImportantEventHandler` sin acoplarlos al SDK de Service Bus.

## Archivos

- `application/important_event_worker.py`: puerto, resultado e idempotencia.
- `adapters/messaging/important_event_worker.py`: recepción y asentamiento Azure.
- `scripts/run_important_event_worker.py`: ejecución finita reproducible.
- `tests/test_important_event_worker.py`: éxito, duplicado y contrato inválido.

## Verificación

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest -q apps/backend/tests/test_important_event_worker.py \
  apps/backend/tests/test_routing_transport.py
```

Resultado: **6 pruebas aprobadas en 0,33 segundos**.

En Azure se publicó un gol sintético con el enrutador y luego se ejecutó:

```bash
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/run_important_event_worker.py \
  --max-messages 10 --wait-seconds 10
```

Resultado: un mensaje procesado, cero duplicados, cero abandonados y cero
enviados a DLQ. La cola terminó con cero mensajes activos y cero muertos.

## Configuración y despliegue posterior

Requiere `SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE`,
`IMPORTANT_EVENTS_QUEUE_NAME` y una identidad con `Azure Service Bus Data
Receiver`. Localmente puede usar `az login`. En Azure se recomienda una
identidad administrada y un Container Apps Job escalado por profundidad de
cola. El paquete usa 0,5 vCPU, 1 GiB y escala `0-1`. El primer intento no creó
el Job porque Azure for Students devolvió `TasksOperationsNotAllowed` al usar
ACR Tasks. El script admite Docker local para completar el despliegue.

## Documentación consultada

- Context7: Azure SDK for Python, recepción asíncrona, renovación de bloqueo,
  `complete`, `abandon` y `dead-letter`.
- MCP de Azure: cola real activa, bloqueo de 60 segundos, diez entregas
  máximas, TTL de un día y DLQ habilitada.
