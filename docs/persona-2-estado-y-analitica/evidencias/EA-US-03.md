# Evidencia técnica de EA-US-03

## Identificación

- **Historia:** EA-US-03 · Calcular estadísticas recalculables.
- **Estado:** verificada localmente.
- **Prioridad:** P0 (RF-08), P1 (RF-10, RF-11) y P2 (RF-12).
- **Última verificación:** 9 de octubre de 2026.
- **Responsable:** Persona 2 · Estado y analítica.
- **Requisitos relacionados:** RF-08, RF-10, RF-11, RF-12, RNF-03.

## Objetivo comprobado

Cada cifra del snapshot se puede recalcular desde sus `source_event_ids` con la fórmula del [catálogo](../catalogo-de-metricas.md). Las cifras sin datos suficientes quedan no disponibles con su motivo.

## Alcance implementado

- Conteos por equipo y jugador: goles, tiros, tiros a puerta, pases intentados y completados, recuperaciones, entradas, entradas ganadas, presiones e intervenciones.
- Precisión de pase con denominador visible y exclusión de resultados `unknown`.
- Posesión por tiempo, cambios y posesiones ganadas.
- Pases progresivos, entradas al último tercio, recuperaciones altas, distancia media y pase más largo.
- Distancia y ángulo de tiro en los momentos de tiro.
- Velocidades y distancia recorrida declaradas no disponibles.
- Catálogo en código (`domain/analytics/catalog.py`) con clave, ámbito, unidad, origen, versión, fórmula, datos y caso sin datos.

## Fuera del alcance

- Dificultad de pase: necesita presión sobre el pasador y posiciones de rivales que `MatchEvent 1.0` no trae.

## Cambios técnicos

| Archivo | Cambio |
|---|---|
| `domain/analytics/statistics.py` | Ventanas, constructor `metric`, reglas de conteo y espaciales |
| `domain/analytics/catalog.py` | Catálogo de métricas |

## Cobertura de criterios

| Criterio | Evidencia | Estado |
|---|---|---|
| Cada conteo coincide con sus eventos de origen | `test_every_count_can_be_recalculated_from_its_source_events` (más de 50 cifras del escenario de 178 eventos) | Cumplido |
| Proporción sin denominador no disponible | `test_ratio_without_data_is_unavailable_instead_of_zero`, `test_pass_accuracy_uses_known_outcomes_and_shows_its_denominator` | Cumplido |
| Dirección de ataque por período | `test_progressive_passes_follow_the_attack_direction_of_each_period`, `test_spatial_metrics_without_direction_are_unavailable` | Cumplido |
| Distancias con dimensiones del campo | `test_pass_distance_uses_pitch_dimensions` | Cumplido |
| Velocidad no disponible (RF-12) | `test_speed_metrics_are_declared_unavailable_with_reason` | Cumplido |
| Jugador solo con eventos identificados (RF-11) | `test_player_metrics_only_use_identified_events` | Cumplido |
| Cada clave en el catálogo | `test_every_emitted_metric_is_in_the_catalog_with_its_version` | Cumplido |

## Reproducción

```bash
.venv/Scripts/python -m pytest apps/backend/tests/test_analytics_statistics.py -q
```

## Resultado

```text
9 passed
```

## Limitaciones y riesgos

- Las métricas espaciales de un equipo con eventos parcialmente posicionados cuentan solo los evaluables; `evaluated_events` en `components` muestra cuántos fueron.
- Los umbrales de pase progresivo (10 m) y recuperación alta (`x' ≥ 60`) son propuestas del equipo, no definiciones de un proveedor.

## Dependencias

- Persona 1: si la vía de vídeo entrega posiciones sucesivas con tiempo, se podrán activar las velocidades.
