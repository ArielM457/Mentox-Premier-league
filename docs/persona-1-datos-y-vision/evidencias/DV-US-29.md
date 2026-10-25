# DV-US-29 · Separar telemetría y eventos importantes

## Estado y resultado

**Estado:** verificada localmente el 23 de octubre de 2026.

El filtro determinista quedó conectado a tres canales con garantías distintas:

1. `match-events` conserva el ingreso que permite reconstruir el procesamiento.
2. `match-metrics` recibe resultados de solo métricas, tolerantes a una pérdida puntual.
3. `important-events` recibe decisiones narrativas, peligro, tiempo muerto y resumen mediante Azure Service Bus.

Los eventos rechazados o duplicados conservan una decisión auditable, pero no crean una cuarta cola. API Management no se añadió: puede proteger una API HTTP pública, pero la clasificación pertenece al backend y en esta etapa no justifica otro recurso con costo.

## Entrada y salida

La entrada es `RoutingEvaluationRequest`. La salida de negocio continúa siendo `RoutingOutcome`; el transporte no cambia el contrato del filtro. `match_id` es la clave de partición de Event Hubs y `decision_id` es el `message_id` de Service Bus.

El botón **Iniciar partido en vivo** ejecuta `/api/v1/matches/{id}/simulation`. Sus seis escenarios pasan por `RoutedEventPipeline`, la misma canalización usada por `/api/v1/agent-routing/evaluate`.

## Decisiones

- Event Hubs se usa para flujos ordenados por partido y datos reconstruibles.
- Service Bus se usa para trabajo importante que debe fallar de forma visible y reintentarse.
- Un fallo de métricas se registra en `telemetry_failures` y no borra el ingreso.
- Un fallo de la cola importante produce error; el backend no confirma una entrega inexistente.
- `ROUTING_TRANSPORT=memory` permite probar sin Azure. `azure` activa los dos Event Hubs y Service Bus con `DefaultAzureCredential`.
- Service Bus está desactivado por defecto en Bicep para evitar costo accidental. Requiere `deployDurableImportantQueue=true`, `what-if` y autorización explícita.

## Archivos

- `apps/backend/src/match_intelligence/application/routing/pipeline.py`
- `apps/backend/src/match_intelligence/adapters/messaging/routing_transport.py`
- `apps/backend/src/match_intelligence/adapters/http/routing_router.py`
- `apps/backend/src/match_intelligence/application/live_simulation.py`
- `apps/backend/src/match_intelligence/adapters/http/match_router.py`
- `apps/backend/tests/test_routing_transport.py`
- `infra/azure/main.bicep`
- `infra/azure/dev.bicepparam.example`
- `infra/azure/README.md`
- `apps/backend/pyproject.toml`
- `apps/backend/uv.lock`

## Criterios y evidencia

| Criterio | Implementación | Verificación |
|---|---|---|
| Conservar ingreso | `publish_ingress` antes del filtro | Dos solicitudes producen dos ingresos |
| Separar métricas | `metrics_only` usa `publish_metrics` | Prueba de canales distintos |
| Proteger importantes | El resto de rutas aceptadas usa `publish_important` | Peligro llega solo a importantes |
| Tolerar fallo de telemetría | Excepción registrada sin rechazar el resultado | `test_metrics_failure_is_observable_but_does_not_lose_ingress` |
| No ocultar fallo durable | Excepción propagada para reintento | `test_important_failure_is_propagated_for_retry` |
| Integrar la experiencia | La simulación HTTP usa el pipeline compartido | Pruebas de experiencia y API |
| Infraestructura reproducible | Event Hub y Service Bus condicional en Bicep | Compilación Bicep correcta |

## Comandos y resultados

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest -q \
  apps/backend/tests/test_routing_transport.py \
  apps/backend/tests/test_agent_routing.py \
  apps/backend/tests/test_match_experience_api.py \
  apps/backend/tests/test_integrated_pipeline_api.py
```

Resultado inicial consolidado: **54 pruebas aprobadas**. Después se añadió la prueba aislada del adaptador Azure; `test_routing_transport.py` terminó con **4 pruebas aprobadas**. Al repetir grupos que mezclan `TestClient` síncrono y clientes ASGI asíncronos reapareció el bloqueo de cierre ya registrado en DV-US-28, por lo que no se presenta ese segundo intento como una suite completa aprobada.

```bash
npm run lint:frontend
npm run build:frontend
```

Resultado: compilación correcta. El linter terminó sin errores y conservó tres advertencias preexistentes de React.

```bash
/home/university/.azure/bin/bicep build infra/azure/main.bicep --stdout
```

Resultado: plantilla compilada correctamente.

## Versiones y documentación consultada

- Python 3.12 mediante `uv`.
- `azure-servicebus` 7.15.0 bloqueado en `uv.lock`.
- Azure SDK for Python: cliente asíncrono de Service Bus, `DefaultAzureCredential`, sender de cola y `ServiceBusMessage`.
- Vite 8.3.3 durante la compilación del frontend.

## Limitaciones y pendientes

- No se desplegaron `match-metrics` ni Service Bus en Azure durante esta verificación.
- Falta ejecutar `az deployment group validate`, `what-if` y `create` con la suscripción elegida.
- Falta asignar `Azure Event Hubs Data Sender` y `Azure Service Bus Data Sender` a la identidad de ejecución.
- La cola Basic no usa detección nativa de duplicados; la idempotencia se conserva mediante `decision_id` y debe comprobarla el consumidor.
- Las salidas actuales de visión siguen siendo observaciones experimentales y no entran a importantes hasta que una política las confirme como `MatchEvent`.
