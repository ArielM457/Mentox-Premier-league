from dataclasses import dataclass
from random import Random

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


@dataclass(frozen=True)
class SyntheticMatch:
    metadata: MatchMetadata
    events: tuple[MatchEvent, ...]


def _position(rng: Random, x: float, y: float) -> Position:
    """Añade una variación pequeña y reproducible sin salir del campo."""
    return Position(
        x=round(min(100.0, max(0.0, x + rng.uniform(-1.5, 1.5))), 2),
        y=round(min(100.0, max(0.0, y + rng.uniform(-1.5, 1.5))), 2),
    )


def generate_acceptance_match(
    *, seed: int = 2026, match_id: str = "synthetic-acceptance-001"
) -> SyntheticMatch:
    """Genera el partido corto usado para aceptar DV-US-01.

    Incluye una fase de control del equipo local, una transición provocada por
    una recuperación y un momento decisivo que termina en gol.
    """
    rng = Random(seed)
    home_id = "team-aurora"
    away_id = "team-rio"

    metadata = MatchMetadata(
        schema_version="1.0",
        match_id=match_id,
        home_team=Team(team_id=home_id, name="Aurora FC"),
        away_team=Team(team_id=away_id, name="Río Unido"),
        pitch_length_m=105.0,
        pitch_width_m=68.0,
        players=[
            Player(
                player_id="aurora-4",
                team_id=home_id,
                name="A. Vega",
                shirt_number=4,
            ),
            Player(
                player_id="aurora-8",
                team_id=home_id,
                name="L. Sol",
                shirt_number=8,
            ),
            Player(
                player_id="aurora-9",
                team_id=home_id,
                name="M. Luz",
                shirt_number=9,
            ),
            Player(
                player_id="aurora-11",
                team_id=home_id,
                name="N. Alba",
                shirt_number=11,
            ),
            Player(
                player_id="rio-5",
                team_id=away_id,
                name="D. Sur",
                shirt_number=5,
            ),
            Player(
                player_id="rio-6",
                team_id=away_id,
                name="I. Lago",
                shirt_number=6,
            ),
            Player(
                player_id="rio-8",
                team_id=away_id,
                name="C. Valle",
                shirt_number=8,
            ),
            Player(
                player_id="rio-10",
                team_id=away_id,
                name="P. Cauce",
                shirt_number=10,
            ),
        ],
        attacking_directions=[
            PeriodDirection(period=1, team_id=home_id, direction=AttackDirection.LEFT_TO_RIGHT),
            PeriodDirection(period=1, team_id=away_id, direction=AttackDirection.RIGHT_TO_LEFT),
            PeriodDirection(period=2, team_id=home_id, direction=AttackDirection.RIGHT_TO_LEFT),
            PeriodDirection(period=2, team_id=away_id, direction=AttackDirection.LEFT_TO_RIGHT),
        ],
    )

    def event(
        number: int,
        clock_ms: int,
        event_type: EventType,
        team_id: str,
        player_id: str | None,
        outcome: EventOutcome,
        start: tuple[float, float] | None = None,
        end: tuple[float, float] | None = None,
        related: tuple[str, ...] = (),
    ) -> MatchEvent:
        return MatchEvent(
            schema_version="1.0",
            event_id=f"evt-{number:03d}",
            match_id=match_id,
            period=1,
            clock_ms=clock_ms,
            video_time_ms=clock_ms + 2_000,
            type=event_type,
            team_id=team_id,
            player_id=player_id,
            start=_position(rng, *start) if start else None,
            end=_position(rng, *end) if end else None,
            outcome=outcome,
            source=EventSource.SYNTHETIC,
            confidence=None,
            related_event_ids=list(related),
        )

    events = (
        # Control: Aurora circula el balón mientras Río presiona.
        event(
            1,
            5_000,
            EventType.PRESSURE,
            away_id,
            "rio-10",
            EventOutcome.SUCCESS,
            (38, 35),
        ),
        event(
            2,
            8_000,
            EventType.PASS,
            home_id,
            "aurora-4",
            EventOutcome.SUCCESS,
            (25, 48),
            (40, 45),
        ),
        event(
            3,
            12_000,
            EventType.PASS,
            home_id,
            "aurora-8",
            EventOutcome.SUCCESS,
            (40, 45),
            (55, 34),
            ("evt-002",),
        ),
        event(
            4,
            16_000,
            EventType.TACKLE,
            away_id,
            "rio-6",
            EventOutcome.SUCCESS,
            (56, 34),
        ),
        event(
            5,
            16_300,
            EventType.POSSESSION_CHANGE,
            away_id,
            "rio-6",
            EventOutcome.SUCCESS,
            (56, 34),
            related=("evt-004",),
        ),
        # Transición: Aurora recupera y progresa rápidamente.
        event(
            6,
            21_000,
            EventType.RECOVERY,
            home_id,
            "aurora-8",
            EventOutcome.SUCCESS,
            (48, 38),
            related=("evt-005",),
        ),
        event(
            7,
            24_000,
            EventType.PASS,
            home_id,
            "aurora-8",
            EventOutcome.SUCCESS,
            (48, 38),
            (67, 30),
            ("evt-006",),
        ),
        event(
            8,
            27_000,
            EventType.PRESSURE,
            away_id,
            "rio-5",
            EventOutcome.FAILURE,
            (68, 30),
            related=("evt-007",),
        ),
        event(
            9,
            29_000,
            EventType.PASS,
            home_id,
            "aurora-11",
            EventOutcome.SUCCESS,
            (67, 30),
            (84, 43),
            ("evt-007", "evt-008"),
        ),
        # Momento decisivo: la transición termina en gol.
        event(
            10,
            32_000,
            EventType.SHOT,
            home_id,
            "aurora-9",
            EventOutcome.GOAL,
            (86, 43),
            (100, 50),
            ("evt-006", "evt-007", "evt-009"),
        ),
    )

    return SyntheticMatch(metadata=metadata, events=events)
