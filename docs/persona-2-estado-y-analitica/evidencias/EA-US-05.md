# Evidencia técnica de EA-US-05

## Identificación

- **Historia:** EA-US-05 · Comparar tramos, hitos e indicadores propios.
- **Estado:** verificada localmente.
- **Prioridad:** P1 (RF-17, RF-30, RF-31) y P2 (RF-32).
- **Última verificación:** 9 de octubre de 2026.
- **Responsable:** Persona 2 · Estado y analítica.
- **Requisitos relacionados:** RF-17, RF-30, RF-31, RF-32.

## Objetivo comprobado

Los indicadores propios `control@1`, `momentum@1` y `chaos@1` son fórmulas versionadas con componentes, pesos y referencias visibles, y origen `team_indicator`. Los detectores `control_shift@1`, `chaos_phase@1` y `milestone@1` se activan en los tramos que cumplen su regla y no en los demás.

## Alcance implementado

- Índices de control, impulso y caos en cada snapshot (ventanas de 3 min y semivida de 120 s).
- Cambio de control entre dos ventanas consecutivas del mismo período.
- Fase de caos con entrada en 60 y rearme bajo 40.
- Hitos por umbral y récord de pase del partido.
- Comparación con el tramo anterior en la presión sostenida y en el cambio de control; `MatchAnalytics.compare_segments` para comparar tramos a pedido.

## Cambios técnicos

| Archivo | Cambio |
|---|---|
| `domain/analytics/indicators.py` | Índices y detectores de cambio de control y caos |
| `domain/analytics/milestones.py` | Hitos de jugador |

## Decisiones técnicas

- Las referencias del caos se subieron de 4 a 6 cambios por minuto y de 4 a 5 duelos por minuto. Con los valores anteriores la fase de presión alta llegaba a 60 y no se distinguía de una fase de caos.
- Un cambio de control no se repite para el mismo líder en el período, para no anunciar varias veces el mismo dominio.

## Cobertura de criterios

| Criterio | Evidencia | Estado |
|---|---|---|
| Comparación con el tramo anterior | `test_scenario_pressure_is_compared_with_the_previous_window` (5 acciones frente a 0) | Cumplido |
| Cambio de control en dominio opuesto y no en dominio constante | `test_scenario_control_shift_and_chaos_phase_happen_in_their_phases` (Río a los 268 s, de 5 a 61,4), `test_one_sided_control_does_not_trigger_a_shift_and_calm_play_is_not_chaos` | Cumplido |
| Caos en tramo inestable y no en tramo estable | Mismas pruebas (caos a los 361 s; la fase de presión no pasa de 43) y `test_chaotic_stretch_triggers_chaos_with_visible_components` | Cumplido |
| Hito una vez y solo si se alcanza | `test_milestone_is_emitted_once_at_the_exact_event`, `test_match_record_pass_needs_distance_improvement_and_history` | Cumplido |
| Componentes visibles y escala del equipo | Componentes y `evidence_limits` comprobados en las pruebas anteriores | Cumplido |

## Reproducción

```bash
.venv/Scripts/python -m pytest apps/backend/tests/test_analytics_patterns.py -q -k "control or chaos or milestone or record or previous_window"
```

## Resultado

```text
6 passed, 11 deselected
```

## Limitaciones y riesgos

- No hay una comparación con una referencia externa de control o caos: la validación es de plausibilidad con tramos diseñados.
- Las ventanas no cruzan el descanso; al empezar un período los índices tardan en estar disponibles.
- En el escenario, los hitos de recuperaciones aparecen varias veces en la fase de caos; la regla de repetición de la atención los limita.

## Dependencias

- Equipo: confirmar pesos, referencias y umbrales (decisión pendiente 5).
