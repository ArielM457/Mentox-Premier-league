# Evidencia técnica de EA-US-06

## Identificación

- **Historia:** EA-US-06 · Seleccionar momentos con motivos visibles.
- **Estado:** verificada localmente.
- **Prioridad:** P0.
- **Última verificación:** 9 de octubre de 2026.
- **Responsable:** Persona 2 · Estado y analítica.
- **Requisitos relacionados:** RF-14. Apoya RF-15, RF-16 y RF-23 a RF-26.

## Objetivo comprobado

El motor `attention@1` fusiona las señales de un mismo evento, puntúa con hechos medidos, novedad, repetición y preferencias, y emite `InsightCandidate v1` con motivos. Cada momento, emitido o descartado, deja una `AttentionDecision`.

## Alcance implementado

- Fusión por evento ancla con tipo principal por rango.
- Prioridad como suma de motivos con código y puntos, entre 0 y 100.
- Umbrales por perfil: neutro 40, casual 50, analista 35, jugador 45.
- Goles siempre emitidos, también los del rival.
- Aceptación directa del objeto de preferencias de Persona 4.

## Cambios técnicos

| Archivo | Cambio |
|---|---|
| `domain/analytics/attention.py` | Fusión, motor, informe y `select_moments` |
| `domain/analytics/models.py` | `SelectionReason`, `AttentionDecision`, `RelevancePreferences` |

## Cobertura de criterios

| Criterio | Evidencia | Estado |
|---|---|---|
| Eventos parecidos no generan varios mensajes | `test_similar_repeated_moments_are_limited_with_visible_reason` | Cumplido |
| Prioridad como suma visible | `test_priority_is_the_visible_sum_of_reasons_and_stays_in_range` | Cumplido |
| Decisiones con motivos | `test_discarded_decision_example_explains_why`, `attention-decision-v1.descartado.json` | Cumplido |
| Preferencias sin cambiar hechos | `test_favorite_club_raises_its_moments_without_changing_facts`, `test_favorite_player_changes_only_moments_where_they_take_part`, `test_casual_and_analyst_receive_different_selections_of_the_same_facts` | Cumplido |
| Gol rival siempre | `test_rival_goal_is_emitted_even_for_the_other_favorite_club`, `test_player_mode_follows_the_player_and_keeps_decisive_goals` | Cumplido |
| Preferencias de Persona 4 | `test_persona_4_preferences_object_is_accepted` | Cumplido |

## Reproducción

```bash
.venv/Scripts/python -m pytest apps/backend/tests/test_analytics_attention.py -q
```

## Resultado

```text
8 passed
```

Con el escenario de 178 eventos: neutro 19 emitidos y 33 descartados, casual 14 y 38, analista 33 y 19, casual del Río 17 y 35, modo jugador `aurora-8` 9 y 43.

## Limitaciones y riesgos

- El modo analista recibe 10 hitos en el escenario; puede resultar recargado y conviene revisarlo con la interfaz.
- RF-15 y RF-16 se completan en la narración: Persona 2 entrega hechos, fuentes y límites, y Persona 3 redacta.

## Dependencias

- Persona 3: plantillas o agentes para los diez tipos de momento.
