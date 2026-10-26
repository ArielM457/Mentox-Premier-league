# Analítica de seguimiento

`MatchEvent 1.0` dice qué pasó y dónde empezó y terminó cada acción, pero no cómo se movieron los jugadores y el balón entre eventos. Con posiciones sucesivas y su tiempo se pueden medir velocidad, distancia, sprints, velocidad del balón, presión por cercanía y forma del equipo. El reto lo pide así: indicadores de velocidad y distancia que se activan al alcanzar umbrales predefinidos.

Persona 2 solo calcula. Las posiciones las entrega Persona 1 con su propio formato de visión, y esta analítica se adapta a él.

- **Estado:** cálculos verificados con trayectorias de resultado conocido; entrada desde el formato de Persona 1 verificada con observaciones simuladas.
- **Pendiente:** recibir observaciones reales de vídeo de Persona 1 (DV-US-17 y DV-US-19).

## Entrada: observaciones de visión de Persona 1

La analítica usa los mismos objetos que Persona 1 ya definió en `application/visual_identity.py` y `application/vision_evaluation.py`:

| Objeto de Persona 1 | Qué aporta | Cómo lo usa la analítica |
|---|---|---|
| `VisualTrackObservation` | Una pista en un instante: `track_id`, `video_time_ms`, `team_id`, `detector_confidence` y `position` de 0 a 100 en el campo fijo | Cada observación es una muestra de su pista; la posición se pasa a metros con las dimensiones del partido |
| `ResolvedVisualIdentity` | Identidad de la pista. Solo es `confirmed` con evidencia ajena al detector (DV-US-12) | Una pista lleva `player_id` solo con identidad confirmada; si dos confirmaciones se contradicen, se descarta la identidad |
| `PredictionOrigin` | `actual_model` o `simulated_fixture` | Cada cifra lo repite en `tracking_evidence.source` y en los avisos |

`application/analytics/tracking_input.py` hace la conversión:

1. Ubica cada observación en `(period, clock_ms)` con el reloj de los eventos. Para cada período usa la diferencia entre `video_time_ms` y `clock_ms` de su primer evento.
2. Descarta y cuenta las observaciones de otro partido, sin posición, anteriores al inicio o repetidas para la misma pista e instante.
3. Arma un `TrackSet` con las pistas en orden deportivo. Los cálculos del dominio (`domain/analytics/tracking.py`) solo trabajan sobre ese `TrackSet`.

**A acordar con Persona 1.** `VisualTrackObservation` todavía no indica la clase del objeto. Mientras tanto:

- El balón se reconoce por su `track_id` (por defecto, `ball`).
- Los porteros, por `goalkeeper_player_ids`.
- Una pista sin equipo que no es el balón (por ejemplo, el árbitro) queda como `unassigned` y no entra en las cifras de jugadores.

Si Persona 1 añade la clase a su observación, el adaptador la usará y estas convenciones desaparecen. Su adaptador de SoccerNet GameState ya la trae: produce cuadros con `referee` (valor `TrackedKind.REFEREE`), que tampoco entran en las cifras de jugadores.

## Reglas de limpieza

- Un tramo entre dos muestras solo cuenta si son del mismo período y están separadas por 0,3 s o menos. Un hueco mayor significa que la pista se perdió.
- Un tramo a más de 12 m/s (43 km/h) para una persona, o a más de 40 m/s (144 km/h) para el balón, se descarta como error de seguimiento. El número de tramos descartados aparece en `components`.
- Las velocidades son medias del recorrido en ventanas de 1 s (0,2 s para el balón), no de un solo par de muestras.

## Métricas (`tracking@1`)

