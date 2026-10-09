# Evidencia técnica de DV-US-04

## Identificación

- **Historia:** DV-US-04 · Evitar el doble conteo.
- **Estado:** núcleo y transporte en memoria verificados localmente; integración con Event Hubs pendiente.
- **Prioridad:** P0.
- **Última verificación:** 9 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.
- **Requisitos relacionados:** DV-RF-06, DV-RF-11, DV-RF-13 y RF-04.

## Objetivo comprobado

Los reintentos de un evento validado no se entregan dos veces al consumidor del estado. La primera aparición de la clave compuesta por `match_id` y `event_id` se acepta. Las apariciones posteriores se separan de los aceptados y quedan disponibles en un registro de diagnóstico.

## Alcance implementado

- Caso de uso `EventDeduplicator`, independiente de HTTP, Azure y del generador sintético.
- Identidad compuesta por `(match_id, event_id)` conforme a `MatchEvent 1.0`.
- Estado de claves vistas conservado entre varias operaciones `process` de la misma instancia.
- Informe inmutable con eventos aceptados, duplicados y sus cantidades.
- Registro acumulado de duplicados durante el ciclo de vida del consumidor.
- Diagnóstico con índice dentro del lote, clave del evento, secuencia de la primera aparición y secuencia del reintento.
- Consumidor `InMemoryEventConsumer` que solo guarda los eventos aceptados.
- Pruebas con el partido sintético de DV-US-01 y sin servicios externos.

## Fuera del alcance

- El consumidor de Azure Event Hubs se implementará en DV-US-07.
- No existe todavía una prueba de integración contra un event hub real o emulado.
- El registro de claves y duplicados no se persiste al reiniciar el proceso.
- La validación estructural anterior a la deduplicación sigue a cargo de DV-US-03.
- La política de eventos tardíos pertenece a DV-US-05.
- No se calculan estadísticas ni se actualiza el estado deportivo.

## Entradas y resultados

| Elemento | Descripción |
|---|---|
| Entrada | Iterable de objetos `MatchEvent` ya validados |
| Clave de idempotencia | Tupla `(match_id, event_id)` |
| Evento aceptado | Primera aparición de una clave durante el ciclo de vida del deduplicador |
| Duplicado | Aparición posterior de una clave ya vista, aunque otros campos de la carga sean distintos |
| Resultado por operación | `DeduplicationReport` con tuplas `accepted` y `duplicates` |
| Diagnóstico acumulado | Propiedad `EventDeduplicator.duplicates` |
| Resultado local | `InMemoryEventConsumer.events` contiene únicamente eventos aceptados |

Ejemplo de una entrada con reintento:

```text
(synthetic-acceptance-001, evt-001) -> aceptado, secuencia 0
(synthetic-acceptance-001, evt-001) -> duplicado, secuencia 1
```

El mismo `event_id` en dos partidos distintos produce dos claves y se acepta una vez en cada partido.

## Cambios técnicos

| Archivo | Cambio | Motivo |
|---|---|---|
| `apps/backend/src/match_intelligence/application/deduplication.py` | Clave, informe, diagnóstico y registro de claves vistas | Mantener la regla en la capa de aplicación y reutilizarla desde cualquier transporte |
| `apps/backend/src/match_intelligence/adapters/messaging/memory.py` | Consumidor local idempotente | Comprobar DV-RF-11 sin Azure |
| `apps/backend/tests/test_event_deduplication.py` | Siete pruebas automatizadas | Demostrar identidad, continuidad entre lotes, diagnóstico y flujo local |
| `docs/persona-1-datos-y-vision/historias-de-usuario.md` | Estado y enlace de evidencia | Mantener la trazabilidad del backlog |
| `docs/persona-1-datos-y-vision/evidencias/README.md` | Registro de DV-US-04 | Hacer visible el estado y la limitación de integración |

## Diseño y flujo

```text
MatchEvent validado
        │
        ▼
EventDeduplicator
        │
        ├── clave nueva ─────────> accepted ──> consumidor del estado
        │
        └── clave ya vista ──────> duplicates ──> diagnóstico
```

El publicador puede repetir un mensaje. La idempotencia se aplica al consumir, antes de que Persona 2 cuente o procese el evento deportivo.

## Decisiones técnicas

### Clave compuesta del evento deportivo

La regla usa `match_id` y `event_id`, no la igualdad completa del objeto ni un identificador del mensaje de transporte. Por eso, un reintento con la misma identidad continúa siendo duplicado aunque cambie por error otro valor de la carga. Esta elección sigue DV-RF-06 y el contrato de `docs/08-formato-de-eventos.md`.

### Estado por instancia de consumidor

Cada `EventDeduplicator` mantiene su propio registro. Dos consumidores independientes no comparten memoria ni interfieren entre sí. La instancia debe vivir tanto como el consumidor que protege. Reiniciar el proceso elimina el registro; la persistencia será una decisión de operación posterior.

### Secuencia de llegada para diagnóstico

El diagnóstico conserva dos posiciones monotónicas: la primera observación y el reintento. También conserva el índice del duplicado en la operación actual. No se usa `clock_ms` para decidir duplicados porque el reloj deportivo no representa el orden de llegada.

### Independencia del transporte

