# Evidencia técnica de EA-US-10

## Identificación

- **Historia:** EA-US-10 · Medir velocidad y distancia desde posiciones.
- **Estado:** verificada con trayectorias de resultado conocido y con observaciones simuladas en el formato de Persona 1; observaciones reales de vídeo pendientes.
- **Prioridad:** P2.
- **Última verificación:** 13 de octubre de 2026.
- **Responsable:** Persona 2 · Estado y analítica.
- **Requisitos relacionados:** RF-11, RF-12 y la sugerencia del reto de indicadores de velocidad y distancia que se activan por umbral.

## Objetivo comprobado

El módulo `tracking@1` calcula distancia, distancia a alta intensidad, velocidad máxima, sprints, velocidad del balón y del tiro, forma del equipo y presión por cercanía, y emite avisos por umbral (`tracking_alert@1`). Lo hace a partir de lo que entrega Persona 1: `VisualTrackObservation`, `ResolvedVisualIdentity` y `PredictionOrigin`. Persona 2 no convierte vídeo ni resuelve identidades. Las reglas están en [analítica de seguimiento](../analitica-de-seguimiento.md).

## Alcance implementado

- Cálculos del dominio sobre `TrackSet` (pistas en orden deportivo), sin depender del formato de entrada.
- Adaptador `tracks_from_observations`, que usa los objetos de Persona 1:
  - pasa las posiciones de 0 a 100 a metros;
  - ubica cada observación en `(period, clock_ms)` con el reloj de los eventos;
  - asigna `player_id` solo con identidad confirmada;
  - descarta y cuenta las observaciones no válidas.
- Campo opcional `tracking_evidence` en `MetricValue`, con el origen de Persona 1 (`simulated_fixture` o `actual_model`).
- Integración en `build_snapshot(tracking=...)` y `MatchAnalytics(tracking_provider=...)`, sin usar muestras posteriores al snapshot.
- Observaciones simuladas con el formato de Persona 1 y la identidad resuelta con su `PlayerIdentityResolver`.

## Fuera del alcance

- Convertir la salida de Roboflow Sports u otro detector en observaciones: es DV-US-19 de Persona 1. El conversor que existía en la versión anterior se eliminó para no duplicar su trabajo.
- Llevar los avisos de seguimiento a `InsightCandidate v1`, que exige eventos de origen.

## Cambios técnicos

| Archivo | Cambio |
|---|---|
| `domain/analytics/tracking.py` | `TrackSet`, `Track`, `Sample`, `Instant`, limpieza, métricas y avisos |
| `application/analytics/tracking_input.py` | `VideoClock`, `TrackingInput` y conversión desde las observaciones de Persona 1 |
| `domain/analytics/models.py` | `TrackingEvidence` en `MetricValue` |
| `domain/analytics/catalog.py` | Claves de seguimiento con versión `tracking@1` |
| `application/analytics/pipeline.py` | Seguimiento opcional en el snapshot y en `MatchAnalytics` |
| `adapters/sources/tracking_mock.py` | Observaciones simuladas con el formato de Persona 1 |
| `adapters/sources/roboflow_tracking.py` | Eliminado: la conversión desde Roboflow es de Persona 1 |

## Decisiones técnicas

- **Se usa el formato de visión de Persona 1, sin crear uno propio.** La versión anterior tenía un contrato `TrackingFrame v1` que duplicaba `VisualTrackObservation`.
- **Convenciones provisionales.** Mientras `VisualTrackObservation` no indique la clase del objeto, el balón se reconoce por `track_id` y los porteros por una lista de jugadores. Una pista sin equipo queda `unassigned`.
- **Identidad.** Una pista solo tiene `player_id` con una `ResolvedVisualIdentity` confirmada. Si hay dos confirmaciones contradictorias, se descarta la identidad.
- **Velocidad.** Se mide como recorrido entre tiempo en ventanas de 1 s (0,2 s para el balón).
- **Récord de velocidad.** Se avisa al terminar el episodio por encima de 30 km/h, una sola vez.

## Cobertura de criterios

| Criterio | Evidencia | Estado |
|---|---|---|
| Distancia y velocidad con trayectorias conocidas | `test_constant_speed_gives_exact_distance_and_top_speed`, `test_sprint_and_high_intensity_distance`, `test_periods_are_never_joined` | Cumplido |
| Saltos y pistas perdidas no cuentan | `test_impossible_jumps_and_lost_tracks_are_not_counted` | Cumplido |
| Balón y tiro | `test_ball_and_shot_speed_use_the_second_after_the_shot` | Cumplido |
| Presión por cercanía y forma | `test_pressure_by_proximity_positive_and_negative`, `test_team_shape_with_known_geometry` | Cumplido |
| Avisos una vez por episodio o hito | `test_speed_record_alert_once_per_episode_and_distance_milestones` | Cumplido |
| Observaciones de Persona 1 sin inventar identidad | `test_persona_1_observations_become_tracks_with_confirmed_identity_only`, `test_contradicting_identities_are_dropped`, `test_video_clock_places_observations_in_their_period` | Cumplido con observaciones construidas en la prueba |
| Origen indicado y sin muestras futuras | `test_mock_produces_persona_1_observations_and_plausible_values`, `test_snapshot_uses_tracking_up_to_its_own_time_only` | Cumplido |

## Reproducción

```bash
.venv/Scripts/python -m pytest apps/backend/tests/test_analytics_tracking.py -q
```

## Resultado

```text
13 passed
```

Suite completa del 13 de octubre de 2026: 225 pruebas pasan (134 de antes y 91 de Persona 2).

## Limitaciones y riesgos

- Las cifras de las observaciones simuladas son de ejemplo y no deben presentarse como mediciones.
- Sin una clase de objeto en `VisualTrackObservation`, el balón y los porteros dependen de convenciones acordadas aparte.
- La regla de huecos de 0,3 s supone 5 observaciones por segundo o más por pista.
- `ResolvedVisualIdentity` se resuelve por observación. Si Persona 1 la entrega solo para algunas, la pista toma la identidad confirmada de cualquiera de ellas.

## Dependencias

- Persona 1: observaciones reales de vídeo (DV-US-17 y DV-US-19) y una forma de marcar balón y porteros.
- Persona 3 y Persona 4: decidir cómo llegan los avisos de seguimiento a la narración y a la pantalla.