| Clave | Ámbito | Unidad | Fórmula |
|---|---|---|---|
| `distance_covered_m` | jugador | meters | Suma de tramos válidos |
| `high_intensity_distance_m` | jugador | meters | Distancia en tramos a 19,8 km/h o más |
| `top_speed_kmh` | jugador | km/h | Máxima velocidad media en ventanas de 1 s |
| `sprints` | jugador | count | Episodios de al menos 1 s a 25,2 km/h o más |
| `ball_speed_kmh` | partido | km/h | Máxima velocidad media del balón en ventanas de 0,2 s |
| `shot_speed_kmh` | tiro | km/h | Máxima velocidad del balón en el segundo posterior a cada `shot`; cita el evento |
| `team_width_m` | equipo | meters | Media por instante del ancho ocupado por los jugadores de campo |
| `team_depth_m` | equipo | meters | Media por instante de la distancia entre el más adelantado y el más retrasado |
| `team_compactness_m` | equipo | meters | Media por instante de la distancia de cada jugador de campo a su centro |
| `pressure_proximity_share` | equipo | percent | Instantes con el rival en control (a ≤ 2 m del balón) y un defensor a ≤ 5 m, sobre los instantes con el rival en control |
| `nearest_defender_m` | equipo | meters | Distancia media del defensor más cercano al poseedor rival |

Las cifras de una pista sin identidad confirmada se publican con `player_id` vacío y su `track_id` en `tracking_evidence`. `build_snapshot(..., tracking=track_set)` y `MatchAnalytics(tracking_provider=...)` reemplazan las cifras de velocidad y distancia que antes salían no disponibles, usando solo las muestras hasta el instante del snapshot.

## Avisos por umbral (`tracking_alert@1`)

| Tipo | Regla |
|---|---|
| `speed_record` | Al terminar un episodio por encima de 30 km/h, si su pico supera en al menos 1 km/h el último récord avisado del partido. Un sprint produce un solo aviso. |
| `distance_milestone` | Cuando un jugador alcanza cada 1 000 m recorridos. |

Cada aviso (`TrackingAlert v1`) lleva su cifra con evidencia, el origen y los límites de lo que se puede afirmar. Por ejemplo, que el seguimiento es simulado o que la pista no tiene identidad confirmada. Los avisos no pasan por `InsightCandidate v1`, porque ese contrato exige eventos de origen y Persona 4 calcula con ellos el tiempo de vídeo. Llevarlos al flujo de momentos requiere acordar el cambio con Persona 3 y Persona 4.

## Observaciones simuladas

`apps/backend/tests/tracking_mock.py` produce, a 5 muestras por segundo, exactamente lo que entregará Persona 1:

- `VisualTrackObservation` por pista e instante, con `detector_confidence = 1.0`.
- Identidades resueltas con su propio `PlayerIdentityResolver`, con la referencia de evidencia «mock de Persona 2».
- Origen `PredictionOrigin.SIMULATED_FIXTURE`.

Así, la analítica recorre con datos de prueba el mismo camino que recorrerá con datos reales.

Las posiciones salen de una cinemática simple a partir de los eventos del escenario:

- El balón pasa por el inicio de cada evento y viaja al final de pases (16 m/s) y tiros (27 m/s). Si un salto entre eventos fuera imposible (más de 32 m/s), el balón no aparece en esas muestras.
- Cada jugador tiene una zona que se desplaza con el balón y con la posesión. Quien interviene en un evento va hacia el lugar desde 4 s antes.
- Límites: 8,5 m/s para quien va a la acción, 5,5 m/s para el resto, 5 m/s para porteros y árbitro, y una aceleración de 3,5 m/s².

Con el escenario de 178 eventos (unos 9,9 minutos):

- Cada jugador de campo recorre entre 810 y 1 240 m, con velocidades máximas de 20 a 31 km/h. Los porteros recorren unos 340 m.
- El balón llega a 114 km/h; los tiros a puerta rondan los 97 km/h y los bloqueados, unos 50 km/h.
- La mayoría de los jugadores hace entre 0 y 6 sprints. El máximo, 9, es de un defensor al que el guion hace intervenir lejos de su zona durante la fase de caos.

Son valores de ejemplo, del orden de los de un partido real, pero no son mediciones y siempre se presentan como simulados.

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
| Reloj de vídeo por período | `test_video_clock_places_observations_in_their_period` |
| Observaciones de Persona 1 con identidad solo confirmada | `test_persona_1_observations_become_tracks_with_confirmed_identity_only` |
| Identidades contradictorias descartadas | `test_contradicting_identities_are_dropped` |
| Observaciones simuladas con el formato de Persona 1 y valores plausibles | `test_mock_produces_persona_1_observations_and_plausible_values` |
| El snapshot no usa muestras futuras | `test_snapshot_uses_tracking_up_to_its_own_time_only` |
