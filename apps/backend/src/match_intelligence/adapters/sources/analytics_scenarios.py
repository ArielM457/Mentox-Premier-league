"""Escenario sintético de Persona 2 para probar estado, patrones y atención.

No reemplaza al generador de Persona 1: es un guion determinista con fases
pensadas para tener ejemplos positivos y negativos de cada regla. Todos los
equipos, jugadores y eventos son inventados.

Período 1 (Aurora ataca de izquierda a derecha):

* 0-145 s, control de Aurora: elaboraciones lentas, un cambio de orientación
  de más de 40 m y dos tiros. Ninguna progresión rápida.
* 148-328 s, presión alta de Río: cinco acciones defensivas y dos balones
  ganados en campo rival en 90 s, una recuperación seguida de tiro y una larga
  posesión de Río que le da el control.
* 332-452 s, caos: pérdidas y recuperaciones cada pocos segundos y tiros de
  ambos equipos.
* 456-500 s, gol de Aurora tras recuperar y progresar 33 de x' en 8 s.

Período 2 (las direcciones se invierten): empate de Río tras una elaboración
lenta y la respuesta de Aurora.
"""

from random import Random

from match_intelligence.adapters.sources.synthetic import SyntheticMatch
from match_intelligence.domain.contracts import (
    AttackDirection,
    EventOutcome,
    EventSource,
    EventType,
    MatchEvent,
    MatchMetadata,
    PeriodDirection,
    Player,
    Position,
    Team,
)

HOME = "team-aurora"
AWAY = "team-rio"
VIDEO_OFFSET_MS = 3_000
SECOND_PERIOD_VIDEO_START_MS = 600_000

P, S, R, T, PC, PR = (
    EventType.PASS,
    EventType.SHOT,
    EventType.RECOVERY,
    EventType.TACKLE,
    EventType.POSSESSION_CHANGE,
    EventType.PRESSURE,
)
OK, KO = EventOutcome.SUCCESS, EventOutcome.FAILURE

_PLAYERS = (
    ("aurora-1", HOME, "S. Roca", 1),
    ("aurora-4", HOME, "A. Vega", 4),
    ("aurora-5", HOME, "R. Brisa", 5),
    ("aurora-8", HOME, "L. Sol", 8),
    ("aurora-10", HOME, "T. Cumbre", 10),
    ("aurora-11", HOME, "N. Alba", 11),
    ("aurora-9", HOME, "M. Luz", 9),
    ("rio-1", AWAY, "G. Fondo", 1),
    ("rio-5", AWAY, "D. Sur", 5),
    ("rio-6", AWAY, "I. Lago", 6),
    ("rio-8", AWAY, "C. Valle", 8),
    ("rio-10", AWAY, "P. Cauce", 10),
    ("rio-7", AWAY, "F. Ribera", 7),
    ("rio-9", AWAY, "J. Delta", 9),
)

Point = tuple[float, float]
# (segundos, tipo, equipo, jugador, resultado, inicio, fin) en el marco de ataque del equipo.
Row = tuple[float, EventType, str, str, EventOutcome, Point | None, Point | None]


