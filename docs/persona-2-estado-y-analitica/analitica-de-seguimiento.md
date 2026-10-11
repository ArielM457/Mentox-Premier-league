# Analítica de seguimiento

`MatchEvent 1.0` dice qué pasó y dónde empezó y terminó cada acción, pero no cómo se movieron los jugadores y el balón entre eventos. Con posiciones sucesivas y su tiempo (seguimiento) se pueden medir velocidad, distancia, sprints, velocidad del balón, presión por cercanía y forma del equipo. El reto lo pide así: indicadores de velocidad y distancia que se activan al alcanzar umbrales predefinidos.

- **Estado:** módulo implementado y verificado con trayectorias de resultado conocido y con seguimiento simulado.
- **Pendiente:** ejecutarlo con posiciones reales de Roboflow Sports sobre un vídeo permitido (DV-US-17 y DV-US-19 de Persona 1).

## Contrato `TrackingFrame v1`

Un cuadro contiene todas las posiciones conocidas en un instante:

```json
{
  "schema_version": "1",
  "match_id": "synthetic-analytics-001",
  "period": 1,
  "clock_ms": 471000,
  "video_time_ms": 474000,
  "source": "synthetic_mock",
  "objects": [
    {"track_id": "trk-aurora-9", "kind": "player", "team_id": "team-aurora",
     "player_id": "aurora-9", "x_m": 92.4, "y_m": 36.1, "confidence": null},
    {"track_id": "trk-ball", "kind": "ball", "team_id": null, "player_id": null,
     "x_m": 93.1, "y_m": 35.8, "confidence": null}
  ]
}
```

- `x_m` va de 0 a `pitch_length_m` en el mismo sentido que `x` de `MatchEvent`; `y_m` va de 0 a `pitch_width_m`.
- `kind` es `player`, `goalkeeper`, `referee` o `ball`.
- `source` es `synthetic_mock` o `video_model`, y cada cifra calculada lo repite en `tracking_evidence.source`.
- `player_id` solo se rellena con una identidad confirmada. Una pista de vídeo sin identidad se informa por `track_id` (DV-US-12).

Las cifras de seguimiento llevan `tracking_evidence` con fuente, pistas, intervalo y número de cuadros, en lugar de eventos de origen. Es un campo opcional nuevo de `MetricValue` y no rompe a quien no lo lea.

## Reglas de limpieza

- Un tramo entre dos cuadros solo cuenta si son del mismo período y están separados por 0,3 s o menos. Un hueco mayor significa que la pista se perdió.
- Un tramo a más de 12 m/s (43 km/h) para una persona, o a más de 40 m/s (144 km/h) para el balón, se descarta como error de seguimiento. El número de tramos descartados aparece en `components`.
- Las velocidades son medias del recorrido en ventanas de 1 s (0,2 s para el balón), no de un solo par de cuadros.

## Métricas (`tracking@1`)

| Clave | Ámbito | Unidad | Fórmula |
|---|---|---|---|
| `distance_covered_m` | jugador | meters | Suma de tramos válidos |
| `high_intensity_distance_m` | jugador | meters | Distancia en tramos a 19,8 km/h o más |
| `top_speed_kmh` | jugador | km/h | Máxima velocidad media en ventanas de 1 s |
| `sprints` | jugador | count | Episodios de al menos 1 s a 25,2 km/h o más |
| `ball_speed_kmh` | partido | km/h | Máxima velocidad media del balón en ventanas de 0,2 s |
| `shot_speed_kmh` | tiro | km/h | Máxima velocidad del balón en el segundo posterior a cada `shot`; cita el evento |
| `team_width_m` | equipo | meters | Media por cuadro del ancho ocupado por los jugadores de campo |
| `team_depth_m` | equipo | meters | Media por cuadro de la distancia entre el más adelantado y el más retrasado |
| `team_compactness_m` | equipo | meters | Media por cuadro de la distancia de cada jugador de campo a su centro |
| `pressure_proximity_share` | equipo | percent | Cuadros con el rival en control (a ≤ 2 m del balón) y un defensor a ≤ 5 m, sobre los cuadros con el rival en control |
| `nearest_defender_m` | equipo | meters | Distancia media del defensor más cercano al poseedor rival |

Con seguimiento, `build_snapshot(..., tracking=frames)` y `MatchAnalytics(tracking_provider=...)` reemplazan las cifras de velocidad y distancia que antes salían no disponibles. Solo usan los cuadros hasta el instante del snapshot.

## Avisos por umbral (`tracking_alert@1`)

