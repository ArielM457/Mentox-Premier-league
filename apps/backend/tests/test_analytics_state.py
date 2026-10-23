from analytics_builders import A, B, KO, Events, metadata

from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.application.analytics.pipeline import build_snapshot
from match_intelligence.domain.analytics.state import MatchState
from match_intelligence.domain.contracts import EventOutcome, EventType


def _metric(snapshot, key, team_id=None, player_id=None):
    return next(
        m for m in snapshot.metrics
        if m.key == key and m.team_id == team_id and m.player_id == player_id
    )


def test_score_possession_and_clock_follow_the_acceptance_match() -> None:
    match = generate_acceptance_match()
    before_goal = build_snapshot(match.metadata, match.events[:9])
    after_goal = build_snapshot(match.metadata, match.events)

    assert before_goal.score == {"team-aurora": 0, "team-rio": 0}
    assert before_goal.possession_team_id == "team-aurora"
    assert before_goal.clock_ms == 29_000
    assert after_goal.score == {"team-aurora": 1, "team-rio": 0}
    assert after_goal.possession_team_id is None  # el gol deja la posesión vacía
    assert after_goal.period == 1
    assert after_goal.last_event_id == "evt-010"
    assert after_goal.recent_event_ids == ["evt-006", "evt-007", "evt-008", "evt-009", "evt-010"]


def test_possession_changes_only_when_another_team_gains_the_ball() -> None:
    events = Events()
    events.pass_(1, A, "a-1", (20, 50), (30, 50))
    events.pressure(2, B, "b-1", (70, 50))          # presión: no cambia la posesión
    events.tackle(3, B, "b-2", (68, 50), outcome=KO)  # entrada fallida: no cambia
    events.pass_(5, A, "a-2", (30, 50), (40, 50), outcome=KO)
    events.recovery(6, B, "b-3", (60, 50))           # cambio A -> B
    events.pass_(8, B, "b-3", (60, 50), (50, 50))
    events.tackle(9, A, "a-3", (50, 50))             # entrada ganada: cambio B -> A
    events.add(9.2, EventType.POSSESSION_CHANGE, A, "a-3", start=(50, 50))  # ya la tenía A

    state = MatchState.fold("test-001", (A, B), events.items)

    assert [(c.from_team_id, c.to_team_id, c.event_id) for c in state.possession_changes] == [
        (A, B, "evt-005"),
        (B, A, "evt-007"),
    ]
    assert state.possession_team_id == A


def test_possession_time_is_attributed_between_events_and_never_extrapolated() -> None:
    events = Events()
    events.pass_(10, A, "a-1", (20, 50), (30, 50))
    events.pass_(40, A, "a-2", (30, 50), (40, 50), outcome=KO)
    events.recovery(50, B, "b-1", (60, 50))
    events.pass_(60, B, "b-1", (60, 50), (50, 50))

    snapshot = build_snapshot(metadata(), events.items, video_time_ms=200_000)

    share_a = _metric(snapshot, "possession_share", A)
    share_b = _metric(snapshot, "possession_share", B)
    # A: 10 s -> 50 s = 40 s; B: 50 s -> 60 s = 10 s.
    assert share_a.value == 80.0 and share_b.value == 20.0
    assert [c.value for c in share_a.components] == [40_000, 50_000]
    assert share_a.source_event_ids == ["evt-001"]
    # El reloj del snapshot avanza con el vídeo, pero la posesión no se extrapola.
    assert snapshot.clock_ms == 60_000 + (200_000 - 61_000)


def test_new_period_clears_possession_and_does_not_join_spells() -> None:
    events = Events()
    events.pass_(10, A, "a-1", (20, 50), (30, 50))
    events.pass_(20, A, "a-2", (30, 50), (40, 50))
    events.pass_(5, B, "b-1", (40, 50), (50, 50), period=2)
    events.pass_(15, B, "b-2", (50, 50), (60, 50), period=2)

    state = MatchState.fold("test-001", (A, B), events.items)

    assert state.period == 2
    assert state.possession_changes == []  # el inicio del período no es un cambio
    assert state.possession_ms(A) == (10_000, ["evt-001"])
    assert state.possession_ms(B) == (10_000, ["evt-003"])


def test_goal_counts_once_and_keeps_its_source() -> None:
    events = Events()
    events.shot(30, A, "a-9", (90, 50), outcome=EventOutcome.GOAL)
    events.shot(60, B, "b-9", (12, 50), outcome=EventOutcome.SAVED)

    snapshot = build_snapshot(metadata(), events.items)

    assert snapshot.score == {A: 1, B: 0}
    goals = _metric(snapshot, "goals", A)
    assert goals.value == 1 and goals.source_event_ids == ["evt-001"]
    assert _metric(snapshot, "shots_on_target", B).source_event_ids == ["evt-002"]


def test_events_that_contradict_metadata_are_excluded_not_counted() -> None:
    events = Events()
    events.pass_(1, A, "a-1", (20, 50), (30, 50))
    events.pass_(2, "team-unknown", None, (30, 50), (40, 50))
    events.pass_(3, A, "b-1", (40, 50), (50, 50))  # jugador de B atribuido a A

    snapshot = build_snapshot(metadata(), events.items)

    assert snapshot.excluded_event_ids == ["evt-002", "evt-003"]
    assert snapshot.event_count == 1
    assert _metric(snapshot, "passes_attempted", A).value == 1
