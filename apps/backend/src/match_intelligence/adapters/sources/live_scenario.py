"""Partido en vivo con jugadas coherentes y situaciones de balón detenido.

El escenario sigue siendo sintético. A diferencia del guion analítico general,
cada pase identifica a su receptor y su intención. Esto permite que el motor de
seguimiento coordine al pasador, al receptor, al balón y al bloque defensivo.
"""

from dataclasses import dataclass
from math import hypot

from match_intelligence.adapters.sources.analytics_scenarios import generate_analytics_scenario
from match_intelligence.adapters.sources.synthetic import SyntheticMatch
from match_intelligence.domain.contracts import (
    EventOutcome,
    EventSource,
    EventType,
    MatchEvent,
    Position,
)

HOME = "team-aurora"
AWAY = "team-rio"
VIDEO_OFFSET_MS = 3_000


@dataclass(frozen=True, slots=True)
class Situation:
    second: float
    kind: EventType
    team: str
    actor: str
    outcome: EventOutcome
    start: tuple[float, float]
    end: tuple[float, float] | None = None
    receiver: str | None = None
    situation: str | None = None
    stoppage_ms: int = 0
    related: tuple[str, ...] = ()


def _script() -> tuple[Situation, ...]:
    """Secuencias cortas revisables: salida, cambio de orientación y transiciones."""
    return (
        Situation(4, EventType.PASS, HOME, "aurora-1", EventOutcome.SUCCESS,
                  (7, 50), (18, 38), "aurora-3", "build_up"),
        Situation(9, EventType.PASS, HOME, "aurora-3", EventOutcome.SUCCESS,
                  (18, 38), (37, 46), "aurora-6", "line_break"),
        Situation(14, EventType.PASS, HOME, "aurora-6", EventOutcome.SUCCESS,
                  (37, 46), (61, 18), "aurora-7", "long_switch"),
        Situation(20, EventType.PASS, HOME, "aurora-7", EventOutcome.SUCCESS,
                  (61, 18), (72, 39), "aurora-10", "inside_support"),
        Situation(25, EventType.PASS, HOME, "aurora-10", EventOutcome.SUCCESS,
                  (72, 39), (84, 50), "aurora-9", "through_ball"),
        Situation(29, EventType.SHOT, HOME, "aurora-9", EventOutcome.SAVED,
                  (84, 50), (100, 50), situation="shot"),

        Situation(36, EventType.PASS, AWAY, "rio-1", EventOutcome.SUCCESS,
                  (94, 50), (82, 62), "rio-4", "build_up"),
        Situation(42, EventType.PASS, AWAY, "rio-4", EventOutcome.SUCCESS,
                  (82, 62), (64, 55), "rio-8", "line_break"),
        Situation(48, EventType.PASS, AWAY, "rio-8", EventOutcome.SUCCESS,
                  (64, 55), (41, 80), "rio-11", "long_switch"),
        Situation(54, EventType.PASS, AWAY, "rio-11", EventOutcome.FAILURE,
                  (41, 80), (29, 64), "rio-10", "intercepted_pass"),
        Situation(55, EventType.RECOVERY, HOME, "aurora-5", EventOutcome.SUCCESS,
                  (29, 64), situation="interception", related=("live-010",)),
        Situation(59, EventType.PASS, HOME, "aurora-5", EventOutcome.SUCCESS,
                  (29, 64), (46, 51), "aurora-8", "safe_outlet", related=("live-011",)),
        Situation(64, EventType.PASS, HOME, "aurora-8", EventOutcome.SUCCESS,
                  (46, 51), (76, 19), "aurora-7", "long_switch", related=("live-011", "live-012")),
        Situation(70, EventType.PASS, HOME, "aurora-7", EventOutcome.SUCCESS,
                  (76, 19), (86, 47), "aurora-9", "cutback", related=("live-011", "live-012", "live-013")),
        Situation(74, EventType.SHOT, HOME, "aurora-9", EventOutcome.GOAL,
                  (86, 47), (100, 50), situation="goal_after_recovery",
                  related=("live-011", "live-012", "live-013", "live-014")),

        Situation(88, EventType.PASS, AWAY, "rio-6", EventOutcome.SUCCESS,
                  (62, 52), (49, 48), "rio-10", "support_under_pressure"),
        Situation(93, EventType.FOUL, HOME, "aurora-6", EventOutcome.SUCCESS,
                  (48, 48), situation="tactical_foul", stoppage_ms=14_000),
        Situation(93.2, EventType.YELLOW_CARD, HOME, "aurora-6", EventOutcome.SUCCESS,
                  (48, 48), situation="yellow_card", related=("live-017",)),
        Situation(94, EventType.INJURY_STOPPAGE, AWAY, "rio-10", EventOutcome.UNKNOWN,
                  (48, 48), situation="injury_treatment", stoppage_ms=13_000,
                  related=("live-017", "live-018")),
        Situation(108, EventType.RESTART, AWAY, "rio-8", EventOutcome.SUCCESS,
                  (48, 48), (33, 25), "rio-7", "free_kick_restart",
                  related=("live-017", "live-018", "live-019")),
        Situation(114, EventType.PASS, AWAY, "rio-7", EventOutcome.SUCCESS,
                  (33, 25), (20, 43), "rio-9", "through_ball"),
        Situation(119, EventType.SHOT, AWAY, "rio-9", EventOutcome.BLOCKED,
                  (20, 43), (7, 50), situation="blocked_shot"),
        Situation(120, EventType.RECOVERY, HOME, "aurora-3", EventOutcome.SUCCESS,
                  (18, 43), situation="second_ball", related=("live-022",)),

        Situation(126, EventType.PASS, HOME, "aurora-3", EventOutcome.SUCCESS,
                  (18, 43), (35, 31), "aurora-6", "safe_outlet", related=("live-023",)),
        Situation(132, EventType.PASS, HOME, "aurora-6", EventOutcome.SUCCESS,
                  (35, 31), (67, 79), "aurora-11", "long_switch"),
        Situation(139, EventType.PASS, HOME, "aurora-11", EventOutcome.SUCCESS,
                  (67, 79), (79, 61), "aurora-10", "inside_support"),
        Situation(144, EventType.PRESSURE, AWAY, "rio-5", EventOutcome.SUCCESS,
                  (79, 61), situation="high_pressure"),
        Situation(146, EventType.TACKLE, AWAY, "rio-5", EventOutcome.SUCCESS,
                  (78, 60), situation="tackle_won", related=("live-027",)),
        Situation(146.2, EventType.POSSESSION_CHANGE, AWAY, "rio-5", EventOutcome.SUCCESS,
                  (78, 60), situation="turnover", related=("live-027", "live-028")),
        Situation(151, EventType.PASS, AWAY, "rio-5", EventOutcome.SUCCESS,
                  (78, 60), (53, 43), "rio-8", "counter_attack", related=("live-028", "live-029")),
        Situation(157, EventType.PASS, AWAY, "rio-8", EventOutcome.SUCCESS,
                  (53, 43), (24, 50), "rio-9", "through_ball", related=("live-028", "live-029", "live-030")),
        Situation(162, EventType.SHOT, AWAY, "rio-9", EventOutcome.SAVED,
                  (24, 50), (0, 50), situation="shot"),
    )


