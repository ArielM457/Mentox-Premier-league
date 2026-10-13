# Evidencia técnica de EA-US-08

## Identificación

- **Historia:** EA-US-08 · Procesar el flujo en Azure.
- **Estado:** verificada con dobles de Azure; despliegue y prueba de humo pendientes.
- **Prioridad:** P0.
- **Última verificación:** 9 de octubre de 2026.
- **Responsable:** Persona 2 · Estado y analítica.
- **Requisitos relacionados:** decisión 10 de decisiones tomadas, RNF-02, RNF-03.

## Objetivo comprobado

El procesador consume los eventos aceptados por la ingesta de Persona 1, respeta la marca de tardío, publica snapshots, momentos, retiros y revisiones con partición por partido y guarda un registro del análisis con hashes. Los adaptadores de Event Hubs y Blob Storage funcionan con clientes simulados. El flujo completo está en [integración con Azure](../integracion-azure.md).

## Alcance implementado

- `AnalyticsStreamProcessor` con puertos de publicación, metadatos y escritura.
- `AnalyticsEnvelope` con cuatro tipos de mensaje.
- `EventHubAnalyticsBridge` sobre `AzureEventHubConsumer` y `EventOrderTracker` de Persona 1, sin modificarlos.
- `AzureEventHubInsightPublisher` y `AzureEventHubInsightConsumer` para `match-insights`.
- `AzureBlobAnalyticsWriter` (contenedor `analytics`, sin sobrescritura) y `AzureBlobMatchMetadataProvider` (contenedor `matches`).
- Selección `memory` o `azure` por variables de entorno.
- `infra/azure/analytics.bicep` y su archivo de parámetros de ejemplo.
- `analytics_stream_worker.py` y `analytics_azure_smoke.py`.

## Fuera del alcance

- Alojamiento del procesador en Azure: queda propuesto Azure Container Apps junto con la API de Persona 4.
- Asignación automática de roles.

## Cobertura de criterios

| Criterio | Evidencia | Estado |
|---|---|---|
| Consume la ingesta de Persona 1 con marca de tardío | `test_bridge_connects_persona_1_ingestion_to_the_processor_in_arrival_order` | Cumplido localmente |
| Publica los cuatro tipos con partición por partido | `test_each_event_publishes_a_snapshot_and_new_moments_once`, `test_late_event_publishes_revision_and_withdraws_or_updates_moments`, `test_insight_publisher_partitions_by_match_and_labels_the_message_type` | Cumplido localmente |
| Registro con hashes | `test_finalize_writes_traceable_run_files_with_hashes`, `test_blob_writer_stores_runs_without_overwriting_and_with_hash_metadata` | Cumplido localmente |
| Momentos de Azure iguales al cálculo local | `analytics_azure_smoke.py` compara ambos | **Pendiente** de suscripción |
| Infraestructura sin modificar `main.bicep` ni claves | `test_analytics_bicep_adds_insights_hub_and_containers_without_touching_main`; las pruebas de Persona 1 sobre `main.bicep` siguen pasando | Cumplido como texto; compilación pendiente |

## Reproducción

```bash
.venv/Scripts/python -m pytest apps/backend/tests/test_analytics_stream.py apps/backend/tests/test_analytics_azure.py -q
```

Con recursos desplegados y roles asignados:

```bash
python apps/backend/scripts/analytics_azure_smoke.py
```

## Resultado

```text
test_analytics_stream.py  5 passed
test_analytics_azure.py   8 passed
```

Tiempo de procesamiento local por evento: media 3,2 ms y p95 4,4 ms con 178 eventos.

## Limitaciones y riesgos

- No se compiló la plantilla: el equipo no tiene Azure CLI ni Bicep CLI.
- `list_blobs`, `get_container_client` y `EventData.properties` solo se probaron con dobles.
- El procesador guarda el estado en memoria; si se reinicia, recalcula desde los eventos que vuelva a leer.

## Dependencias

- Una suscripción con permisos para desplegar `main.bicep` y `analytics.bicep`.
- Persona 4: decidir el alojamiento conjunto de la API y el procesador.
