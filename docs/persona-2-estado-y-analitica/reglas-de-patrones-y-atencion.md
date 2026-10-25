# Reglas de jugadas, patrones y atención

Los detectores son causales: al procesar un evento solo ven ese evento y los anteriores. Por eso un momento emitido durante la reproducción no cambia cuando llegan eventos nuevos. Las pruebas `test_moments_of_a_prefix_never_change_when_more_events_arrive` y `test_cached_analytics_answers_growing_and_shrinking_prefixes_like_fresh_runs` lo comprueban.

Cuando una regla no puede evaluarse por falta de posiciones o de dirección de ataque, el analizador registra una nota (`DetectionNote`) y no emite nada.

## Jugadas (`sequence@1`, RF-29)

Una jugada empieza con un evento que da la posesión y sigue mientras el mismo equipo actúa con el balón. Termina con un tiro, cuando el rival gana el balón, tras más de 20 s sin acciones propias o al cambiar de período. Las presiones y entradas fallidas del rival quedan como contexto.

| Caso | Resultado | Prueba |
|---|---|---|
| Recuperación, dos pases y gol del partido de aceptación | Una jugada `seq-evt-006` con 4 eventos, la presión `evt-008` como contexto, 3 jugadores y 11 s | `test_acceptance_match_groups_recovery_passes_and_goal_into_one_sequence` |
| Pausa de 29 s y cambio de período | Tres jugadas: `stopped`, `period_end` y `ongoing` | `test_long_pause_and_new_period_close_a_sequence` |

El momento de un gol cita todos los eventos de su jugada y el marcador resultante (`test_goal_moment_cites_the_whole_sequence_and_resulting_score`).

## Patrones

### Progresión rápida (`fast_progression@1`)

**Regla.** En los primeros 15 s de una jugada, el balón avanza al menos 30 de `x'` desde la primera acción con posición y llega al último tercio (`x' ≥ 66,7`), con al menos dos eventos distintos. Se emite una vez por jugada, en el evento que cruza el umbral.

| Caso | Resultado | Prueba |
|---|---|---|
| Recuperación en 40 y pases hasta 72 en 6 s | Positivo en `evt-003`; el pase siguiente no repite | `test_fast_progression_positive_is_emitted_once_when_threshold_is_crossed` |
| +35 en 18 s | Negativo: demasiado lento | `test_fast_progression_negative_slow_or_short` |
| Llega al último tercio con +20 | Negativo: avance corto | `test_fast_progression_negative_slow_or_short` |
| Jugada sin posiciones | Sin señal, con nota | `test_fast_progression_without_positions_is_noted_not_emitted` |
| Equipo que ataca de derecha a izquierda | Positivo con coordenadas normalizadas | `test_right_to_left_team_uses_normalized_coordinates` |
| Empate de Río en el escenario tras 40 s de elaboración | Negativo | `escenario-analitica.analitica.json` |

**Límite.** El avance se mide con los puntos de inicio y fin de cada evento; no hay seguimiento continuo del balón.

### Recuperación que acaba en tiro (`recovery_to_shot@1`)

**Regla.** La jugada empieza ganando el balón (`recovery`, `tackle` o `possession_change`) y termina en tiro en 15 s o menos.

| Caso | Resultado | Prueba |
|---|---|---|
| Tiro 8 s después de recuperar | Positivo, con `seconds_since_recovery = 8` | `test_recovery_to_shot_positive_and_negative` |
| Tiro 17 s después | Negativo | Igual |
| Jugada que empezó con un pase | Negativo | Igual |

**Límite (RF-16).** Es una relación temporal. El momento lleva escrito que los eventos no demuestran que una acción causara la otra.

### Presión sostenida (`sustained_pressure@1`)

**Regla.** En una ventana de 90 s, el equipo suma al menos 5 acciones defensivas (`pressure`, `tackle`, `recovery`, `possession_change`) con inicio en campo rival (`x' ≥ 50`), y al menos 2 de ellas ganan el balón. Se emite al cumplirse y se rearma cuando la ventana deja de cumplirla. Los hechos comparan la ventana actual con los 90 s anteriores (RF-17) e incluyen la precisión de pase del rival en la ventana cuando existe.

| Caso | Resultado | Prueba |
|---|---|---|
| 3 presiones y 2 recuperaciones en campo rival en 40 s | Positivo | `test_sustained_pressure_positive_in_opponent_half` |
| Las mismas acciones en campo propio | Negativo | `test_sustained_pressure_negative_cases` |
| 5 presiones sin ganar el balón | Negativo | Igual |
| Acciones separadas más de 90 s | Negativo | Igual |
| Acciones sin posición o sin dirección | Sin señal; nota si falta la dirección | `test_sustained_pressure_ignores_unpositioned_actions_and_requires_direction` |
| Presión alta de Río en el escenario | Positivo a los 190 s: 5 acciones frente a 0 en el tramo anterior | `test_scenario_pressure_is_compared_with_the_previous_window` |

