# Evidencia técnica de EA-US-12

## Identificación

- **Historia:** EA-US-12 · Desplegar la analítica en Azure con datos ficticios en Supabase.
- **Estado:** verificada en local y en Azure, incluido el flujo continuo con Event Hubs.
- **Prioridad:** P1.
- **Última verificación:** 18 de octubre de 2026.
- **Responsable:** Persona 2 · Estado y analítica.
- **Requisitos relacionados:** RNF-01 a RNF-03, la decisión 10 (Event Hubs y Blob Storage) y el requisito del equipo de desplegar en Azure.

## Objetivo comprobado

La API usa el motor real de Persona 2 en vez de la analítica provisional y lee los partidos de una base PostgreSQL (Supabase). Un script despliega en Azure todos los servicios de la analítica y otro carga datos ficticios. Las guías completas están en [despliegue en Azure y Supabase](../despliegue-azure-supabase.md).

## Cobertura de criterios

| Criterio | Evidencia | Estado |
|---|---|---|
| La API responde con la analítica real y los contratos de Persona 4 | `test_adapter_returns_presentation_contracts_with_the_same_facts`, `test_api_routes_work_with_the_real_engine`; 70 de las 71 pruebas de Persona 4 pasan con el motor real (la otra depende del identificador provisional `moment-evt-006`) | Cumplido |
| Sin variables, la API se comporta igual que antes | `test_default_registry_keeps_the_provisional_engine_by_default` y las 71 pruebas de Persona 4 con el motor provisional | Cumplido |
| Los momentos de Persona 2 tienen titular legible en los dos idiomas | `test_provisional_narrative_names_every_persona_2_moment` | Cumplido |
| Los contratos se guardan y se leen iguales | `test_event_rows_round_trip_every_field`, `test_metadata_rows_round_trip_with_roster_order`, `test_observation_and_identity_rows_round_trip`, `test_seeded_matches_read_back_identical`, `test_seeded_tracking_gives_the_same_tracks` | Cumplido |
| El esquema se aplica varias veces y la carga no duplica | Fixture `store` (aplica dos veces), `test_reseeding_replaces_instead_of_duplicating` | Cumplido |
| Las vistas exponen decisiones, métricas y avisos | `test_views_expose_the_analysis` | Cumplido |
| El procesador continuo usa Supabase además de Blob | `test_stream_worker_sinks_store_its_run_and_find_metadata`, `test_first_available_metadata_provider_falls_back_in_order`, `test_fan_out_writer_writes_every_file_everywhere` | Cumplido con dobles de Event Hubs |
| No se mezclan datos de partidos | `test_store_rejects_data_of_another_match` | Cumplido |
| La API carga partidos y seguimiento desde la base | `test_api_loads_matches_and_tracking_from_the_database` | Cumplido |
| Las imágenes se construyen y la interfaz llega a la API, incluido el canal en directo | `docker build` de las dos imágenes y prueba manual con las dos en una red de Docker | Cumplido en local |
| El script sigue los pasos en orden y no expone la cadena de Supabase | Ejecución con dobles de `az`, `docker` e `Invoke-RestMethod`; la carga real corrió contra PostgreSQL local | Cumplido con dobles |
| Carga de datos en Supabase | `supabase_seed.py --schema` contra el proyecto real: 2 partidos, 49 222 observaciones y 2 análisis; la consulta de `attention_decisions` devuelve los momentos | Cumplido |
| Plantilla aceptada por Azure | `what-if` (20 recursos para crear y 3 asignaciones de roles que no se pueden calcular antes) y `az deployment group validate` de las dos fases | Cumplido |
| Flujo continuo en Azure | Flujo continuo verificado el 25 de octubre de 2026: el trabajo `replay` publicó en `match-events` los 178 eventos del partido de analítica a 8× (como `synthetic-analytics-001-live-20261026003858`). El procesador los aplicó todos a tiempo, con un transporte medio de 51 ms (p95 71 ms) y un procesamiento medio de 27 ms (p95 35 ms). Propuso momentos en 19 eventos y, 30 s después del último, guardó el registro `run-c57436ad-…` con 7 archivos en Blob y en Supabase. | Cumplido |
| Despliegue en Azure | Tres intentos. Primero, Azure creó el entorno en modo Express y rechazó el trabajo `replay`. Después suspendió el cómputo del entorno recreado con el mismo nombre (`ManagedClusterSuspended`). Por último, la API no alcanzaba Supabase porque la cadena era la directa, solo IPv6. Con la plantilla en modo `WorkloadProfiles`, el entorno `…-wp`, la cadena del Session pooler y la API resistente a la base, el 25 de octubre de 2026, en Azure for Students (`eastus2`), el entorno `cae-mentoxp2-demo-wp` sigue activo, la API lee los 3 partidos y su seguimiento desde Supabase, y la interfaz, el análisis de momentos y la previa responden (imagen `0635142`). | Cumplido |