def _first_half_script() -> list[Row]:
    rows: list[Row] = [
        # Control de Aurora: cadena lenta con pases hacia atrás y laterales.
        (4.0, P, HOME, "aurora-4", OK, (20, 50), (30, 40)),
        (10.0, P, HOME, "aurora-8", OK, (30, 40), (28, 60)),
        (16.0, P, HOME, "aurora-5", OK, (28, 60), (42, 62)),
        (22.0, P, HOME, "aurora-10", OK, (42, 62), (55, 50)),
        (25.0, PR, AWAY, "rio-6", KO, (43, 50), None),
        (28.0, P, HOME, "aurora-8", OK, (55, 50), (63, 35)),
        (34.0, P, HOME, "aurora-11", OK, (63, 35), (72, 25)),
        (39.0, P, HOME, "aurora-10", OK, (72, 25), (80, 45)),
        (43.0, S, HOME, "aurora-9", EventOutcome.SAVED, (83, 48), (100, 50)),
        (49.0, P, AWAY, "rio-1", OK, (8, 50), (28, 40)),
        (53.0, P, AWAY, "rio-5", KO, (28, 40), (48, 55)),
        (55.0, R, HOME, "aurora-8", OK, (52, 45), None),
        (58.0, P, HOME, "aurora-8", OK, (52, 45), (45, 30)),
        (62.0, P, HOME, "aurora-4", OK, (45, 30), (38, 18)),
        (66.0, P, HOME, "aurora-4", OK, (38, 18), (50, 12)),
        (71.0, PR, AWAY, "rio-10", KO, (48, 15), None),
        (74.0, P, HOME, "aurora-10", OK, (50, 12), (48, 30)),
        (78.0, P, HOME, "aurora-4", OK, (48, 30), (35, 15)),
        # Cambio de orientación de casi 60 m: récord de pase del partido.
        (84.0, P, HOME, "aurora-4", OK, (35, 15), (70, 82)),
        (89.0, P, HOME, "aurora-11", OK, (70, 82), (78, 70)),
        (93.0, PR, AWAY, "rio-6", KO, (20, 30), None),
        (95.0, P, HOME, "aurora-11", KO, (78, 70), (88, 55)),
        (97.0, R, AWAY, "rio-5", OK, (12, 45), None),
        (100.0, P, AWAY, "rio-5", OK, (12, 45), (30, 60)),
        (104.0, P, AWAY, "rio-8", OK, (30, 60), (40, 50)),
        (107.0, T, HOME, "aurora-10", OK, (60, 50), None),
        (107.3, PC, HOME, "aurora-10", OK, (60, 50), None),
        (111.0, P, HOME, "aurora-10", OK, (60, 50), (64, 62)),
        (115.0, P, HOME, "aurora-8", OK, (64, 62), (58, 45)),
        (119.0, P, HOME, "aurora-5", OK, (58, 45), (66, 30)),
        (123.0, PR, AWAY, "rio-8", KO, (34, 70), None),
        (126.0, P, HOME, "aurora-8", OK, (66, 30), (74, 40)),
        (131.0, P, HOME, "aurora-10", OK, (74, 40), (70, 60)),
        (136.0, P, HOME, "aurora-11", OK, (70, 60), (80, 66)),
        (141.0, P, HOME, "aurora-8", OK, (80, 66), (84, 50)),
        (145.0, S, HOME, "aurora-9", EventOutcome.BLOCKED, (86, 50), (90, 50)),
        # Presión alta de Río en campo de Aurora.
        (148.0, R, AWAY, "rio-6", OK, (14, 50), None),
        (151.0, P, AWAY, "rio-6", OK, (14, 50), (35, 40)),
        (155.0, P, AWAY, "rio-10", KO, (35, 40), (55, 30)),
        (157.0, R, HOME, "aurora-5", OK, (45, 70), None),
        (160.0, P, HOME, "aurora-5", OK, (45, 70), (15, 45)),
        (164.0, P, HOME, "aurora-1", OK, (12, 45), (18, 25)),
        (166.0, PR, AWAY, "rio-9", OK, (82, 75), None),
        (168.0, P, HOME, "aurora-4", OK, (18, 25), (25, 40)),
        (170.0, PR, AWAY, "rio-10", OK, (75, 60), None),
        (172.0, P, HOME, "aurora-5", KO, (25, 40), (35, 55)),
        (173.0, R, AWAY, "rio-8", OK, (65, 45), None),
        (175.0, P, AWAY, "rio-8", OK, (65, 45), (76, 48)),
        (178.0, S, AWAY, "rio-9", EventOutcome.OFF_TARGET, (82, 45), (100, 62)),
        (185.0, P, HOME, "aurora-1", OK, (6, 50), (16, 70)),
        (187.0, PR, AWAY, "rio-7", OK, (84, 30), None),
        (189.0, P, HOME, "aurora-4", OK, (16, 70), (26, 62)),
        (190.0, T, AWAY, "rio-6", OK, (74, 38), None),
        (190.3, PC, AWAY, "rio-6", OK, (74, 38), None),
        (193.0, P, AWAY, "rio-6", OK, (74, 38), (82, 50)),
        (196.0, P, AWAY, "rio-10", OK, (82, 50), (78, 30)),
        (200.0, PR, HOME, "aurora-5", KO, (22, 70), None),
        (202.0, P, AWAY, "rio-7", OK, (78, 30), (86, 40)),
        (205.0, S, AWAY, "rio-9", EventOutcome.SAVED, (88, 48), (100, 50)),
        (210.0, P, HOME, "aurora-1", OK, (6, 50), (20, 20)),
        (212.0, PR, AWAY, "rio-9", KO, (80, 80), None),
        (214.0, P, HOME, "aurora-4", KO, (20, 20), (35, 30)),
        (216.0, R, AWAY, "rio-8", OK, (66, 70), None),
        # Larga posesión de Río: el control cambia de equipo.
        (219.0, P, AWAY, "rio-8", OK, (66, 70), (60, 50)),
        (224.0, P, AWAY, "rio-5", OK, (60, 50), (58, 30)),
        (229.0, P, AWAY, "rio-6", OK, (58, 30), (70, 25)),
        (234.0, PR, HOME, "aurora-11", KO, (32, 75), None),
        (236.0, P, AWAY, "rio-7", OK, (70, 25), (78, 40)),
        (241.0, P, AWAY, "rio-10", OK, (78, 40), (72, 55)),
        (246.0, P, AWAY, "rio-8", OK, (72, 55), (80, 65)),
        (251.0, P, AWAY, "rio-6", OK, (80, 65), (75, 45)),
        (256.0, P, AWAY, "rio-10", OK, (75, 45), (84, 40)),
        (261.0, PR, HOME, "aurora-8", KO, (18, 60), None),
        (263.0, P, AWAY, "rio-7", OK, (84, 40), (88, 55)),
        (268.0, S, AWAY, "rio-9", EventOutcome.BLOCKED, (89, 50), (92, 50)),
        (271.0, R, AWAY, "rio-5", OK, (85, 60), None),
        (274.0, P, AWAY, "rio-5", OK, (85, 60), (78, 75)),
        (279.0, P, AWAY, "rio-8", OK, (78, 75), (70, 60)),
        (284.0, P, AWAY, "rio-6", OK, (70, 60), (80, 45)),
        (289.0, P, AWAY, "rio-10", OK, (80, 45), (86, 52)),
        (293.0, S, AWAY, "rio-7", EventOutcome.SAVED, (87, 54), (100, 50)),
        (299.0, P, HOME, "aurora-1", KO, (6, 50), (40, 50)),
        (301.0, R, AWAY, "rio-5", OK, (58, 50), None),
        (304.0, P, AWAY, "rio-5", OK, (58, 50), (68, 65)),
        (309.0, P, AWAY, "rio-8", OK, (68, 65), (76, 50)),
        (314.0, P, AWAY, "rio-10", OK, (76, 50), (70, 30)),
        (319.0, P, AWAY, "rio-6", OK, (70, 30), (80, 38)),
        (324.0, PR, HOME, "aurora-4", KO, (22, 62), None),
        (326.0, P, AWAY, "rio-7", KO, (80, 38), (90, 50)),
        (328.0, R, HOME, "aurora-4", OK, (10, 50), None),
    ]
    rows.extend(_chaos_rows(start_s=332.0, cycles=10))
    rows.extend([
        # Gol de Aurora: recuperación y progresión rápida.
        (456.0, P, AWAY, "rio-5", OK, (40, 50), (45, 70)),
        (459.0, P, AWAY, "rio-8", KO, (45, 70), (52, 60)),
        (461.0, R, HOME, "aurora-10", OK, (54, 40), None),
        (463.0, P, HOME, "aurora-10", OK, (54, 40), (66, 55)),
        (466.0, P, HOME, "aurora-8", OK, (66, 55), (80, 48)),
        (468.0, PR, AWAY, "rio-5", KO, (18, 52), None),
        (469.0, P, HOME, "aurora-11", OK, (80, 48), (87, 52)),
        (471.0, S, HOME, "aurora-9", EventOutcome.GOAL, (88, 53), (100, 50)),
        (480.0, P, AWAY, "rio-10", OK, (50, 50), (40, 40)),
        (484.0, P, AWAY, "rio-8", OK, (40, 40), (55, 40)),
        (488.0, PR, HOME, "aurora-10", KO, (45, 60), None),
        (490.0, P, AWAY, "rio-6", KO, (55, 40), (70, 50)),
        (492.0, R, HOME, "aurora-4", OK, (30, 50), None),
        (495.0, P, HOME, "aurora-4", OK, (30, 50), (42, 60)),
        (500.0, P, HOME, "aurora-8", OK, (42, 60), (50, 40)),
    ])
    return rows


