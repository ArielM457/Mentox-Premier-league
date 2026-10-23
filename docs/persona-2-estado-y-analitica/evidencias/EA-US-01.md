# Evidencia técnica de EA-US-01

## Identificación

- **Historia:** EA-US-01 · Consultar el estado del partido.
- **Estado:** verificada localmente.
- **Prioridad:** P0.
- **Última verificación:** 9 de octubre de 2026.
- **Responsable:** Persona 2 · Estado y analítica.
- **Requisitos relacionados:** RF-07, RNF-01.

## Objetivo comprobado

`build_snapshot` y `MatchAnalytics.snapshot` producen `MatchSnapshot v1` desde eventos normalizados. El marcador, el período, el reloj y la posesión se derivan con reglas versionadas (`possession@1`) y el resultado no depende del orden de llegada.

## Alcance implementado

- Pliegue determinista `MatchState` en orden `(period, clock_ms)`.
- Posesión por tramos con atribución de tiempo entre eventos del mismo período, sin extrapolar.
- Reloj del snapshot avanzado con `video_time_ms` cuando se pide en un instante posterior al último evento.
- Exclusión de eventos de otro partido, de un equipo desconocido o con un jugador del otro equipo según los metadatos.
- Campos opcionales: `engine_version`, `event_count`, `last_event_id`, `last_event_clock_ms`, `state_revision`, `late_event_ids`, `corrected_event_ids` y `excluded_event_ids`.

## Fuera del alcance

- Saques, faltas, tarjetas y goles en propia puerta: `MatchEvent 1.0` no los representa.
- Tiempo de posesión después del último evento.

## Cambios técnicos

| Archivo | Cambio |
|---|---|
| `domain/analytics/models.py` | Contratos `MetricValue`, `MatchSnapshot` y `InsightCandidate` compatibles con Persona 4 |
| `domain/analytics/state.py` | `MatchState`, tramos y cambios de posesión, `chronological` |
| `domain/analytics/pitch.py` | Dirección de ataque, metros, distancia y ángulo a portería |
| `application/analytics/pipeline.py` | `build_snapshot` y `MatchAnalytics.snapshot` |

## Decisiones técnicas

- `tackle` con `success` da la posesión porque gana el balón; el `possession_change` que suele seguirle ya no cuenta como otro cambio.
- Un gol deja la posesión vacía: el evento no dice quién saca.
- Los empates de `(period, clock_ms)` conservan el orden de llegada.

## Cobertura de criterios

| Criterio | Evidencia | Estado |
|---|---|---|
| Marcador, posesión y reloj coinciden con la secuencia | `test_score_possession_and_clock_follow_the_acceptance_match`, `test_possession_changes_only_when_another_team_gains_the_ball`, `test_possession_time_is_attributed_between_events_and_never_extrapolated`, `test_new_period_clears_possession_and_does_not_join_spells`, `test_goal_counts_once_and_keeps_its_source` | Cumplido |
| Dos ejecuciones producen el mismo snapshot | `test_two_runs_of_the_same_match_are_identical` | Cumplido |
| El orden de llegada no cambia el resultado | `test_input_order_does_not_change_the_result` | Cumplido |
| Un evento contradictorio se excluye e informa | `test_events_that_contradict_metadata_are_excluded_not_counted` | Cumplido |

## Reproducción

```bash
.venv/Scripts/python -m pytest apps/backend/tests/test_analytics_state.py apps/backend/tests/test_analytics_reproducibility.py -q
```

## Resultado

```text
test_analytics_state.py            6 passed
test_analytics_reproducibility.py  5 passed
```

## Limitaciones y riesgos

- Si un equipo pierde el balón sin un evento que lo registre, la posesión sigue atribuida al último equipo con el balón.
- Un snapshot con 14 jugadores ocupa unos 106 KB en JSON.

## Dependencias

- Persona 4 debe importar los contratos desde `domain/analytics/models.py` al integrar.
