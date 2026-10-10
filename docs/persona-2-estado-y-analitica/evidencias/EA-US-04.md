# Evidencia técnica de EA-US-04

## Identificación

- **Historia:** EA-US-04 · Agrupar jugadas y detectar patrones.
- **Estado:** verificada localmente.
- **Prioridad:** P0 (RF-09) y P1 (RF-29, RF-33).
- **Última verificación:** 9 de octubre de 2026.
- **Responsable:** Persona 2 · Estado y analítica.
- **Requisitos relacionados:** RF-09, RF-29, RF-33.

## Objetivo comprobado

Las jugadas (`sequence@1`) agrupan acciones de un equipo con el balón. Cuatro patrones con reglas versionadas (`fast_progression@1`, `recovery_to_shot@1`, `sustained_pressure@1` y los momentos menores `progressive_pass@1` y `high_recovery@1`) se activan solo cuando los eventos cumplen la regla. Las reglas están en [reglas de patrones y atención](../reglas-de-patrones-y-atencion.md).

## Alcance implementado

- `SequenceBuilder` incremental con cierre por tiro, pérdida, pausa de 20 s o cambio de período, y presiones rivales como contexto.
- Detectores causales: emiten en el evento que cumple la regla y nunca dependen de eventos posteriores.
- Notas de detección cuando faltan posiciones o dirección de ataque.
- Escenario sintético `synthetic-analytics-001` (178 eventos, 2 períodos) con fases de control, presión alta, caos, gol en transición y empate tras elaboración lenta.

## Cambios técnicos

| Archivo | Cambio |
|---|---|
| `domain/analytics/sequences.py` | Jugadas |
| `domain/analytics/signals.py` | Señal, nota, contexto e historial con búsqueda por ventana |
| `domain/analytics/patterns.py` | Detectores de tiro, progresión rápida, recuperación y tiro, presión sostenida, pase progresivo y recuperación alta |
| `adapters/sources/analytics_scenarios.py` | Escenario sintético de Persona 2 |

## Cobertura de criterios

| Criterio | Evidencia | Estado |
|---|---|---|
| Recuperación, pases y tiro como una jugada | `test_acceptance_match_groups_recovery_passes_and_goal_into_one_sequence`, `test_goal_moment_cites_the_whole_sequence_and_resulting_score` | Cumplido |
| Positivo y negativo por patrón | `test_fast_progression_positive_is_emitted_once_when_threshold_is_crossed`, `test_fast_progression_negative_slow_or_short`, `test_recovery_to_shot_positive_and_negative`, `test_sustained_pressure_positive_in_opponent_half`, `test_sustained_pressure_negative_cases` | Cumplido |
| Sin datos no se afirma | `test_fast_progression_without_positions_is_noted_not_emitted`, `test_sustained_pressure_ignores_unpositioned_actions_and_requires_direction` | Cumplido |
| Dirección de ataque | `test_right_to_left_team_uses_normalized_coordinates` | Cumplido |
| Jugadas por pausa y período | `test_long_pause_and_new_period_close_a_sequence` | Cumplido |

## Reproducción

```bash
.venv/Scripts/python -m pytest apps/backend/tests/test_analytics_patterns.py -q
```

## Resultado

```text
17 passed
```

## Limitaciones y riesgos

- Las posiciones son puntos de inicio y fin de cada evento; no hay trayectoria del balón ni posiciones de rivales.
- Los umbrales (30 de `x'` en 15 s, 5 acciones y 2 balones ganados en 90 s) se ajustaron con escenarios sintéticos.
- En la fase de caos del escenario, la regla de progresión rápida también se activa en recuperaciones seguidas de tiro: el dato lo cumple, pero el umbral puede necesitar más contexto.

## Dependencias

- Persona 1: un partido sintético más largo para revisar la frecuencia de cada patrón.
