# Evidencia técnica de DV-US-07

## Identificación

- **Historia:** DV-US-07 · Publicar eventos en Event Hubs.
- **Estado:** verificada en integración mediante DV-US-15.
- **Prioridad:** P0.
- **Última verificación:** 13 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.
- **Requisitos relacionados:** DV-RF-12, DV-RF-13, DV-RNF-06 y DV-RNF-07.

## Objetivo comprobado

> **Actualización de integración:** el 13 de octubre de 2026 la prueba real publicó dos mensajes, aceptó uno, registró un duplicado y terminó sin rechazos ni fallos. Los tiempos y la salida anonimizada están en [DV-US-15](DV-US-15.md). Las referencias posteriores a Azure pendiente pertenecen al corte local original del 9 de octubre.

El backend dispone de un productor y un consumidor asíncronos para Azure Event Hubs. El productor envuelve cada `MatchEvent 1.0` en el sobre documentado, conserva la identidad deportiva y registra el intento de publicación. El consumidor reconstruye y valida el sobre, entrega una sola vez cada evento deportivo y separa mensajes inválidos, duplicados y fallos del SDK.

La comprobación automatizada usa dobles de los clientes oficiales. También existe una prueba manual de ida y vuelta para ejecutar contra los recursos de DV-US-06. No se afirma que el recorrido de red haya sido verificado mientras esa prueba no se ejecute en una suscripción Azure.

## Alcance implementado

- Contrato `MatchEventEnvelope` con versión, identidad del mensaje, tipo, productor, correlación, tiempo y carga.
- Creación de identificadores independientes para mensaje de transporte y evento deportivo.
- Productor asíncrono `AzureEventHubPublisher`.
- Autenticación sin cadenas de conexión mediante `DefaultAzureCredential`.
- Publicación con `match_id` como clave de partición.
- Registro de producción, inicio y final de publicación.
- Error `EventPublicationError` con diagnóstico reproducible.
- Consumidor asíncrono `AzureEventHubConsumer`.
- Validación del sobre y de `MatchEvent 1.0` mediante Pydantic.
- Deduplicación por `(match_id, event_id)` reutilizando DV-US-04.
- Registros separados de aceptados, rechazados, duplicados y errores del consumidor.
- Medición del tiempo entre producción y recepción.
- Actualización de checkpoint después de registrar cada mensaje recibido.
- Cierre explícito de clientes y credenciales asíncronos.
- Prueba manual que publica dos veces un evento sintético y espera un aceptado y un duplicado.
- Salida Bicep `eventHubFullyQualifiedNamespace` compatible con el constructor del SDK.

## Fuera del alcance

- No se ejecutó la prueba contra un Event Hub real.
- No se midió latencia de red en Azure.
- No se configuró un almacén persistente de checkpoints.
- Los diagnósticos y la deduplicación viven en memoria.
- No se implementó todavía la selección automática entre memoria y Azure; corresponde a DV-US-08.
- No se implementó almacenamiento de artefactos en Blob; corresponde a DV-US-09.
- No se modificó el evento original para añadir datos del transporte.

## Entradas y resultados

| Elemento | Descripción |
|---|---|
| Evento de entrada | `MatchEvent 1.0` validado |
| Configuración | Namespace completo, nombre del event hub y grupo de consumidores |
| Autenticación | `DefaultAzureCredential`, compatible con Azure CLI e identidad administrada |
| Mensaje publicado | `EventData` cuyo cuerpo JSON contiene `MatchEventEnvelope` |
| Clave de partición | `match_id`, para conservar juntas las acciones del partido |
| Evento aceptado | `ReceivedMatchEvent` con carga y tiempos de transporte |
| Rechazo | Secuencia de llegada, tiempo, código y mensaje de validación |
| Duplicado | Identidad del mensaje de reintento y diagnóstico de DV-US-04 |
| Error | Tipo, mensaje y tiempo del fallo de publicación o consumo |

## Sobre de transporte

```json
{
  "message_version": "1",
  "message_id": "msg-001",
  "message_type": "match_event.created",
  "produced_at": "2026-10-09T12:00:00Z",
  "producer": "synthetic-generator",
  "correlation_id": "synthetic-acceptance-001",
  "payload": {
    "schema_version": "1.0",
    "event_id": "evt-001",
    "match_id": "synthetic-acceptance-001",
    "period": 1,
    "clock_ms": 5000,
    "video_time_ms": 7000,
    "type": "pressure",
    "team_id": "team-rio",
    "player_id": "rio-10",
    "start": {"x": 38.0, "y": 35.0},
    "end": null,
    "outcome": "success",
    "source": "synthetic",
    "confidence": null,
    "related_event_ids": []
  }
}
```

Las coordenadas exactas del partido sintético dependen de la semilla. El ejemplo ilustra el contrato, no una captura literal de una ejecución.