## Decisiones técnicas

- **Supabase solo como base de datos.** Event Hubs sigue siendo el canal y Blob guarda los registros (decisión 10). El esquema es PostgreSQL estándar.
- **Esquema propio.** `match_analytics` no se expone en la API de datos de Supabase y tiene RLS sin políticas; solo el backend entra con la cadena.
- **Tablas iguales a los contratos.** Se guardan `MatchMetadata`, `MatchEvent`, `VisualTrackObservation` y `ResolvedVisualIdentity` tal como los define Persona 1. El análisis se guarda con los mismos archivos que en Blob; las vistas los convierten en filas.
- **Adaptador en lugar de cambiar contratos.** `PresentationAnalytics` entrega a la API de Persona 4 el subconjunto que conoce. Las razones, señales y componentes siguen en `match-insights`.
- **El escenario vuelve a `src`.** Desde la unión con `main`, la API de Persona 4 lo carga al arrancar, y el código de producción no puede importar desde `tests`.
- **Dos fases en Bicep.** Las Container Apps necesitan que las imágenes ya existan en el registro.
- **Secreto fuera de la línea de comandos.** La cadena de Supabase pasa a Azure en un archivo temporal de una carpeta privada y queda como secreto de Container Apps. Una revisión de seguridad automática señaló que en Linux `/tmp` deja el archivo legible por otros usuarios; se corrigió con permisos 700 y 600 antes de escribirlo.

## Reproducción

```bash
.venv/Scripts/python -m pytest apps/backend/tests -q
```

Con un PostgreSQL desechable (nunca el proyecto de Supabase, porque la prueba borra el esquema):

```bash
SUPABASE_TEST_DB_URL=postgresql://postgres@127.0.0.1:55432/postgres .venv/Scripts/python -m pytest apps/backend/tests -q
```

```bash
docker build -t mentox-local/match-intelligence-api:test apps/backend
docker build -t mentox-local/match-intelligence-web:test apps/frontend
```

## Resultado

```text
Sin base de prueba: 337 passed, 8 skipped
Con PostgreSQL 18 local: 344 passed, 1 skipped
Carga de datos: 2 partidos, 188 eventos, 49 222 observaciones, 2 análisis (9 archivos cada uno)
Imágenes: match-intelligence-api 512 MB, match-intelligence-web 77 MB
Estado con seguimiento del partido completo: 115 a 145 ms
```

El salto omitido sin base es la prueba de Postman de Persona 4, que ya se omitía antes.

## Versiones

| Componente | Versión |
|---|---|
| PostgreSQL local | 18.1 (Supabase usa 15 o 17; el esquema no usa funciones nuevas) |
| psycopg | 3.3.6 |
| uv | 0.13.1 (regeneró `uv.lock`: solo añade `psycopg` y `psycopg-binary`) |
| Docker | 29.8.2 |
| Imágenes base | `python:3.12-slim`, `node:22-alpine`, `nginx:1.27-alpine` |

## Limitaciones y riesgos

- Context7 no estaba disponible. Las propiedades de Bicep y Container Apps se confirmaron con la validación de Azure y con la referencia de `Microsoft.App/managedEnvironments` 2026-07-01, cuyos valores de `environmentMode` son `ConsumptionOnly`, `WorkloadProfiles`, `Express` y `Archived`.
- Azure ahora crea los entornos en modo Express si no se indica el modo. Ese modo no admite trabajos ni sufijos de revisión, y apaga lo que no recibe HTTP. El modo no se puede cambiar: el script recrea el entorno después de pedir confirmación.
- Las comprobaciones del script con dobles no prueban los permisos reales de la suscripción, como el registro de proveedores o la política de regiones.
- Event Hubs Standard cobra aunque no se use: hay que borrar el grupo después de la demo.
- La API mantiene una sola réplica porque guarda estado en memoria.

## Dependencias

- La persona dueña de la cuenta crea el proyecto de Supabase y la sesión de Azure.
- Persona 4: confirmar `ANALYTICS_ENGINE=persona2` como valor predeterminado y el titular de los momentos nuevos.
- Persona 3: alinear sus contratos para consumir `match-insights` o la base.
