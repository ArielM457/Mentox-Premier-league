"""Catálogo de métricas de Persona 2.

Cada clave emitida en ``MatchSnapshot`` o ``InsightCandidate`` debe figurar
aquí con su fórmula, unidad, datos necesarios y versión. Una prueba lo
comprueba para que el catálogo documentado no se separe del código.
"""

from dataclasses import dataclass

from .models import MetricOrigin


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    key: str
    scopes: tuple[str, ...]
    unit: str
    origin: MetricOrigin
    formula_version: str
    formula: str
    requires: tuple[str, ...]
    when_unavailable: str


_C = MetricOrigin.EVENT_COUNT
_D = MetricOrigin.DERIVED
_I = MetricOrigin.TEAM_INDICATOR
_M = MetricOrigin.VALUE_MODEL

METRIC_CATALOG: dict[str, MetricDefinition] = {
    item.key: item
    for item in (
        MetricDefinition("goals", ("team", "player"), "count", _C, "goals@1",
                         "Tiros con resultado goal.", ("type", "outcome"),
                         "Siempre disponible; cero si no hubo goles."),
        MetricDefinition("shots", ("team", "player"), "count", _C, "shots@1",
                         "Eventos shot con cualquier resultado.", ("type",),
                         "Siempre disponible."),
        MetricDefinition("shots_on_target", ("team", "player"), "count", _C, "shots_on_target@1",
                         "Tiros con resultado goal o saved.", ("type", "outcome"),
                         "Siempre disponible."),
        MetricDefinition("passes_attempted", ("team", "player"), "count", _C, "passes_attempted@1",
                         "Eventos pass con cualquier resultado.", ("type",),
                         "Siempre disponible."),
        MetricDefinition("passes_completed", ("team", "player"), "count", _C, "passes_completed@1",
                         "Pases con resultado success.", ("type", "outcome"),
                         "Siempre disponible."),
        MetricDefinition("pass_accuracy", ("team", "player"), "percent", _D, "pass_accuracy@1",
                         "100 × pases success / pases con resultado success o failure. "
                         "Los pases con resultado unknown no entran en el denominador.",
                         ("type", "outcome"),
                         "No disponible si no hay pases con resultado conocido."),
        MetricDefinition("recoveries", ("team", "player"), "count", _C, "recoveries@1",
                         "Eventos recovery.", ("type",), "Siempre disponible."),
        MetricDefinition("tackles", ("team", "player"), "count", _C, "tackles@1",
                         "Eventos tackle con cualquier resultado.", ("type",),
                         "Siempre disponible."),
        MetricDefinition("tackles_won", ("team", "player"), "count", _C, "tackles_won@1",
                         "Tackles con resultado success.", ("type", "outcome"),
                         "Siempre disponible."),
        MetricDefinition("pressures", ("team", "player"), "count", _C, "pressures@1",
                         "Eventos pressure con cualquier resultado.", ("type",),
                         "Siempre disponible."),
        MetricDefinition("possession_changes", ("match",), "count", _C, "possession@1",
                         "Veces que la posesión pasa de un equipo al otro según possession@1. "
                         "La primera posesión del período no cuenta como cambio.",
                         ("type", "outcome", "team_id"), "Siempre disponible."),
        MetricDefinition("possession_won", ("team",), "count", _C, "possession@1",
                         "Cambios de posesión en que el equipo recibe el balón.",
                         ("type", "outcome", "team_id"), "Siempre disponible."),
        MetricDefinition("possession_share", ("team",), "percent", _D, "possession@1",
                         "100 × tiempo de posesión del equipo / tiempo de posesión atribuido a "
                         "ambos. El tiempo se mide entre eventos del mismo período.",
                         ("clock_ms", "type", "team_id"),
                         "No disponible si todavía no hay tiempo de posesión atribuido."),
        MetricDefinition("progressive_passes", ("team", "player"), "count", _D, "progressive_pass@1",
                         "Pases success que avanzan al menos 10 m hacia la portería rival y "
                         "terminan fuera del tercio defensivo propio (x' ≥ 33,3).",
                         ("start", "end", "attacking_directions", "pitch_length_m"),
                         "No disponible si ningún pase tiene posiciones y dirección de ataque."),
        MetricDefinition("final_third_entries", ("team",), "count", _D, "final_third_entry@1",
                         "Pases success que empiezan antes del último tercio (x' < 66,7) y "
                         "terminan dentro.",
                         ("start", "end", "attacking_directions"),
                         "No disponible si ningún pase tiene posiciones y dirección de ataque."),
        MetricDefinition("high_recoveries", ("team",), "count", _D, "high_recovery@1",
                         "Recoveries, possession_change o tackles ganados con inicio en "
                         "x' ≥ 60 (campo rival).",
                         ("start", "attacking_directions"),
                         "No disponible si ninguna recuperación tiene posición y dirección."),
        MetricDefinition("avg_pass_distance_m", ("team", "player"), "meters", _D, "pass_distance@1",
                         "Media de la distancia euclídea entre start y end de los pases, "
                         "escalada con pitch_length_m y pitch_width_m.",
                         ("start", "end", "pitch_length_m", "pitch_width_m"),
                         "No disponible si ningún pase tiene ambas posiciones."),
        MetricDefinition("longest_pass_m", ("team", "player"), "meters", _D, "pass_distance@1",
                         "Mayor distancia de un pase success.",
                         ("start", "end", "outcome", "pitch_length_m", "pitch_width_m"),
                         "No disponible si ningún pase success tiene ambas posiciones."),
        MetricDefinition("involvement", ("player",), "count", _C, "involvement@1",
                         "Eventos con el player_id del jugador. No se infiere identidad.",
                         ("player_id",), "Solo se publica para jugadores con eventos."),
        MetricDefinition("ball_speed_kmh", ("match",), "km/h", _D, "tracking@1",
                         "Con seguimiento: máxima velocidad media del balón en ventanas de 0,2 s, "
                         "descartando tramos de más de 40 m/s y huecos de más de 0,3 s. Con solo MatchEvent 1.0 no hay "
                         "posiciones sucesivas con tiempo.",
                         ("tracking",), "No disponible sin seguimiento del balón."),
        MetricDefinition("shot_speed_kmh", ("match", "event"), "km/h", _D, "tracking@1",
                         "Con seguimiento: máxima velocidad del balón en el segundo posterior al "
                         "evento shot. Con solo MatchEvent 1.0 no hay duración del vuelo.",
                         ("tracking", "type", "clock_ms"),
                         "No disponible sin seguimiento del balón tras el tiro."),
        MetricDefinition("distance_covered_m", ("player",), "meters", _D, "tracking@1",
                         "Con seguimiento: suma de desplazamientos entre cuadros del mismo período, "
                         "descartando saltos de más de 12 m/s. Con solo MatchEvent 1.0 no hay "
                         "posiciones del jugador.",
                         ("tracking",), "No disponible sin seguimiento del jugador."),
        MetricDefinition("high_intensity_distance_m", ("player",), "meters", _D, "tracking@1",
                         "Distancia recorrida en tramos a 19,8 km/h o más.",
                         ("tracking",), "No disponible sin seguimiento."),
        MetricDefinition("top_speed_kmh", ("player",), "km/h", _D, "tracking@1",
                         "Máxima velocidad media en ventanas de 1 s (recorrido / tiempo).",
                         ("tracking",), "No disponible con menos de 1 s de seguimiento."),
        MetricDefinition("sprints", ("player",), "count", _D, "tracking@1",
                         "Episodios de al menos 1 s a 25,2 km/h o más.",
                         ("tracking",), "No disponible sin seguimiento."),
        MetricDefinition("team_width_m", ("team",), "meters", _D, "tracking@1",
                         "Media por cuadro de la distancia entre los jugadores de campo más "
                         "separados a lo ancho.", ("tracking",),
                         "No disponible con menos de 3 jugadores de campo por cuadro."),
        MetricDefinition("team_depth_m", ("team",), "meters", _D, "tracking@1",
                         "Media por cuadro de la distancia entre el jugador de campo más adelantado "
                         "y el más retrasado.", ("tracking",),
                         "No disponible con menos de 3 jugadores de campo por cuadro."),
        MetricDefinition("team_compactness_m", ("team",), "meters", _D, "tracking@1",
                         "Media por cuadro de la distancia de los jugadores de campo a su centro.",
                         ("tracking",), "No disponible con menos de 3 jugadores de campo por cuadro."),
        MetricDefinition("pressure_proximity_share", ("team",), "percent", _D, "tracking@1",
                         "100 × cuadros con el rival en control del balón (a ≤ 2 m) y un jugador "
                         "del equipo a ≤ 5 m del poseedor / cuadros con el rival en control.",
                         ("tracking",), "No disponible si el rival no controló el balón."),
        MetricDefinition("nearest_defender_m", ("team",), "meters", _D, "tracking@1",
                         "Distancia media del jugador más cercano del equipo al poseedor rival.",
                         ("tracking",), "No disponible si el rival no controló el balón."),
        MetricDefinition("shot_distance_m", ("event",), "meters", _D, "shot_geometry@1",
                         "Distancia desde start del tiro hasta el centro de la portería rival.",
                         ("start", "attacking_directions", "pitch_length_m", "pitch_width_m"),
                         "Se omite si el tiro no tiene posición o dirección."),
        MetricDefinition("shot_angle_deg", ("event",), "degrees", _D, "shot_geometry@1",
                         "Ángulo visible entre los postes (7,32 m) desde start del tiro.",
                         ("start", "attacking_directions", "pitch_length_m", "pitch_width_m"),
                         "Se omite si el tiro no tiene posición o dirección."),
        MetricDefinition("pass_forward_gain_m", ("event",), "meters", _D, "progressive_pass@1",
                         "Avance del pase hacia la portería rival: (x' final − x' inicial) × "
                         "pitch_length_m / 100.",
                         ("start", "end", "attacking_directions", "pitch_length_m"),
                         "Se omite si el pase no tiene posiciones o dirección."),
        MetricDefinition("pass_distance_m", ("event",), "meters", _D, "pass_distance@1",
                         "Distancia euclídea del pase escalada con las dimensiones del campo.",
                         ("start", "end", "pitch_length_m", "pitch_width_m"),
                         "Se omite si el pase no tiene ambas posiciones."),
        MetricDefinition("control_index", ("team",), "index_0_100", _I, "control@1",
                         "Indicador propio. Media ponderada de cuotas del equipo en la ventana: "
                         "posesión por tiempo (0,4), pases completados (0,3) y acciones en el "
                         "último tercio (0,3). Los dos equipos suman 100.",
                         ("clock_ms", "type", "outcome", "start", "attacking_directions"),
                         "No disponible con menos de 8 eventos o 2 componentes en la ventana."),
        MetricDefinition("momentum_index", ("team",), "index_0_100", _I, "momentum@1",
                         "Indicador propio. Cuota de amenaza reciente con semivida de 120 s: "
                         "tiro 2, a puerta +1, gol +1, entrada al último tercio 1, pase "
                         "progresivo 0,5 y recuperación alta 1.",
                         ("clock_ms", "type", "outcome", "start", "end", "attacking_directions"),
                         "No disponible si la amenaza ponderada de ambos es menor que 0,5."),
        MetricDefinition("chaos_index", ("match",), "index_0_100", _I, "chaos@1",
                         "Indicador propio. 100 × suma ponderada de componentes saturados: "
                         "cambios de posesión por minuto (ref. 6, peso 0,5), proporción de pases "
                         "fallidos (ref. 0,5, peso 0,25) y duelos (tackle y recovery) por minuto "
                         "(ref. 5, peso 0,25).",
                         ("clock_ms", "type", "outcome", "team_id"),
                         "No disponible con menos de 60 s de ventana o menos de 6 eventos."),
        MetricDefinition("defensive_actions_opponent_half", ("team",), "count", _D,
                         "sustained_pressure@1",
                         "Pressure, tackle, recovery y possession_change del equipo con inicio "
                         "en x' ≥ 50 dentro de la ventana.",
                         ("start", "attacking_directions", "clock_ms"),
                         "Los eventos sin posición no se cuentan."),
        MetricDefinition("ball_wins_opponent_half", ("team",), "count", _D, "sustained_pressure@1",
                         "Recovery, possession_change o tackle ganado con inicio en x' ≥ 50.",
                         ("start", "attacking_directions", "clock_ms"),
                         "Los eventos sin posición no se cuentan."),
        MetricDefinition("forward_progress", ("sequence",), "pitch_percent", _D, "fast_progression@1",
                         "Mayor x' alcanzada menos x' de la primera acción con posición de la "
                         "jugada. Usa inicios de acciones y finales de pases success.",
                         ("start", "end", "attacking_directions"),
                         "No se evalúa si la jugada no tiene posiciones y dirección."),
        MetricDefinition("forward_progress_m", ("sequence",), "meters", _D, "fast_progression@1",
                         "forward_progress × pitch_length_m / 100.",
                         ("start", "end", "attacking_directions", "pitch_length_m"),
                         "Igual que forward_progress."),
        MetricDefinition("sequence_duration_s", ("sequence",), "seconds", _D, "sequence@1",
                         "Reloj del último evento propio menos reloj del primero.",
                         ("clock_ms",), "Siempre disponible."),
        MetricDefinition("sequence_passes", ("sequence",), "count", _C, "sequence@1",
                         "Pases del equipo dentro de la jugada.", ("type",),
                         "Siempre disponible."),
        MetricDefinition("seconds_since_recovery", ("sequence",), "seconds", _D, "recovery_to_shot@1",
                         "Reloj del tiro menos reloj del evento que ganó el balón.",
                         ("clock_ms", "type"), "Solo si la jugada empezó ganando el balón."),
        MetricDefinition("match_longest_pass_m", ("player",), "meters", _D, "milestone@1",
                         "Nuevo pase success más largo del partido (≥ 40 m, al menos 5 m más que "
                         "el anterior y después de 10 pases success del partido).",
                         ("start", "end", "outcome", "player_id"),
                         "Solo con posiciones y player_id."),
        MetricDefinition("xt_added", ("team", "player", "event"), "xt", _M, "modelo",
                         "Suma de xT(final) − xT(inicio) de pases success con un modelo validado.",
                         ("start", "end", "attacking_directions", "modelo xT validado"),
                         "Desactivada si no hay un modelo xT validado."),
        MetricDefinition("xg", ("team", "player", "event"), "xg", _M, "modelo",
                         "Suma de la probabilidad de gol de cada tiro según un modelo validado.",
                         ("start", "attacking_directions", "modelo xG validado"),
                         "Desactivada si no hay un modelo xG validado."),
        MetricDefinition("vaep", ("team", "player"), "vaep", _M, "modelo",
                         "Valor de acciones VAEP; requiere campos que MatchEvent 1.0 no trae.",
                         ("bodypart", "tipos SPADL completos", "modelo VAEP validado"),
                         "Desactivada; ver el informe de viabilidad."),
    )
}


def definition(key: str) -> MetricDefinition:
    return METRIC_CATALOG[key]


def version(key: str) -> str:
    return METRIC_CATALOG[key].formula_version
