# Integración de la analítica con Azure

La analítica funciona igual en local y en Azure: el dominio no conoce Azure y los adaptadores se eligen por configuración. Este documento describe el flujo integrado, cómo desplegarlo y qué falta comprobar con una suscripción real.

## Flujo

```text
Generador sintético o vídeo (Persona 1)
        │  MatchEventEnvelope
        ▼
Event Hubs · match-events ──────────────── grupo backend
        │
        ▼
AzureEventHubConsumer (Persona 1): valida y deduplica
        │
        ▼
EventOrderTracker (Persona 1): marca tardíos
        │
        ▼
EventHubAnalyticsBridge → AnalyticsStreamProcessor (Persona 2)
        │   MatchStateEngine, detectores y motor de atención
        │
        ├──► Event Hubs · match-insights
        │        match_snapshot.updated
        │        insight_candidate.proposed
        │        insight_candidate.withdrawn
        │        match_state.revised
        │     grupos: narrative (Persona 3), experience (Persona 4), diagnostics
        │
        └──► Blob Storage · analytics/<match_id>/<run_id>/
                 final-snapshot.json, state-timeline.jsonl, candidates.jsonl,
                 withdrawals.jsonl, attention-decisions.jsonl, revisions.jsonl, run.json

Blob Storage · matches/<match_id>/   → metadatos del partido (guardados por Persona 1)
Blob Storage · models/<modelo>/current.json → modelos validados (opcional)
```

Cada mensaje de `match-insights` usa `match_id` como clave de partición, así que los mensajes de un partido llegan en orden. El sobre `AnalyticsEnvelope` lleva `message_type`, `correlation_id` (el partido), `source_event_id` y la carga útil. Un consumidor debe tratar `insight_candidate.proposed` como alta o actualización por `candidate_id`, e `insight_candidate.withdrawn` como baja. Las bajas ocurren cuando un evento tardío o corregido cambia la jugada.

`run.json` incluye versiones de motor y atención, política de tardíos, estado de los modelos de valor, resumen de tiempos de procesamiento y el SHA-256 de cada archivo del registro.

## Recursos

`infra/azure/analytics.bicep` se despliega en el mismo grupo de recursos que `main.bicep` y reutiliza su namespace y su cuenta de Storage sin modificarlos:

- Event hub `match-insights`, 2 particiones, 1 día de retención (parámetro `insightsRetentionDays`).
- Grupos de consumidores `narrative`, `experience` y `diagnostics`.
- Contenedores privados `analytics` y `models`.

No hay claves ni cadenas de conexión. Igual que en la plantilla de Persona 1, la autenticación local por clave está deshabilitada y las aplicaciones usan `DefaultAzureCredential` con roles RBAC.

## Despliegue

Primero se despliega `main.bicep` según `infra/azure/README.md`. Después:

```bash
cp infra/azure/analytics.bicepparam.example infra/azure/analytics.bicepparam
```

Complete `eventHubNamespaceName` y `storageAccountName` con las salidas del despliegue anterior:

```bash
az deployment group show --name "mentox-data-vision" --resource-group "<grupo>" --query properties.outputs --output json
```

Valide, previsualice y despliegue:

```bash
az deployment group validate --resource-group "<grupo>" --template-file infra/azure/analytics.bicep --parameters infra/azure/analytics.bicepparam
```

```bash
az deployment group what-if --resource-group "<grupo>" --template-file infra/azure/analytics.bicep --parameters infra/azure/analytics.bicepparam
```

```bash
az deployment group create --name "mentox-analytics" --resource-group "<grupo>" --template-file infra/azure/analytics.bicep --parameters infra/azure/analytics.bicepparam
```

## Roles

La identidad que ejecuta el procesador necesita, como mínimo:

- `Azure Event Hubs Data Receiver` sobre `match-events` y `Azure Event Hubs Data Sender` sobre `match-insights`. Para pruebas, `Azure Event Hubs Data Owner` sobre el namespace.
- `Storage Blob Data Reader` sobre `matches` y `models`, y `Storage Blob Data Contributor` sobre `analytics`.

## Variables

Solo nombres y endpoints:

