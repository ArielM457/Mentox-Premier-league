# Evidencia técnica de EA-US-10

## Identificación

- **Historia:** EA-US-10 · Medir velocidad y distancia desde posiciones.
- **Estado:** verificada con trayectorias de resultado conocido y seguimiento simulado; posiciones reales de vídeo pendientes.
- **Prioridad:** P2.
- **Última verificación:** 11 de octubre de 2026.
- **Responsable:** Persona 2 · Estado y analítica.
- **Requisitos relacionados:** RF-11, RF-12 y la sugerencia del reto de indicadores de velocidad y distancia que se activan por umbral.

## Objetivo comprobado

El módulo `tracking@1` calcula distancia, distancia a alta intensidad, velocidad máxima, sprints, velocidad del balón y del tiro, forma del equipo y presión por cercanía a partir de `TrackingFrame v1`, y emite avisos por umbral (`tracking_alert@1`). Cada cifra indica su fuente en `tracking_evidence`. Las reglas están en [analítica de seguimiento](../analitica-de-seguimiento.md).

## Alcance implementado

- Contratos `TrackingFrame v1`, `TrackedObject` y `TrackingAlert v1`, y el campo opcional `tracking_evidence` en `MetricValue`.
- Limpieza: huecos de más de 0,3 s, saltos de más de 12 m/s para personas y de 40 m/s para el balón.
- Integración en `build_snapshot(tracking=...)` y `MatchAnalytics(tracking_provider=...)`, sin usar cuadros posteriores al snapshot.
- Seguimiento simulado a 5 Hz desde los eventos (`tracking_mock.py`).
- Conversión de detecciones proyectadas de Roboflow Sports (`roboflow_tracking.py`), sin asignar identidad.

## Fuera del alcance

- Ejecutar Roboflow Sports sobre un vídeo: es DV-US-19 de Persona 1 y requiere un vídeo permitido, descargas de pesos y GPU.
- Llevar los avisos de seguimiento al contrato `InsightCandidate v1`, que exige eventos de origen. Hace falta acordar el cambio con Persona 3 y Persona 4.

## Cambios técnicos

| Archivo | Cambio |
|---|---|
| `domain/analytics/tracking.py` | Contratos, limpieza, métricas, avisos y distancia acumulada |
| `domain/analytics/models.py` | `TrackingEvidence` en `MetricValue` |
| `domain/analytics/catalog.py` | Claves de seguimiento con versión `tracking@1` |
| `application/analytics/pipeline.py` | Seguimiento opcional en el snapshot y en `MatchAnalytics` |
| `adapters/sources/tracking_mock.py` | Seguimiento simulado |
| `adapters/sources/roboflow_tracking.py` | Conversión desde Roboflow Sports |

## Decisiones técnicas

- Las velocidades se miden como recorrido entre tiempo en ventanas de 1 s (0,2 s para el balón), para no amplificar el ruido entre dos cuadros.
- Un récord de velocidad se avisa al terminar el episodio por encima de 30 km/h, con su pico, para no repetir el aviso mientras el jugador acelera.
- El seguimiento simulado se ajustó para dar valores del orden de un partido real. La primera versión daba 20 sprints y 690 m a alta intensidad en 10 minutos para un jugador, y un balón a 160 km/h al reaparecer tras no verse.

## Cobertura de criterios

| Criterio | Evidencia | Estado |
|---|---|---|
| Distancia y velocidad con trayectorias conocidas | `test_constant_speed_gives_exact_distance_and_top_speed`, `test_sprint_and_high_intensity_distance`, `test_periods_are_never_joined` | Cumplido |
| Saltos y pistas perdidas no cuentan | `test_impossible_jumps_and_lost_tracks_are_not_counted` | Cumplido |
| Balón y tiro | `test_ball_and_shot_speed_use_the_second_after_the_shot` | Cumplido |
| Presión por cercanía y forma | `test_pressure_by_proximity_positive_and_negative`, `test_team_shape_with_known_geometry` | Cumplido |
| Avisos una vez por episodio o hito | `test_speed_record_alert_once_per_episode_and_distance_milestones` | Cumplido |
| Fuente indicada y sin cuadros futuros | `test_mock_tracking_is_deterministic_and_plausible`, `test_snapshot_uses_tracking_up_to_its_own_time_only` | Cumplido |
| Roboflow sin inventar identidad | `test_roboflow_rows_become_video_frames_without_inventing_identity` | Cumplido con filas de ejemplo; falta una exportación real |

## Reproducción

```bash
.venv/Scripts/python -m pytest apps/backend/tests/test_analytics_tracking.py -q
```

## Resultado

```text
11 passed
```

Con el escenario de 178 eventos, los jugadores de campo simulados recorren entre 810 y 1 240 m, con velocidades máximas de 20 a 31 km/h; el balón llega a 114 km/h. Generar el seguimiento lleva unos 0,3 s y calcular todas las métricas, unos 0,2 s.

## Limitaciones y riesgos

- Las cifras del seguimiento simulado son de ejemplo y no deben presentarse como mediciones.
- Las unidades de la configuración del campo de Roboflow (12 000 × 7 000) y el formato de exportación deben confirmarse con la revisión fijada.
- La regla de huecos de 0,3 s supone 5 cuadros por segundo o más.
- Un defensor simulado hace 9 sprints en la fase de caos del guion; el resto, entre 0 y 6.

## Dependencias

- Persona 1: vídeo permitido (DV-US-17) y exportación de Roboflow Sports (DV-US-19) en el formato propuesto.
- Persona 3 y Persona 4: decidir cómo llegan los avisos de seguimiento a la narración y a la pantalla.
