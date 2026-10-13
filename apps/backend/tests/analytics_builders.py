"""Constructores de partidos mínimos para las pruebas de analítica.

``team-a`` ataca de izquierda a derecha en el período 1 y ``team-b`` al revés;
en el período 2 se invierten. Las posiciones de los eventos son fijas, como en
``MatchEvent 1.0``.
"""

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

A = "team-a"
B = "team-b"
MATCH_ID = "test-001"
OK = EventOutcome.SUCCESS
KO = EventOutcome.FAILURE


def metadata(*, match_id: str = MATCH_ID, with_directions: bool = True) -> MatchMetadata:
    directions = [
        PeriodDirection(period=1, team_id=A, direction=AttackDirection.LEFT_TO_RIGHT),
        PeriodDirection(period=1, team_id=B, direction=AttackDirection.RIGHT_TO_LEFT),
        PeriodDirection(period=2, team_id=A, direction=AttackDirection.RIGHT_TO_LEFT),
        PeriodDirection(period=2, team_id=B, direction=AttackDirection.LEFT_TO_RIGHT),
    ]
    return MatchMetadata(
        schema_version="1.0",
        match_id=match_id,
        home_team=Team(team_id=A, name="Equipo A"),
        away_team=Team(team_id=B, name="Equipo B"),
        pitch_length_m=100.0,
        pitch_width_m=50.0,
        players=[
            Player(player_id=f"a-{n}", team_id=A, name=f"Jugador A{n}", shirt_number=n) for n in range(1, 8)
        ] + [
            Player(player_id=f"b-{n}", team_id=B, name=f"Jugador B{n}", shirt_number=n) for n in range(1, 8)
        ],
        attacking_directions=directions if with_directions else [],
    )


class Events:
    """Fábrica secuencial de eventos ``evt-001``, ``evt-002``…"""

    def __init__(self, *, match_id: str = MATCH_ID, video_offset_ms: int = 1_000) -> None:
        self.match_id = match_id
        self.video_offset_ms = video_offset_ms
        self.items: list[MatchEvent] = []

    def add(
        self,
        seconds: float,
        event_type: EventType,
        team_id: str,
        player_id: str | None = None,
        outcome: EventOutcome = OK,
        start: tuple[float, float] | None = None,
        end: tuple[float, float] | None = None,
        *,
        period: int = 1,
        event_id: str | None = None,
    ) -> MatchEvent:
        clock_ms = int(round(seconds * 1000))
        event = MatchEvent(
            schema_version="1.0",
            event_id=event_id or f"evt-{len(self.items) + 1:03d}",
            match_id=self.match_id,
            period=period,
            clock_ms=clock_ms,
            video_time_ms=clock_ms + self.video_offset_ms + (600_000 if period == 2 else 0),
            type=event_type,
            team_id=team_id,
            player_id=player_id,
            start=Position(x=start[0], y=start[1]) if start else None,
            end=Position(x=end[0], y=end[1]) if end else None,
            outcome=outcome,
            source=EventSource.SYNTHETIC,
        )
        self.items.append(event)
        return event

    def pass_(self, seconds: float, team_id: str, player_id: str, start, end, outcome=OK, **kw) -> MatchEvent:
        return self.add(seconds, EventType.PASS, team_id, player_id, outcome, start, end, **kw)

    def shot(self, seconds: float, team_id: str, player_id: str, start, outcome=EventOutcome.SAVED, **kw) -> MatchEvent:
        goal_x = 100.0 if (team_id == A) == (kw.get("period", 1) == 1) else 0.0
        return self.add(seconds, EventType.SHOT, team_id, player_id, outcome, start, (goal_x, 50.0), **kw)

    def recovery(self, seconds: float, team_id: str, player_id: str, start=None, **kw) -> MatchEvent:
        return self.add(seconds, EventType.RECOVERY, team_id, player_id, OK, start, **kw)

    def pressure(self, seconds: float, team_id: str, player_id: str, start=None, outcome=KO, **kw) -> MatchEvent:
        return self.add(seconds, EventType.PRESSURE, team_id, player_id, outcome, start, **kw)

    def tackle(self, seconds: float, team_id: str, player_id: str, start=None, outcome=OK, **kw) -> MatchEvent:
        return self.add(seconds, EventType.TACKLE, team_id, player_id, outcome, start, **kw)
