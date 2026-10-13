# Catálogo de métricas

Cada cifra de `MatchSnapshot v1` o `InsightCandidate v1` tiene una entrada en `domain/analytics/catalog.py` con la misma clave, unidad, origen y versión de fórmula. La prueba `test_every_emitted_metric_is_in_the_catalog_with_its_version` falla si el código emite una clave que no está aquí.

## Reglas comunes

- **Eventos de origen.** Cada cifra lleva `source_event_ids`. En los conteos, el valor es exactamente el número de eventos de origen. La prueba `test_every_count_can_be_recalculated_from_its_source_events` lo comprueba con los 178 eventos del escenario.
- **Cero o no disponible.** Un conteo vale cero cuando el flujo se observó y no hubo eventos de ese tipo. Una proporción sin denominador, o una métrica espacial sin posiciones o sin dirección de ataque, queda con `available: false`, sin valor y con `unavailable_reason`. Nunca se reemplaza por cero.
- **Coordenadas.** `x'` es la posición normalizada hacia la portería rival según `attacking_directions`: `x' = 100` es siempre la portería que el equipo ataca. Sin dirección no se calcula nada que dependa del sentido.
- **Metros.** `dx × pitch_length_m / 100` y `dy × pitch_width_m / 100`.
- **Ventanas.** `(inicio, fin]` sobre `clock_ms` dentro de un solo período. Una ventana no cruza el descanso. Las cifras con ventana indican `window_ms`, `period`, `window_start_clock_ms` y `window_end_clock_ms`.
- **Origen.** `event_count` es un conteo directo; `derived`, un cálculo con fórmula; `team_indicator`, una escala propia del equipo; `value_model`, la salida de un modelo validado.
- **Componentes.** Los porcentajes y los indicadores muestran su numerador, denominador o componentes en `components`.

## Estado del partido (`possession@1`)

| Clave | Ámbito | Unidad | Fórmula | Sin datos |
|---|---|---|---|---|
| `score` | equipo | goles | Tiros con resultado `goal`. Un gol deja la posesión vacía. | 0-0 al empezar |
| `possession_team_id` | partido | equipo | Equipo del último evento que dio la posesión | `null` antes del primer evento, tras un gol y al empezar un período |
| `possession_changes` | partido | count | Veces que la posesión pasa de un equipo al otro. La primera posesión de un período no cuenta. | 0 |
| `possession_won` | equipo | count | Cambios de posesión a favor del equipo | 0 |
| `possession_share` | equipo | percent | 100 × tiempo de posesión del equipo / tiempo atribuido a ambos | No disponible sin tiempo atribuido |

Dan la posesión: `pass`, `shot`, `recovery` y `possession_change` con cualquier resultado, y `tackle` con `success`. No la cambian `pressure` ni un `tackle` fallido. El tiempo se mide entre eventos del mismo período y no se extrapola después del último evento. El reloj del snapshot sí avanza con el vídeo cuando se pide en un `video_time_ms` posterior.

## Estadísticas básicas

| Clave | Ámbito | Unidad | Fórmula | Datos | Sin datos |
|---|---|---|---|---|---|
| `goals` | equipo, jugador | count | `shot` con `goal` | tipo, resultado | 0 |
| `shots` | equipo, jugador | count | `shot` con cualquier resultado | tipo | 0 |
| `shots_on_target` | equipo, jugador | count | `shot` con `goal` o `saved` | tipo, resultado | 0 |
| `passes_attempted` | equipo, jugador | count | `pass` con cualquier resultado | tipo | 0 |
| `passes_completed` | equipo, jugador | count | `pass` con `success` | tipo, resultado | 0 |
| `pass_accuracy` | equipo, jugador | percent | 100 × `success` / (`success` + `failure`). `unknown` no entra en el denominador. | tipo, resultado | No disponible sin pases con resultado conocido |
| `recoveries` | equipo, jugador | count | `recovery` | tipo | 0 |
| `tackles` | equipo, jugador | count | `tackle` | tipo | 0 |
| `tackles_won` | equipo, jugador | count | `tackle` con `success` | tipo, resultado | 0 |
| `pressures` | equipo, jugador | count | `pressure` | tipo | 0 |
| `involvement` | jugador | count | Eventos con su `player_id` | `player_id` | Solo se publica si tiene eventos |

