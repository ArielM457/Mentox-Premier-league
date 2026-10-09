# Evidencia técnica de DV-US-05

## Identificación

- **Historia:** DV-US-05 · Reconocer un evento tardío.
- **Estado:** detección y registro verificados localmente; reconstrucción pendiente de acuerdo con Persona 2.
- **Prioridad:** P1.
- **Última verificación:** 9 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.
- **Requisitos relacionados:** DV-RF-08, RF-05 y DV-RNF-03.

## Objetivo comprobado

La ingesta reconoce cuando un evento validado y no duplicado llega con una posición deportiva anterior al reloj máximo observado para su partido. El evento no se descarta ni se oculta: se reenvía en orden de llegada con la marca `late` y se añade a un registro de diagnóstico.

La implementación no reconstruye el estado del partido. Esa decisión pertenece a Persona 2 y todavía no está acordada en la documentación del proyecto.

## Alcance implementado

- Comparación del tiempo deportivo mediante la tupla ordenada `(period, clock_ms)`.
- Reloj máximo, o `watermark`, independiente para cada `match_id`.
- Clasificación de cada llegada como `on_time` o `late`.
- Política provisional `forward_and_flag`.
- Reenvío de todos los eventos en su orden de llegada original.
- Registro del índice dentro del lote, partido, evento, tiempo del evento, reloj máximo y secuencia global de llegada.
- Conservación del reloj máximo cuando llega un evento tardío.
- Estado conservado entre operaciones sucesivas de la misma instancia.
- Tratamiento correcto del reinicio de `clock_ms` al comenzar otro período.

## Fuera del alcance

- Reconstruir marcador, posesión, estadísticas o `MatchSnapshot` pertenece a Persona 2.
- Confirmar la política definitiva con Persona 2 sigue pendiente.
- No se reordena el flujo ni se inserta el evento dentro de un historial deportivo.
- No se corrigen ni retiran eventos anteriores.
- No se persisten relojes máximos o diagnósticos al reiniciar el proceso.
- No se define una ventana de tolerancia temporal.
- La validación y la deduplicación corresponden a DV-US-03 y DV-US-04 y deben ejecutarse antes.

## Entradas y resultados

| Elemento | Descripción |
|---|---|
| Entrada | Iterable de objetos `MatchEvent` validados y deduplicados, en orden de llegada |
| Tiempo comparable | `MatchTime(period, clock_ms)` |
| Reloj máximo | Mayor `MatchTime` observado por `match_id` |
| Evento puntual | Tiempo igual o posterior al reloj máximo del partido |
| Evento tardío | Tiempo estrictamente anterior al reloj máximo del partido |
| Resultado | `EventOrderReport` con eventos clasificados, registros tardíos y política aplicada |
| Salida provisional | Todos los eventos reenviados en orden de llegada; los tardíos llevan estado `late` |

Ejemplo:

```text
Llega evt-003 en período 1, 12 000 ms -> on_time, watermark = (1, 12 000)
Llega evt-002 en período 1,  8 000 ms -> late, watermark permanece (1, 12 000)
```

## Cambios técnicos

| Archivo | Cambio | Motivo |
|---|---|---|
| `apps/backend/src/match_intelligence/application/event_order.py` | Tiempo comparable, estados, política, informe y seguimiento por partido | Detectar y registrar eventos tardíos sin acoplarse al estado ni al transporte |
| `apps/backend/tests/test_event_order.py` | Ocho pruebas de orden, períodos, lotes y partidos | Demostrar la regla y sus límites |
| `docs/persona-1-datos-y-vision/historias-de-usuario.md` | Estado y enlace de evidencia | Mantener la trazabilidad del backlog |
| `docs/persona-1-datos-y-vision/evidencias/README.md` | Registro de DV-US-05 | Mostrar el avance y la dependencia pendiente |

## Diseño y flujo

```text
MatchEvent validado y no duplicado
                │
                ▼
       EventOrderTracker
                │
        ┌───────┴────────┐
        ▼                ▼
     on_time            late
        │                │
        │                └── registro diagnóstico
        └───────┬────────┘
                ▼
     reenvío en orden de llegada
                │
                ▼
  política de reconstrucción de Persona 2
```

## Política provisional

La política implementada se identifica como `forward_and_flag`:

1. El evento tardío no se descarta.
2. El evento no se reordena durante la ingesta.
3. La salida conserva su objeto `MatchEvent` original y añade una clasificación externa.
4. El diagnóstico conserva el reloj contra el que se detectó el retraso.
5. El reloj máximo no retrocede.
6. Persona 2 debe decidir si reconstruye el estado completo, recalcula desde un punto anterior o aplica otra estrategia.

Esta es una propuesta operativa de Persona 1 para no ocultar información. No se registra como acuerdo definitivo del equipo.

## Decisiones técnicas

### Período y reloj como una sola posición

Comparar únicamente `clock_ms` marcaría como tardío el primer evento del segundo período, porque el reloj vuelve a comenzar. `MatchTime` ordena primero por `period` y luego por `clock_ms`. Así, `(2, 1 000)` ocurre después de `(1, 32 000)`.

### Igualdad de reloj