`EventDeduplicator` solo importa el contrato de dominio y biblioteca estándar. El adaptador en memoria ya lo usa. El futuro consumidor de Event Hubs debe pasar cada `MatchEvent` validado por la misma instancia antes de entregarlo al backend. Esta separación permite probar la regla sin el SDK de Azure, pero no sustituye una prueba de integración de DV-US-07.

### Sin consulta a Context7

Esta historia no añadió ni asumió APIs de bibliotecas o frameworks externos. La implementación usa dataclasses, colecciones y tipos de Python 3.12. Por esa razón no fue necesaria una consulta a Context7.

## Cobertura de criterios de aceptación

| Criterio | Implementación | Evidencia | Estado |
|---|---|---|---|
| Dos mensajes con el mismo `match_id` y `event_id` producen un solo evento aceptado | Registro `_first_seen` y separación en `DeduplicationReport` | `test_same_match_and_event_id_is_accepted_only_once` y `test_retry_is_detected_across_separate_consume_operations` | Cumplido localmente |
| El duplicado queda registrado para diagnóstico | `DuplicateEvent` y registro acumulado `duplicates` | `test_duplicate_is_recorded_with_diagnostic_positions` | Cumplido localmente |
| La regla funciona con transporte local | `InMemoryEventConsumer` usa el deduplicador antes de guardar | `test_local_consumer_does_not_deliver_published_retry_twice` | Cumplido localmente |
| La regla funciona con Event Hubs | El caso de uso es independiente del transporte y define el punto de integración | Requiere el consumidor y la prueba de integración de DV-US-07 | Pendiente de integración |

## Cobertura adicional

| Comportamiento | Evidencia | Estado |
|---|---|---|
| El mismo `event_id` en partidos distintos no colisiona | `test_key_combines_match_id_and_event_id` | Cumplido |
| Cambiar otro campo no evita detectar el reintento | `test_identity_key_wins_when_retry_payload_changes` | Cumplido |
| Dos consumidores no comparten estado accidentalmente | `test_deduplicator_instances_do_not_share_state` | Cumplido |
| La suite anterior no presenta regresiones | Suite completa del backend | Cumplido |

## Pruebas automatizadas

| Prueba | Comportamiento comprobado |
|---|---|
| `test_same_match_and_event_id_is_accepted_only_once` | Una repetición dentro del lote solo produce un aceptado |
| `test_duplicate_is_recorded_with_diagnostic_positions` | El diagnóstico contiene clave y secuencias de llegada |
| `test_key_combines_match_id_and_event_id` | La identidad incluye el partido |
| `test_retry_is_detected_across_separate_consume_operations` | El estado se conserva entre lotes de una instancia |
| `test_identity_key_wins_when_retry_payload_changes` | La regla no depende de comparar toda la carga |
| `test_local_consumer_does_not_deliver_published_retry_twice` | El consumidor en memoria entrega el partido una sola vez |
| `test_deduplicator_instances_do_not_share_state` | El registro pertenece a cada consumidor |

## Reproducción

Desde la raíz del repositorio:

```bash
uv python install 3.12
uv sync --project apps/backend --extra dev
UV_CACHE_DIR=/tmp/mentox-uv-cache uv run \
  --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_event_deduplication.py -q
```

Para ejecutar toda la suite:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache uv run \
  --project apps/backend --python 3.12 \
  pytest apps/backend/tests -q
```

## Entorno verificado

| Componente | Versión |
|---|---|
| Python | 3.12.13 |
| uv | 0.11.32 |
| pytest | 9.1.1 |
| Contrato | MatchEvent 1.0 |
| Transporte probado | Memoria local |
| Infraestructura externa | Ninguna |

## Resultado

Verificación específica de DV-US-04 ejecutada el 9 de octubre de 2026:

```text
.......                                                                  [100%]
7 passed in 0.07s
```

Verificación completa del backend:

```text
...................................                                      [100%]
35 passed in 0.28s
```

## Limitaciones y riesgos

- El registro vive en memoria. Un reinicio acepta nuevamente claves observadas antes del reinicio.
- Varias réplicas del consumidor tendrían registros separados. Una operación distribuida necesitará partición coherente, almacenamiento compartido o idempotencia persistente.
- No se ha probado concurrencia desde varios hilos. El consumidor asíncrono previsto debe aplicar la operación sin intercalar modificaciones del mismo registro.
- El historial crece con cada clave y duplicado. Antes de procesar partidos largos se debe definir retención por partido o ventana de vida.
- La detección por identidad descarta una carga posterior con la misma clave aunque cambie su contenido. Las correcciones o retiros necesitan un contrato distinto; todavía son una decisión pendiente.
- No existe evidencia contra Azure Event Hubs. La independencia del caso de uso no demuestra serialización, particiones, puntos de control ni reintentos reales del servicio.

## Dependencias y siguientes pasos

- DV-US-07 debe implementar el consumidor de Event Hubs, validar su carga y pasar los aceptados por una instancia de `EventDeduplicator`.
- La prueba de DV-US-07 debe publicar un reintento y comprobar que el backend recibe un solo evento deportivo y un diagnóstico.
- DV-US-08 reutilizará el mismo caso de uso al seleccionar transporte mediante configuración.
- Persona 2 debe consumir únicamente `DeduplicationReport.accepted`.
- La política de correcciones, retiros y retención del registro debe acordarse antes de una operación distribuida persistente.