def _chaos_rows(*, start_s: float, cycles: int) -> list[Row]:
    """Ciclos de 12 s con dos pérdidas, dos recuperaciones y algún tiro."""
    home_players = ("aurora-4", "aurora-5", "aurora-10", "aurora-11")
    away_players = ("rio-5", "rio-6", "rio-8", "rio-10")
    rows: list[Row] = []
    for index in range(cycles):
        t = start_s + 12 * index
        home = home_players[index % len(home_players)]
        away = away_players[index % len(away_players)]
        y = 25 + (index * 13) % 50
        rows.append((t, P, HOME, home, OK, (45, y), (52, y + 5)))
        rows.append((t + 3, P, HOME, home_players[(index + 1) % 4], KO, (52, y + 5), (60, y)))
        rows.append((t + 5, R, AWAY, away, OK, (40, 100 - y), None))
        if index in {2, 7}:
            outcome = EventOutcome.OFF_TARGET if index == 2 else EventOutcome.SAVED
            rows.append((t + 7, S, AWAY, "rio-9", outcome, (72, 50), (100, 50)))
            rows.append((t + 10, R, HOME, "aurora-1", OK, (5, 50), None))
            continue
        rows.append((t + 8, P, AWAY, away_players[(index + 1) % 4], KO, (40, 100 - y), (55, 100 - y)))
        if index == 5:
            rows.append((t + 10, R, HOME, home, OK, (45, y), None))
            rows.append((t + 11, S, HOME, "aurora-9", EventOutcome.BLOCKED, (75, 45), (80, 45)))
            continue
        rows.append((t + 10, R, HOME, home, OK, (45, y), None))
    return rows