## Calidad de pase y territorio (RF-10)

| Clave | Ámbito | Unidad | Fórmula | Sin datos |
|---|---|---|---|---|
| `avg_pass_distance_m` | equipo, jugador | meters | Media de la distancia entre `start` y `end` de los pases con ambas posiciones | No disponible sin pases con posiciones |
| `longest_pass_m` | equipo, jugador | meters | Mayor distancia de un pase `success` | No disponible sin pases `success` con posiciones |
| `progressive_passes` | equipo, jugador | count | Pase `success` que avanza al menos 10 m hacia la portería rival y termina en `x' ≥ 33,3` | No disponible si ningún pase puede evaluarse |
| `final_third_entries` | equipo | count | Pase `success` con `x' < 66,7` al empezar y `x' ≥ 66,7` al terminar | Igual |
| `high_recoveries` | equipo | count | `recovery`, `possession_change` o `tackle` ganado con inicio en `x' ≥ 60` | Igual |
| `pass_forward_gain_m` | evento | meters | `(x' final − x' inicial) × pitch_length_m / 100` | Se omite |
| `pass_distance_m` | evento | meters | Distancia del pase | Se omite |
| `shot_distance_m` | evento | meters | Distancia desde el tiro al centro de la portería rival | Se omite |
| `shot_angle_deg` | evento | degrees | Ángulo visible entre los postes (7,32 m) desde el tiro | Se omite |

Las métricas espaciales muestran en `components` cuántos eventos pudieron evaluarse (`evaluated_events`). No hay todavía una **dificultad de pase**: necesita presión real sobre el pasador, rivales y líneas de pase, y `MatchEvent 1.0` no los trae.

## Velocidad y distancia (RF-12)

Con solo `MatchEvent 1.0`, `ball_speed_kmh`, `shot_speed_kmh` y `distance_covered_m` salen como no disponibles: un pase con inicio y fin no dice cuánto tardó el balón, y el formato pide expresamente no estimarlo así. Con las observaciones de seguimiento de Persona 1 (`VisualTrackObservation`) se calculan, junto con `top_speed_kmh`, `sprints`, `high_intensity_distance_m`, `team_width_m`, `team_depth_m`, `team_compactness_m`, `pressure_proximity_share` y `nearest_defender_m`. Esas cifras llevan `tracking_evidence` con el origen (`simulated_fixture` o `actual_model`). Las fórmulas y reglas de limpieza están en [analítica de seguimiento](analitica-de-seguimiento.md).

## Jugadas (`sequence@1`)

| Clave | Unidad | Fórmula |
|---|---|---|
| `sequence_passes` | count | Pases del equipo en la jugada |
| `sequence_duration_s` | seconds | Reloj del último evento propio menos el del primero |
| `forward_progress` | pitch_percent | Mayor `x'` alcanzada menos `x'` de la primera acción con posición |
| `forward_progress_m` | meters | `forward_progress × pitch_length_m / 100` |
| `seconds_since_recovery` | seconds | Reloj del tiro menos el del evento que ganó el balón |

Las posiciones de una jugada son los inicios de cada acción y los finales de los pases `success`.

## Patrones con ventana

| Clave | Unidad | Fórmula |
|---|---|---|
| `defensive_actions_opponent_half` | count | `pressure`, `tackle`, `recovery` y `possession_change` del equipo con inicio en `x' ≥ 50` en 90 s |
| `ball_wins_opponent_half` | count | De esas, las que ganan el balón |

## Hitos (`milestone@1`)