def _validate_script(rows: tuple[Situation, ...]) -> None:
    """Impide pases sin receptor o retrocesos sin una razón táctica declarada."""
    justified_backwards = {"cutback", "safe_outlet", "support_under_pressure"}
    for row in rows:
        if row.kind not in {EventType.PASS, EventType.RESTART}:
            continue
        if row.receiver is None or row.end is None or row.receiver == row.actor:
            raise ValueError(f"Pase inválido de {row.actor}: falta un receptor distinto")
        progress = row.end[0] - row.start[0]
        if row.team == AWAY:
            progress *= -1
        if progress < -8 and row.situation not in justified_backwards:
            raise ValueError(f"Pase hacia atrás sin propósito táctico: {row.actor}")
        length = hypot(row.end[0] - row.start[0], row.end[1] - row.start[1])
        if row.situation == "long_switch" and length < 25:
            raise ValueError(f"Cambio de orientación demasiado corto: {row.actor}")
        if row.situation == "through_ball" and progress < 10:
            raise ValueError(f"Pase al espacio sin progresión: {row.actor}")


def generate_live_scenario(*, seed: int = 19, match_id: str = "synthetic-live-001") -> SyntheticMatch:
    base = generate_analytics_scenario(seed=seed, match_id=match_id)
    rows = _script()
    _validate_script(rows)
    events = []
    for number, row in enumerate(rows, start=1):
        clock_ms = round(row.second * 1_000)
        events.append(MatchEvent(
            schema_version="1.0",
            event_id=f"live-{number:03d}",
            match_id=match_id,
            period=1,
            clock_ms=clock_ms,
            video_time_ms=clock_ms + VIDEO_OFFSET_MS,
            type=row.kind,
            team_id=row.team,
            player_id=row.actor,
            receiver_player_id=row.receiver,
            start=Position(x=row.start[0], y=row.start[1]),
            end=Position(x=row.end[0], y=row.end[1]) if row.end else None,
            outcome=row.outcome,
            source=EventSource.SYNTHETIC,
            confidence=1.0,
            situation=row.situation,
            stoppage_ms=row.stoppage_ms,
            related_event_ids=list(row.related),
        ))
    return SyntheticMatch(metadata=base.metadata, events=tuple(events))
