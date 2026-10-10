# Evidencia técnica de EA-US-02

## Identificación

- **Historia:** EA-US-02 · Reconstruir el estado ante tardíos y correcciones.
- **Estado:** verificada localmente.
- **Prioridad:** P1.
- **Última verificación:** 9 de octubre de 2026.
- **Responsable:** Persona 2 · Estado y analítica.
- **Requisitos relacionados:** RF-05 y el tercer criterio pendiente de DV-US-05.

## Objetivo comprobado

`MatchStateEngine` aplica la política `rebuild_from_ordered_history@1`, complementaria a `forward_and_flag` de Persona 1. Un evento tardío se inserta en su posición deportiva y el análisis se vuelve a plegar; el estado resultante es idéntico al de la llegada en orden.

## Alcance implementado

- `ingest`: aplicación incremental si es puntual; reconstrucción si es tardío.
- `correct`: reemplazo explícito de un evento con el mismo `event_id`.
- `retract`: retiro de un evento.
- `StateRevision` con motivo, política, marcador y posesión antes y después, y momentos retirados y añadidos.
- `rebuild(events, video_time_ms=...)`, que cumple `MatchStateRebuilder` de `VideoSynchronizedReplay` (Persona 1) para los saltos de vídeo.

## Fuera del alcance

- Un contrato de corrección en la ingesta: hoy el deduplicador de Persona 1 descarta cualquier `event_id` repetido, también una corrección.
- Persistir el historial al reiniciar el proceso.

## Cambios técnicos

| Archivo | Cambio |
|---|---|
| `application/analytics/engine.py` | Motor, revisiones, resultados de ingesta y `replay` |

## Decisiones técnicas

- Repetido idéntico: `duplicate`, sin cambios. Mismo `event_id` con otro contenido: `conflict`, sin cambios. Corregir requiere intención explícita.
- Un salto de vídeo reinicia el historial y no crea una revisión, porque el partido no cambió.
- La reconstrucción repliega todo el partido: con 178 eventos tarda milisegundos.

## Cobertura de criterios

| Criterio | Evidencia | Estado |
|---|---|---|
| Un tardío produce el mismo estado que a tiempo | `test_late_event_rebuilds_the_same_state_as_on_time_arrival` (con `EventOrderTracker` de Persona 1) | Cumplido |
| Corrección y retiro reconstruyen y registran revisión | `test_correction_replaces_the_event_and_withdraws_moments_it_supported`, `test_retraction_removes_the_event_from_every_figure` | Cumplido |
| Repetido idéntico y conflicto | `test_duplicates_are_idempotent_and_conflicts_need_explicit_correction` | Cumplido |
| Salto de vídeo sin revisión | `test_engine_implements_the_video_seek_rebuilder_of_persona_1` | Cumplido |
| Publicación de la revisión y de los momentos actualizados | `test_late_event_publishes_revision_and_withdraws_or_updates_moments` | Cumplido |

## Reproducción

```bash
.venv/Scripts/python -m pytest apps/backend/tests/test_analytics_engine.py apps/backend/tests/test_analytics_stream.py -q
```

## Resultado

```text
test_analytics_engine.py  5 passed
test_analytics_stream.py  5 passed
```

## Limitaciones y riesgos

- Los momentos ya mostrados en pantalla pueden cambiar tras una reconstrucción; el flujo publica `insight_candidate.withdrawn` o una nueva versión, y Persona 4 debe decidir cómo mostrarlo.
- Varias réplicas del procesador para un mismo partido tendrían estados separados; la partición por `match_id` lo evita.

## Dependencias

- Persona 1: acordar esta política para cerrar DV-US-05 y definir un tipo de mensaje de corrección.