| Variable | Valor |
|---|---|
| `EVENT_HUB_FULLY_QUALIFIED_NAMESPACE` | `<namespace>.servicebus.windows.net` |
| `EVENT_HUB_NAME` | `match-events` |
| `EVENT_HUB_CONSUMER_GROUP` | `backend` para el procesador; `diagnostics` para la prueba de humo |
| `INSIGHTS_EVENT_HUB_NAME` | `match-insights` |
| `INSIGHTS_CONSUMER_GROUP` | `diagnostics` (prueba de humo) |
| `AZURE_BLOB_SERVICE_ENDPOINT` | `https://<cuenta>.blob.core.windows.net` |
| `ANALYTICS_OUTPUT` | `memory` o `azure` (fábrica de `insights_configuration.py`) |
| `ANALYTICS_BLOB_CONTAINER` | `analytics` |
| `VALUE_MODELS_SOURCE` | `none` o `blob` |
| `ANALYTICS_IDLE_SECONDS` | Segundos sin eventos antes de guardar el registro de un partido (30) |

## Procesador continuo

```bash
python apps/backend/scripts/analytics_stream_worker.py
```

Imprime una línea JSON por evento con llegada (`on_time` o `late`), resultado (`applied`, `rebuilt` o `duplicate`), mensajes publicados, latencia de transporte y tiempo de procesamiento. Al quedar inactivo un partido, guarda su registro en `analytics`.

## Prueba de humo de extremo a extremo

```bash
python apps/backend/scripts/analytics_azure_smoke.py
```

La prueba:

1. Guarda un partido sintético nuevo en `matches` con el adaptador de Persona 1.
2. Publica sus eventos en `match-events` con un tardío (`evt-005` después de `evt-007`) y un duplicado (`evt-001`).
3. Procesa el flujo y escucha `match-insights`.
4. Guarda el registro en `analytics`.
5. Compara los momentos recibidos desde Azure con el cálculo local y falla si no coinciden.

La salida incluye mensajes por tipo, tardíos, duplicados, latencia de transporte de cada mensaje y ubicación de los archivos.

## Qué está verificado

| Comprobación | Dónde | Estado |
|---|---|---|
| Publicador de `match-insights`: partición por partido, propiedad `message_type`, registro de fallos | `test_insight_publisher_partitions_by_match_and_labels_the_message_type`, `test_insight_publication_failure_is_recorded_and_raised` | Local con cliente simulado |
| Consumidor de `match-insights`: validación del sobre y latencia | `test_insight_consumer_validates_envelopes_and_measures_transport` | Local con cliente simulado |
| Escritor de `analytics` sin sobrescritura y con hash | `test_blob_writer_stores_runs_without_overwriting_and_with_hash_metadata` | Local con cliente simulado |
| Lectura de metadatos desde `matches` | `test_metadata_provider_reads_matches_stored_by_persona_1` | Local con cliente simulado |
| Selección `memory` o `azure` y errores de configuración | `test_output_configuration_*` | Local |
| Puente con la ingesta de Persona 1, incluido un tardío | `test_bridge_connects_persona_1_ingestion_to_the_processor_in_arrival_order` | Local |
| Plantilla con hub, grupos y contenedores, sin claves | `test_analytics_bicep_adds_insights_hub_and_containers_without_touching_main` | Lectura del texto; sin compilar |
| Despliegue, roles y prueba de humo | `analytics.bicep`, `analytics_azure_smoke.py` | **Pendiente**: requiere suscripción |

En este equipo no hay Azure CLI ni Bicep CLI, así que la plantilla no se compiló. Antes de desplegar hay que ejecutar `az bicep build --file infra/azure/analytics.bicep`.

## Rendimiento medido en local

Procesador completo (estado, snapshot y atención) con publicador en memoria, Python 3.13.9 en Windows 11:

| Partido | Eventos | Media por evento | p95 | Máximo |
|---|---|---|---|---|
| Aceptación | 10 | 1,0 ms | 1,5 ms | 1,5 ms |
| Escenario de analítica | 178 | 3,2 ms | 4,4 ms | 25,6 ms |

El snapshot más grande publicado ocupó 106 KB, por debajo del límite de 1 MB por mensaje de Event Hubs Standard. Falta medir la latencia de transporte real con la prueba de humo.

## Alojamiento propuesto

El procesador es un proceso Python de larga duración. La propuesta es ejecutarlo en Azure Container Apps con identidad administrada, en la misma imagen que la API de Persona 4, para mantener el monolito modular acordado. También puede correr en una máquina del equipo durante la demo, porque solo necesita las variables anteriores y una identidad con los roles. La decisión corresponde al equipo junto con Persona 4.