| Tipo | Regla |
|---|---|
| `speed_record` | Al terminar un episodio por encima de 30 km/h, si su pico supera en al menos 1 km/h el último récord avisado del partido. Un sprint produce un solo aviso. |
| `distance_milestone` | Cuando un jugador alcanza cada 1 000 m recorridos. |

Cada aviso (`TrackingAlert v1`) lleva su cifra con evidencia y los límites de lo que se puede afirmar. Por ejemplo, que el seguimiento es simulado o que la pista no tiene identidad confirmada. Los avisos no pasan por `InsightCandidate v1`, porque ese contrato exige eventos de origen y Persona 4 calcula con ellos el tiempo de vídeo. Integrarlos en el flujo de momentos requiere acordar un cambio de contrato con Persona 3 y Persona 4.

## Seguimiento simulado

`adapters/sources/tracking_mock.py` genera cuadros a 5 Hz a partir de los eventos del escenario. Sirve para desarrollar y demostrar el módulo mientras no haya un vídeo procesado:

- El balón pasa por el inicio de cada evento y viaja al final de pases (16 m/s) y tiros (27 m/s). Si un salto entre eventos fuera imposible (más de 32 m/s), el balón no aparece en esos cuadros, como cuando un seguimiento real lo pierde.
- Cada jugador tiene una zona que se desplaza con el balón y con la posesión. Quien interviene en un evento va hacia el lugar desde 4 s antes.
- Límites: 8,5 m/s para quien va a la acción, 5,5 m/s para el resto, 5 m/s para porteros y árbitro, y una aceleración de 3,5 m/s².

Con el escenario de 178 eventos (unos 9,9 minutos), cada jugador de campo recorre entre 810 y 1 240 m, con velocidades máximas de 20 a 31 km/h. Los porteros recorren unos 340 m. El balón llega a 114 km/h, los tiros a puerta rondan los 97 km/h y los bloqueados, unos 50 km/h. La mayoría de los jugadores hace entre 0 y 6 sprints. El máximo, 9, es de un defensor al que el guion hace intervenir lejos de su zona durante la fase de caos. Son valores de ejemplo, del orden de los de un partido real, pero no son mediciones y siempre se presentan como simulados.

## Conexión con Roboflow Sports

`adapters/sources/roboflow_tracking.py` convierte detecciones ya proyectadas al campo, una por fila, en `TrackingFrame v1` con `source = video_model`:

```json
{"frame_index": 120, "fps": 25.0, "tracker_id": 7, "class_name": "player",
 "team": 0, "pitch_x": 4210.5, "pitch_y": 3120.0, "confidence": 0.91}
```

- `pitch_x` y `pitch_y` están en las unidades de la configuración del campo de Roboflow; por defecto, 12 000 × 7 000. Hay que confirmar ese valor con la revisión fijada del repositorio.
- `team` es el grupo del clasificador por color (0 o 1). Es arbitrario, así que hay que indicar qué `team_id` corresponde a cada grupo.
- No se asigna `player_id`.
- Si el detector ve varios balones en un cuadro, se conserva el de mayor confianza.
- Las clases desconocidas y las filas incompletas se ignoran y se cuentan.

Este formato de fila es una **propuesta para el script de exportación de Persona 1** (DV-US-19). Con él, el mismo módulo calcula las métricas reales sin cambios.

## Pruebas

| Comportamiento | Prueba |
|---|---|
| Velocidad constante: distancia y velocidad exactas | `test_constant_speed_gives_exact_distance_and_top_speed` |
| Sprint y distancia a alta intensidad | `test_sprint_and_high_intensity_distance` |
| Saltos imposibles y pistas perdidas | `test_impossible_jumps_and_lost_tracks_are_not_counted` |
| Los períodos no se unen | `test_periods_are_never_joined` |
| Velocidad del balón y del tiro | `test_ball_and_shot_speed_use_the_second_after_the_shot` |
| Presión por cercanía, positiva y negativa | `test_pressure_by_proximity_positive_and_negative` |
| Forma del equipo con geometría conocida | `test_team_shape_with_known_geometry` |
| Un aviso de récord por episodio e hitos de distancia | `test_speed_record_alert_once_per_episode_and_distance_milestones` |
| Seguimiento simulado determinista y plausible | `test_mock_tracking_is_deterministic_and_plausible` |
| El snapshot no usa cuadros futuros | `test_snapshot_uses_tracking_up_to_its_own_time_only` |
| Conversión de Roboflow sin inventar identidad | `test_roboflow_rows_become_video_frames_without_inventing_identity` |