## Cambios técnicos

| Archivo | Cambio | Motivo |
|---|---|---|
| `apps/backend/src/match_intelligence/application/transport.py` | Sobre, reloj y creación de mensajes | Mantener el contrato de transporte fuera del SDK de Azure |
| `apps/backend/src/match_intelligence/adapters/messaging/azure_event_hubs.py` | Productor, consumidor, tiempos y diagnósticos | Integrar Event Hubs sin contaminar el dominio |
| `apps/backend/scripts/event_hubs_smoke.py` | Prueba manual de ida y vuelta | Permitir evidencia reproducible contra Azure |
| `apps/backend/tests/test_azure_event_hubs.py` | Once pruebas automatizadas | Verificar contrato, fallos, duplicados, tiempos, factorías y ciclo de vida |
| `apps/backend/pyproject.toml` | Dependencias directas de Event Hubs e identidad | Declarar los SDK usados por el adaptador |
| `apps/backend/uv.lock` | Versiones resueltas | Repetir el entorno |
| `infra/azure/main.bicep` | Salida del namespace completo | Configurar el SDK sin construir nombres fuera de infraestructura |
| `infra/azure/README.md` | Variables y comando de prueba | Documentar la integración sin secretos |

## Diseño y flujo

```text
MatchEvent validado
        │
        ▼
MatchEventEnvelope ── produced_at + message_id
        │
        ▼
AzureEventHubPublisher ── publicación + recibo o fallo
        │
        ▼
Azure Event Hubs
        │
        ▼
AzureEventHubConsumer
        │
        ├── sobre inválido ──> rejected
        └── sobre válido
                │
                ▼
          EventDeduplicator
                │
                ├── repetido ──> duplicates
                └── nuevo ─────> accepted + latencia
```

## Decisiones técnicas

### Sobre independiente del evento

Los campos de transporte no se añaden a `MatchEvent`. `produced_at` mide la creación del mensaje y no reemplaza `clock_ms` ni `video_time_ms`. El consumidor reconstruye el mismo modelo deportivo y la prueba compara igualdad completa.

### Identidades diferentes

`message_id` identifica un intento de transporte. `event_id` identifica el hecho deportivo. Dos reintentos pueden tener mensajes distintos y el mismo evento; por eso la deduplicación continúa usando `(match_id, event_id)`.

### Clave de partición

El productor usa `match_id` como `partition_key`. Esto mantiene los eventos de un mismo partido en una partición mientras la deduplicación protege al consumidor de reintentos.

### Errores observables

Un fallo de `send_batch` produce `EventPublicationError` y un `PublicationFailure`. El objeto original no se modifica. Los errores asíncronos del consumidor se guardan como `ConsumerFailure`; los mensajes mal formados se registran por separado y no detienen los siguientes.

### Tiempos

- `produced_at`: creación del sobre.
- `publication_started_at`: inicio de `send_batch`.
- `published_at`: retorno correcto de `send_batch`.
- `received_at`: procesamiento del mensaje por el consumidor.
- `publication_duration_ms`: tiempo local dentro de la publicación.
- `transport_latency_ms`: diferencia entre recepción y producción.

Los relojes de máquinas distintas pueden tener desfase. La prueba Azure deberá registrar ese límite al interpretar latencias.

### Identidad de Azure

No se admiten cadenas de conexión en el adaptador. `DefaultAzureCredential` permite usar la sesión de Azure CLI durante desarrollo y una identidad administrada en un entorno compartido. Los clientes y la credencial se cierran explícitamente.

## Context7 y documentación vigente

Se consultó Context7 con `/azure/azure-sdk-for-python` antes de implementar:

- Construcción de `EventHubProducerClient` con namespace completo, nombre del hub y credencial.
- Uso asíncrono de `send_batch` con `EventData`.
- Construcción y `receive` de `EventHubConsumerClient`.
- Callbacks `on_event` y `on_error`, posición inicial y checkpoints.
- Uso y cierre de `DefaultAzureCredential` asíncrono.

Después se comprobaron las firmas instaladas mediante introspección local. Las versiones resueltas fueron `azure-eventhub 5.15.1`, `azure-identity 1.26.0` y `aiohttp 3.14.4`. `aiohttp` se declaró directamente porque las credenciales asíncronas lo necesitan como transporte.

## Cobertura de criterios de aceptación