def _second_half_script() -> list[Row]:
    return [
        # Empate de Río tras una elaboración lenta (no es progresión rápida).
        (3.0, P, AWAY, "rio-10", OK, (50, 50), (42, 45)),
        (7.0, P, AWAY, "rio-6", OK, (42, 45), (30, 60)),
        (12.0, P, AWAY, "rio-5", OK, (30, 60), (40, 75)),
        (17.0, PR, HOME, "aurora-9", KO, (62, 30), None),
        (19.0, P, AWAY, "rio-8", OK, (40, 75), (52, 65)),
        (25.0, P, AWAY, "rio-10", OK, (52, 65), (60, 50)),
        (31.0, P, AWAY, "rio-7", OK, (60, 50), (70, 35)),
        (36.0, P, AWAY, "rio-8", OK, (70, 35), (78, 50)),
        (40.0, P, AWAY, "rio-7", OK, (78, 50), (85, 45)),
        (43.0, S, AWAY, "rio-9", EventOutcome.GOAL, (87, 52), (100, 50)),
        (48.0, P, HOME, "aurora-10", OK, (50, 50), (45, 40)),
        (52.0, P, HOME, "aurora-8", OK, (45, 40), (60, 30)),
        (56.0, P, HOME, "aurora-11", OK, (60, 30), (72, 20)),
        (60.0, PR, AWAY, "rio-5", KO, (25, 80), None),
        (61.0, P, HOME, "aurora-11", KO, (72, 20), (85, 40)),
        (63.0, R, AWAY, "rio-1", OK, (12, 60), None),
        (66.0, P, AWAY, "rio-1", OK, (12, 60), (35, 40)),
        (70.0, P, AWAY, "rio-6", OK, (35, 40), (48, 55)),
        (74.0, T, HOME, "aurora-8", OK, (52, 45), None),
        (76.0, P, HOME, "aurora-8", OK, (52, 45), (66, 52)),
        (79.0, P, HOME, "aurora-10", OK, (66, 52), (76, 60)),
        (82.0, S, HOME, "aurora-9", EventOutcome.OFF_TARGET, (80, 55), (100, 70)),
    ]