**Límite.** Cuenta acciones registradas como eventos; no mide la distancia real entre jugadores.

### Pase progresivo y recuperación alta

`progressive_pass@1` convierte cada pase progresivo del catálogo en un momento menor, y `high_recovery@1` hace lo mismo con cada balón ganado en `x' ≥ 60`. Tienen prioridad base baja: el modo analista los recibe y el casual casi nunca.

### Hitos de jugador (`milestone@1`, RF-30)

**Regla.** Se emite en el evento exacto en que el contador del jugador alcanza un umbral, una sola vez. También se emite un nuevo récord de pase del partido si supera 40 m, mejora el anterior en 5 m y ya hubo 10 pases completados.

| Caso | Resultado | Prueba |
|---|---|---|
| 12 pases completados | Un hito en el décimo (`evt-010`) con sus 10 eventos | `test_milestone_is_emitted_once_at_the_exact_event` |
| 9 completados y 1 fallido | Sin hito | Igual |
| Pase de 60 m tras 10 pases, y otro que mejora menos de 5 m | Un solo récord, con el anterior como componente | `test_match_record_pass_needs_distance_improvement_and_history` |
| Pase de 60 m al inicio del partido | Sin récord | Igual |

**Límite.** Solo suman eventos con `player_id`; no se infiere identidad.

### Cambio de control (`control_shift@1`, RF-31)

**Regla.** Compara `control_index` en dos ventanas consecutivas de 3 min del mismo período. Se emite cuando un equipo pasa a liderar con al menos 60, venía de menos de 50 y ganó al menos 20 puntos. No se repite para el mismo líder en el período.

| Caso | Resultado | Prueba |
|---|---|---|
| Escenario: Aurora domina y luego Río presiona y retiene | Positivo para Río a los 268 s (de 5 a 61,4) | `test_scenario_control_shift_and_chaos_phase_happen_in_their_phases` |
| Un solo equipo con el balón durante 400 s | Negativo | `test_one_sided_control_does_not_trigger_a_shift_and_calm_play_is_not_chaos` |

### Fase de caos (`chaos_phase@1`, RF-32)

**Regla.** Se emite cuando `chaos_index` llega a 60 y se rearma al bajar de 40.

| Caso | Resultado | Prueba |
|---|---|---|
| Escenario: pérdidas cada pocos segundos entre 332 y 452 s | Positivo a los 361 s; la fase de presión no pasa de 43 | `test_scenario_control_shift_and_chaos_phase_happen_in_their_phases` |
| Juego tranquilo de un solo equipo | Negativo | `test_one_sided_control_does_not_trigger_a_shift_and_calm_play_is_not_chaos` |
| 12 ciclos de pérdida y recuperación | Positivo, con los tres componentes, pesos y referencias | `test_chaotic_stretch_triggers_chaos_with_visible_components` |

Ambos indicadores llevan en `evidence_limits` que son escalas del equipo y no estadísticas oficiales.

### Situaciones del partido (`situation@1`)

Desde el 25 de octubre de 2026, `MatchEvent 1.0` trae faltas, tarjetas y detenciones como eventos propios (rama `develop`). La regla no infiere nada: cada `foul`, `yellow_card`, `red_card` o `injury_stoppage` es un momento.

- Las faltas y tarjetas citan el conteo del equipo y del jugador hasta ese evento (`fouls`, `yellow_cards`, `red_cards`).
- La detención cita `stoppage_seconds`, que sale de `stoppage_ms`, y avisa en `evidence_limits` que no es un diagnóstico médico.
- La roja se emite siempre, como el gol.
- Una falta repetida en menos de 2 minutos pierde 20 puntos por repetición, así que no todas se muestran.

| Caso | Resultado | Prueba |
|---|---|---|
| Dos faltas y una amarilla del mismo jugador | Conteos 1 y 2; la segunda falta se descarta por repetición | `test_cards_and_fouls_count_per_team_and_player` |
| Roja en modo casual | Se emite siempre | `test_red_card_is_always_emitted_and_events_without_situations_are_not` |
| Detención de 12 s | `stoppage_seconds = 12` con su límite | `test_injury_stoppage_reports_the_event_duration_and_its_limit` |
| Partido en vivo de Persona 4 | El modo casual ve tarjetas y lesión; las faltas solo el analista | `test_casual_viewers_see_cards_but_not_every_foul` |

## Motor de atención (`attention@1`, RF-14)

### Fusión

Las señales del mismo evento forman un único momento con identificador `moment-<event_id>`. El tipo principal es el de mayor rango, en este orden:

`goal` › `shot` › `recovery_to_shot` › `fast_progression` › `sustained_pressure` › `control_shift` › `chaos_phase` › `player_milestone` › `high_recovery` › `progressive_pass`

Los hechos, jugadores, fuentes y límites de todas las señales se unen sin duplicados. `signals` conserva la lista completa.

### Prioridad