Dos acciones pueden compartir `period` y `clock_ms`. Un tiempo igual al reloj máximo se considera puntual. Solo un valor estrictamente anterior se marca como tardío.

### Separación por partido

Cada `match_id` tiene su propio reloj máximo. La llegada de un partido no cambia la clasificación de otro partido procesado por la misma instancia.

### Orden de llegada inalterado

`EventOrderReport.forwarded` conserva exactamente el orden recibido. La ingesta señala el retraso, pero no decide cómo una estadística ya calculada debe cambiar. Esto mantiene separados los límites de Persona 1 y Persona 2.

### Orden del flujo de calidad

El componente presupone este orden:

```text
validación -> deduplicación -> clasificación temporal -> estado
```

Un duplicado debe retirarse antes de comprobar el orden para que un reintento no genere además un diagnóstico tardío engañoso.

### Sin consulta a Context7

La historia usa dataclasses, `StrEnum`, colecciones y comparación ordenada de Python 3.12. No se incorporó ni se asumió ninguna API externa, por lo que Context7 no fue necesario.

## Cobertura de criterios de aceptación

| Criterio | Implementación | Evidencia | Estado |
|---|---|---|---|
| Detectar que el reloj es anterior al último evento procesado | `EventOrderTracker` compara `MatchTime` con el reloj máximo del partido | `test_event_behind_the_match_watermark_is_marked_late` y `test_order_is_tracked_across_separate_batches` | Cumplido localmente |
| No descartar el evento silenciosamente | Todos los eventos aparecen en `forwarded`; los tardíos también aparecen en `late_events` | `test_late_event_is_forwarded_in_arrival_order_and_recorded` | Cumplido localmente |
| Coincidir con la política acordada con Persona 2 | Existe la política provisional `forward_and_flag`, pero Persona 2 aún no acordó la reconstrucción | Documentos de Persona 1 y Persona 2 revisados | Pendiente de acuerdo |

## Cobertura adicional

| Comportamiento | Evidencia | Estado |
|---|---|---|
| Un tardío no retrocede el reloj máximo | `test_late_event_does_not_move_watermark_backwards` | Cumplido |
| Dos eventos con el mismo reloj son puntuales | `test_same_clock_is_not_late` | Cumplido |
| El reloj puede reiniciar en un período nuevo | `test_new_period_advances_order_even_when_clock_restarts` | Cumplido |
| Volver a un período anterior se detecta | `test_event_from_previous_period_is_late_after_period_transition` | Cumplido |
| Los partidos no comparten reloj máximo | `test_matches_have_independent_watermarks` | Cumplido |

## Pruebas automatizadas

| Prueba | Comportamiento comprobado |
|---|---|
| `test_event_behind_the_match_watermark_is_marked_late` | Retroceso de reloj marcado como `late` |
| `test_late_event_is_forwarded_in_arrival_order_and_recorded` | Reenvío, orden y diagnóstico completo |
| `test_late_event_does_not_move_watermark_backwards` | Reloj máximo monotónico |
| `test_order_is_tracked_across_separate_batches` | Estado temporal conservado entre operaciones |
| `test_same_clock_is_not_late` | Igualdad permitida |
| `test_new_period_advances_order_even_when_clock_restarts` | Transición válida entre períodos |
| `test_event_from_previous_period_is_late_after_period_transition` | Retroceso de período detectado |
| `test_matches_have_independent_watermarks` | Aislamiento por partido |

## Reproducción

Desde la raíz del repositorio:

```bash
uv python install 3.12
uv sync --project apps/backend --extra dev
UV_CACHE_DIR=/tmp/mentox-uv-cache uv run \
  --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_event_order.py -q
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
| Datos | Partido sintético de DV-US-01 |
| Infraestructura externa | Ninguna |

## Resultado

Verificación específica de DV-US-05 ejecutada el 9 de octubre de 2026:

```text
........                                                                 [100%]
8 passed in 0.07s
```

Verificación completa del backend:

```text
...........................................                              [100%]
43 passed in 0.32s
```

## Limitaciones y riesgos

- La estrategia de reconstrucción del estado sigue pendiente de Persona 2.
- El reloj máximo y el diagnóstico viven en memoria y se pierden al reiniciar.
- Varias réplicas del consumidor mantendrían relojes separados si no comparten partición o estado.
- No existe una tolerancia configurable. Cualquier retroceso, incluso de un milisegundo, se marca como tardío.
- El componente no diferencia demora de transporte, corrección histórica o retiro de un evento.
- Un evento de un período anterior siempre se considera tardío después de avanzar de período.
- No hay pruebas con Event Hubs ni con una transmisión real.
- No se ha definido cuándo liberar el reloj y el historial de un partido terminado.

## Dependencias y siguientes pasos

- Persona 2 debe acordar y probar cómo `late` modifica o reconstruye `MatchSnapshot v1`.
- Después del acuerdo se debe actualizar la política documentada y el tercer criterio de aceptación.
- El futuro flujo de ingesta debe conectar DV-US-03, DV-US-04 y DV-US-05 en ese orden.
- DV-US-07 debe conservar la secuencia de llegada del consumidor de Event Hubs y pasar los eventos aceptados por este componente.
- Las correcciones y retiros requieren un contrato separado antes de implementarse.