def _metadata(match_id: str) -> MatchMetadata:
    return MatchMetadata(
        schema_version="1.0",
        match_id=match_id,
        home_team=Team(team_id=HOME, name="Aurora FC"),
        away_team=Team(team_id=AWAY, name="Río Unido"),
        pitch_length_m=105.0,
        pitch_width_m=68.0,
        players=[
            Player(player_id=pid, team_id=team, name=name, shirt_number=number)
            for pid, team, name, number in _PLAYERS
        ],
        attacking_directions=[
            PeriodDirection(period=1, team_id=HOME, direction=AttackDirection.LEFT_TO_RIGHT),
            PeriodDirection(period=1, team_id=AWAY, direction=AttackDirection.RIGHT_TO_LEFT),
            PeriodDirection(period=2, team_id=HOME, direction=AttackDirection.RIGHT_TO_LEFT),
            PeriodDirection(period=2, team_id=AWAY, direction=AttackDirection.LEFT_TO_RIGHT),
        ],
    )


def generate_analytics_scenario(
    *, seed: int = 7, match_id: str = "synthetic-analytics-001"
) -> SyntheticMatch:
    """Partido determinista: la misma semilla produce los mismos eventos."""
    rng = Random(seed)
    metadata = _metadata(match_id)
    directions = {(d.period, d.team_id): d.direction for d in metadata.attacking_directions}

    def fixed(team: str, period: int, point: Point | None) -> Position | None:
        if point is None:
            return None
        x, y = point
        if directions[(period, team)] is AttackDirection.RIGHT_TO_LEFT:
            x = 100 - x
        jitter_x, jitter_y = rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.8)
        return Position(
            x=round(min(100.0, max(0.0, x + jitter_x)), 2),
            y=round(min(100.0, max(0.0, y + jitter_y)), 2),
        )

    events: list[MatchEvent] = []
    for period, rows, video_start in (
        (1, _first_half_script(), VIDEO_OFFSET_MS),
        (2, _second_half_script(), SECOND_PERIOD_VIDEO_START_MS),
    ):
        for seconds, event_type, team, player, outcome, start, end in sorted(rows, key=lambda r: r[0]):
            clock_ms = int(round(seconds * 1000))
            events.append(
                MatchEvent(
                    schema_version="1.0",
                    event_id=f"sc-{len(events) + 1:03d}",
                    match_id=match_id,
                    period=period,
                    clock_ms=clock_ms,
                    video_time_ms=video_start + clock_ms,
                    type=event_type,
                    team_id=team,
                    player_id=player,
                    start=fixed(team, period, start),
                    end=fixed(team, period, end),
                    outcome=outcome,
                    source=EventSource.SYNTHETIC,
                    confidence=None,
                    related_event_ids=[],
                )
            )
    return SyntheticMatch(metadata=metadata, events=tuple(events))