La prioridad es la suma visible de estos puntos, recortada entre 0 y 100. Cada punto aparece en `reasons` con su código.

| Código | Puntos | Cuándo |
|---|---|---|
| `base_kind` | goal 80, red_card 80, yellow_card 55, injury_stoppage 50, recovery_to_shot 50, fast_progression 50, sustained_pressure 50, control_shift 50, shot 45, chaos_phase 45, player_milestone 40, high_recovery 35, foul 30, progressive_pass 25 | Siempre |
| `measured_fact` | 0 a 15 | Fuerza del hecho según la regla, por ejemplo +6 por tiro a puerta o +3 si es a menos de 16,5 m |
| `combined_signals` | +5 por señal extra, máximo +10 | Otras reglas en el mismo evento |
| `novelty` | +10 | Primer momento emitido de ese tipo para ese equipo |
| `repetition` | −20 | El mismo tipo para el mismo equipo se emitió hace menos de 2 min en el período |
| `favorite_team` | +10 | Momento del club favorito |
| `favorite_player` | +15 | Participa el jugador favorito |
| `analyst_mode` | +10 | Modo analista y tipo analítico |
| `casual_mode` | −10 | Modo casual y `control_shift` o `chaos_phase` |
| `player_mode_involved` | +20 | Modo jugador y participa |
| `player_mode_not_involved` | −30 | Modo jugador, no participa y no es gol |
| `decisive_fact` | 0 | Los goles y las rojas se emiten siempre, también los del rival (RF-24) |
| `below_threshold` | 0 | Motivo del descarte |

### Umbral por perfil

| Perfil | Umbral |
|---|---|
| Neutro (flujo publicado en Azure) | 40 |
| Casual | 50 |
| Analista | 35 |
| Jugador | 45 |

Cada momento genera una `AttentionDecision` con `emitted` o `discarded`, la prioridad, el umbral y los motivos. El ejemplo [`attention-decision-v1.descartado.json`](ejemplos/attention-decision-v1.descartado.json) muestra un descarte.

### Comprobaciones

| Requisito | Prueba |
|---|---|
| RF-14: varios tiros parecidos no generan varios mensajes | `test_similar_repeated_moments_are_limited_with_visible_reason` |
| La prioridad es la suma de sus motivos | `test_priority_is_the_visible_sum_of_reasons_and_stays_in_range` |
| RF-24: el gol rival se emite para la afición del otro club | `test_rival_goal_is_emitted_even_for_the_other_favorite_club` |
| RF-24: el club favorito sube prioridad sin cambiar hechos | `test_favorite_club_raises_its_moments_without_changing_facts` |
| RF-25: el jugador favorito solo cambia sus momentos | `test_favorite_player_changes_only_moments_where_they_take_part` |
| RF-26: el modo jugador lo sigue y conserva los goles | `test_player_mode_follows_the_player_and_keeps_decisive_goals` |
| RF-23: casual y analista reciben selecciones distintas de los mismos hechos | `test_casual_and_analyst_receive_different_selections_of_the_same_facts` |

### Resultado con el escenario de 178 eventos

| Perfil | Emitidos | Descartados |
|---|---|---|
| Neutro | 19 | 33 |
| Casual | 14 | 38 |
| Analista | 33 | 19 |
| Casual, club Río | 17 | 35 |
| Jugador `aurora-8` | 9 | 43 |

El detalle por momento está en [`escenario-analitica.analitica.json`](ejemplos/escenario-analitica.analitica.json).

## Tipos de momento

La narración debe cubrir estos valores de `kind`:

| `kind` | Qué ocurrió | Hechos principales |
|---|---|---|
| `goal` | Gol | `goals` de ambos equipos, jugada, distancia y ángulo |
| `shot` | Tiro sin gol | `shots` del jugador, jugada, distancia y ángulo |
| `recovery_to_shot` | Tiro poco después de ganar el balón (normalmente fusionado en `goal` o `shot`) | `seconds_since_recovery` |
| `fast_progression` | Avance rápido hacia el último tercio | `forward_progress`, `forward_progress_m`, `sequence_duration_s` |
| `sustained_pressure` | Presión sostenida en campo rival | acciones y balones ganados en la ventana actual y la anterior |
| `control_shift` | Cambio del equipo con más control | `control_index` actual y anterior con componentes |
| `chaos_phase` | Fase de cambios frecuentes | `chaos_index` con componentes |
| `player_milestone` | Hito de un jugador | contador alcanzado o `match_longest_pass_m` |
| `high_recovery` | Balón ganado en campo rival | `high_recoveries` del equipo |
| `progressive_pass` | Pase que acerca el balón a la portería rival | `pass_forward_gain_m`, `pass_distance_m` |
| `foul` | Falta | `fouls` del equipo y del jugador |
| `yellow_card`, `red_card` | Tarjeta | `yellow_cards` o `red_cards` del equipo y del jugador |
| `injury_stoppage` | Juego detenido por lesión | `stoppage_seconds` |