| Clave | Unidad | Fórmula |
|---|---|---|
| contador del jugador (`passes_completed`, `progressive_passes`, `recoveries`, `tackles_won`, `shots_on_target`, `goals`) | count | Umbral alcanzado; los eventos de origen son todos los que suman |
| `match_longest_pass_m` | meters | Nuevo pase más largo del partido (≥ 40 m, 5 m más que el anterior, tras 10 pases `success` del partido) |

Umbrales: pases completados 10, 25 y 50; pases progresivos 3, 5 y 10; recuperaciones 3, 5 y 8; entradas ganadas 3 y 5; tiros a puerta 3; goles 2 y 3.

## Indicadores propios

Son escalas de este proyecto, con origen `team_indicator`. No son estadísticas oficiales y deben presentarse junto con sus componentes.

**`control_index` (`control@1`, 0-100 por equipo, ventana de 3 min).** Media ponderada de tres cuotas del equipo: posesión por tiempo (peso 0,4), pases completados (0,3) y eventos con inicio en el último tercio (0,3). Si un componente no tiene datos en ninguno de los dos equipos, se omite y se reparten los pesos restantes. Los dos equipos suman 100. No disponible con menos de 8 eventos o menos de 2 componentes.

**`momentum_index` (`momentum@1`, 0-100 por equipo).** Cuota de amenaza reciente con semivida de 120 s y horizonte de 10 min. Pesos: tiro 2, +1 si va a puerta, +1 si es gol, entrada al último tercio 1, pase progresivo 0,5 y recuperación alta 1. No disponible si la suma ponderada de ambos es menor que 0,5.

**`chaos_index` (`chaos@1`, 0-100 del partido, ventana de 3 min).** `100 × Σ peso × min(1, valor / referencia) / Σ pesos` con tres componentes: cambios de posesión por minuto (referencia 6, peso 0,5), proporción de pases fallidos (0,5 y 0,25; necesita al menos 4 pases con resultado) y duelos por minuto (`tackle` y `recovery`; 5 y 0,25). No disponible si la ventana dura menos de 60 s o tiene menos de 6 eventos.

Las referencias se eligieron para separar las fases del escenario sintético: con 4 cambios por minuto, la fase de presión alta ya llegaba a 60. Un partido real ronda los 2 cambios por minuto. Deben revisarse con partidos sintéticos más largos.

## Modelos de valor

| Clave | Unidad | Estado |
|---|---|---|
| `xt_added` | xt | Desactivada hasta tener una cuadrícula con licencia y validación |
| `xg` | xg | Desactivada hasta tener coeficientes con licencia y validación |
| `vaep` | vaep | Desactivada; faltan campos en `MatchEvent 1.0` |

El motivo exacto aparece en `unavailable_reason`. El [informe de viabilidad](informe-modelos-de-valor.md) explica cómo activarlas.

## Ejemplo con el partido de aceptación de Persona 1

Valores al final del partido (`evt-010`, 32 s), tomados de [`match-snapshot-v1.valido.json`](ejemplos/match-snapshot-v1.valido.json):

| Cifra | Aurora FC | Río Unido | Cómo comprobarla |
|---|---|---|---|
| Marcador | 1 | 0 | `evt-010` es un `shot` con `goal` |
| Pases completados / intentados | 4 / 4 | 0 / 0 | `evt-002`, `evt-003`, `evt-007`, `evt-009` |
| Precisión de pase | 100 % | no disponible | Río no tiene pases con resultado |
| Posesión por tiempo | 79,2 % | 20,8 % | Aurora 8-16 s y 21-32 s (19 s); Río 16-21 s (5 s) |
| Pases progresivos | 4 | no disponible | Avances de 14,5 a 21 m hacia la portería rival |
| Entradas al último tercio | 2 | no disponible | `evt-007` (x' 46,8 → 66,9) y `evt-009` (66,1 → 85,4) |
| Pase más largo | 22,7 m | no disponible | `evt-009` |
| `control_index` | 91,7 | 8,3 | Componentes en el snapshot |
| `chaos_index` | no disponible | | La ventana dura 32 s, menos de 60 |