| Criterio | Implementación | Evidencia | Estado |
|---|---|---|---|
| Publicar el sobre documentado | `MatchEventEnvelope` y `AzureEventHubPublisher` | `test_publisher_sends_documented_envelope_and_records_timings` | Cumplido localmente; Azure pendiente |
| Recuperar `MatchEvent 1.0` sin alterar valores | Validación del consumidor | `test_envelope_round_trip_preserves_match_event` y `test_consumer_restores_payload_and_measures_transport_latency` | Cumplido localmente; Azure pendiente |
| Hacer visibles los errores de publicación | `EventPublicationError` y `PublicationFailure` | `test_publication_failure_is_visible_and_does_not_mutate_event` | Cumplido localmente |
| Evitar doble conteo en reintentos | `EventDeduplicator` en el consumidor | `test_retried_event_is_accepted_once_and_duplicate_is_recorded` | Cumplido localmente; Azure pendiente |
| Registrar tiempos para medir latencia | Recibo de publicación y evento recibido | Pruebas de publicación y recepción | Cumplido localmente; medición Azure pendiente |

## Pruebas automatizadas

| Prueba | Comportamiento comprobado |
|---|---|
| `test_envelope_round_trip_preserves_match_event` | Serialización y recuperación sin cambios |
| `test_publisher_sends_documented_envelope_and_records_timings` | Sobre, partición y tiempos de publicación |
| `test_publication_failure_is_visible_and_does_not_mutate_event` | Error observable y evento intacto |
| `test_consumer_restores_payload_and_measures_transport_latency` | Recepción equivalente y latencia |
| `test_invalid_message_is_recorded_without_stopping_later_message` | Rechazo aislado y continuidad |
| `test_retried_event_is_accepted_once_and_duplicate_is_recorded` | Idempotencia entre mensajes |
| `test_consumer_callback_checkpoints_processed_messages` | Checkpoint posterior al procesamiento |
| `test_receive_passes_callbacks_and_position_to_sdk_client` | Configuración del ciclo de recepción |
| `test_consumer_sdk_error_is_recorded` | Error asíncrono del SDK visible |
| `test_close_releases_client_and_owned_credential` | Liberación de clientes y credenciales |
| `test_default_credential_factories_can_be_created_and_closed` | Transporte asíncrono disponible y factorías construibles |

## Reproducción local

Desde la raíz del repositorio:

```bash
uv sync --project apps/backend --extra dev
UV_CACHE_DIR=/tmp/mentox-uv-cache uv run \
  --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_azure_event_hubs.py -q

UV_CACHE_DIR=/tmp/mentox-uv-cache uv run \
  --project apps/backend --python 3.12 \
  pytest apps/backend/tests -q
```

## Reproducción en Azure pendiente

Después de desplegar DV-US-06 y asignar `Azure Event Hubs Data Owner`:

```bash
export EVENT_HUB_FULLY_QUALIFIED_NAMESPACE="<namespace>.servicebus.windows.net"
export EVENT_HUB_NAME="match-events"
export EVENT_HUB_CONSUMER_GROUP="diagnostics"

uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/event_hubs_smoke.py
```

Resultado esperado:

```json
{
  "published": 2,
  "publication_failures": 0,
  "accepted": 1,
  "duplicates": 1,
  "rejected": 0,
  "consumer_failures": 0
}
```

La salida real incluirá también identificadores sintéticos y tiempos medidos.

## Entorno verificado

| Componente | Versión |
|---|---|
| Python | 3.12.13 |
| uv | 0.11.32 |
| pytest | 9.1.1 |
| azure-eventhub | 5.15.1 |
| azure-identity | 1.26.0 |
| aiohttp | 3.14.4 |
| Pydantic | 2.12.5 |
| Azure real | No utilizado |

## Resultado

Pruebas específicas de DV-US-07:

```text
...........                                                              [100%]
11 passed
```

Suite completa después de DV-US-07:

```text
61 passed
```

## Limitaciones y riesgos

- No existe evidencia todavía de publicación o consumo en Azure.
- Sin un checkpoint store, el progreso no persiste entre procesos.
- El registro de deduplicación se pierde al reiniciar y no se comparte entre réplicas.
- La prueba manual espera cinco segundos para que el consumidor reclame particiones; una red lenta puede requerir más tiempo.
- Cancelar el consumidor termina la prueba, pero no representa un servicio de larga duración.
- La latencia usa relojes locales; máquinas desincronizadas pueden producir valores engañosos.
- `DefaultAzureCredential` puede probar varias fuentes de identidad antes de fallar; los diagnósticos no deben registrar tokens.
- La política de reintentos internos del SDK conserva sus valores predeterminados y deberá ajustarse después de medir Azure.

## Dependencias y siguientes pasos

- Desplegar DV-US-06 y asignar RBAC a la identidad de prueba.
- Ejecutar `event_hubs_smoke.py` y anexar la salida sin secretos.
- Incorporar Blob Checkpoint Store si el consumidor necesita reanudación persistente.
- DV-US-08 seleccionará memoria o Azure mediante configuración.
- DV-US-05 y Persona 2 deberán procesar los aceptados después de deduplicar.
