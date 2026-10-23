"""Ejemplos positivos y negativos de cada regla (RF-09, RF-29, RF-30 a RF-33)."""

from analytics_builders import A, B, KO, Events, metadata

from match_intelligence.adapters.sources.analytics_scenarios import generate_analytics_scenario
from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.application.analytics.pipeline import MatchAnalyzer
from match_intelligence.domain.analytics.sequences import SequenceOutcome
from match_intelligence.domain.contracts import EventOutcome


def _analyze(events, meta=None) -> MatchAnalyzer:
    analyzer = MatchAnalyzer(meta or metadata())
    analyzer.extend(events)
    return analyzer


def _kinds(analyzer: MatchAnalyzer, kind: str):
    return [signal for signal in analyzer.signals if signal.kind == kind]


# --- Jugadas (RF-29) ---------------------------------------------------------

def test_acceptance_match_groups_recovery_passes_and_goal_into_one_sequence() -> None:
    match = generate_acceptance_match()
    sequences = _analyze(match.events, match.metadata).sequences

    assert [(s.sequence_id, s.team_id, s.started_by, s.outcome) for s in sequences] == [
        ("seq-evt-002", "team-aurora", "pass", SequenceOutcome.LOST),
        ("seq-evt-004", "team-rio", "tackle", SequenceOutcome.LOST),
        ("seq-evt-006", "team-aurora", "recovery", SequenceOutcome.GOAL),
    ]
    decisive = sequences[-1]
    assert decisive.event_ids == ("evt-006", "evt-007", "evt-009", "evt-010")
    assert decisive.context_event_ids == ("evt-008",)  # presión rival como contexto
    assert decisive.player_ids == ("aurora-8", "aurora-11", "aurora-9")
    assert decisive.duration_ms == 11_000


def test_long_pause_and_new_period_close_a_sequence() -> None:
    events = Events()
    events.pass_(1, A, "a-1", (20, 50), (30, 50))
    events.pass_(30, A, "a-2", (30, 50), (40, 50))       # 29 s después: otra jugada
    events.pass_(5, A, "a-2", (60, 50), (50, 50), period=2)

    sequences = _analyze(events.items).sequences

    assert [s.outcome for s in sequences] == [
        SequenceOutcome.STOPPED, SequenceOutcome.PERIOD_END, SequenceOutcome.ONGOING,
    ]


# --- Tiro y gol ----------------------------------------------------------------

def test_goal_moment_cites_the_whole_sequence_and_resulting_score() -> None:
    match = generate_acceptance_match()
    analyzer = _analyze(match.events, match.metadata)
    goal = _kinds(analyzer, "goal")[0]

    assert goal.source_event_ids == ("evt-006", "evt-007", "evt-008", "evt-009", "evt-010")
    facts = {(f.key, f.team_id): f.value for f in goal.facts}
    assert facts[("goals", "team-aurora")] == 1 and facts[("goals", "team-rio")] == 0
    assert facts[("sequence_passes", "team-aurora")] == 2
    assert facts[("shot_distance_m", "team-aurora")] > 0


# --- Progresión rápida ----------------------------------------------------------

def test_fast_progression_positive_is_emitted_once_when_threshold_is_crossed() -> None:
    events = Events()
    events.recovery(10, A, "a-1", (40, 50))
    events.pass_(13, A, "a-1", (40, 50), (55, 50))
    events.pass_(16, A, "a-2", (55, 50), (72, 40))   # +32 en 6 s y llega al último tercio
    events.pass_(18, A, "a-3", (72, 40), (80, 45))   # sigue la misma jugada: no repite

    signals = _kinds(_analyze(events.items), "fast_progression")

    assert [s.anchor_event_id for s in signals] == ["evt-003"]
    facts = {f.key: f.value for f in signals[0].facts}
    assert facts["forward_progress"] == 32.0 and facts["sequence_duration_s"] == 6.0


def test_fast_progression_negative_slow_or_short() -> None:
    slow = Events()
    slow.pass_(10, A, "a-1", (40, 50), (50, 50))
    slow.pass_(20, A, "a-1", (50, 50), (60, 50))
    slow.pass_(28, A, "a-2", (60, 50), (75, 50))     # +35, pero en 18 s
    short = Events()
    short.pass_(10, A, "a-1", (50, 50), (60, 50))
    short.pass_(12, A, "a-1", (60, 50), (70, 50))    # último tercio, pero solo +20

    assert _kinds(_analyze(slow.items), "fast_progression") == []
    assert _kinds(_analyze(short.items), "fast_progression") == []


def test_fast_progression_without_positions_is_noted_not_emitted() -> None:
    events = Events()
    events.recovery(10, A, "a-1")
    events.pass_(12, A, "a-1", None, None)
    events.pass_(14, A, "a-2", None, None)

    analyzer = _analyze(events.items)

    assert _kinds(analyzer, "fast_progression") == []
    assert [(n.rule, n.reason) for n in analyzer.notes] == [
        ("fast_progression@1", "La jugada no tiene posiciones"),
    ]


def test_right_to_left_team_uses_normalized_coordinates() -> None:
    events = Events()
    events.recovery(10, B, "b-1", (60, 50))          # x' = 40
    events.pass_(12, B, "b-1", (60, 50), (45, 50))   # x' = 55
    events.pass_(15, B, "b-2", (45, 50), (25, 50))   # x' = 75: +35 en 5 s

    assert [s.team_id for s in _kinds(_analyze(events.items), "fast_progression")] == [B]


# --- Recuperación y tiro --------------------------------------------------------

def test_recovery_to_shot_positive_and_negative() -> None:
    quick = Events()
    quick.recovery(10, A, "a-1", (55, 50))
    quick.pass_(13, A, "a-1", (55, 50), (75, 50))
    quick.shot(18, A, "a-9", (82, 50))
    slow = Events()
    slow.recovery(10, A, "a-1", (55, 50))
    slow.pass_(15, A, "a-1", (55, 50), (60, 50))
    slow.pass_(22, A, "a-2", (60, 50), (75, 50))
    slow.shot(27, A, "a-9", (82, 50))                # 17 s después
    build_up = Events()
    build_up.pass_(10, A, "a-1", (55, 50), (75, 50))
    build_up.shot(12, A, "a-9", (82, 50))            # la jugada no empezó ganando el balón

    positive = _kinds(_analyze(quick.items), "recovery_to_shot")
    assert len(positive) == 1
    fact = positive[0].facts[0]
    assert fact.key == "seconds_since_recovery" and fact.value == 8.0
    assert fact.source_event_ids == ["evt-001", "evt-003"]
    assert any("no demuestran" in limit for limit in positive[0].evidence_limits)  # RF-16
    assert _kinds(_analyze(slow.items), "recovery_to_shot") == []
    assert _kinds(_analyze(build_up.items), "recovery_to_shot") == []


# --- Presión sostenida ----------------------------------------------------------

def _pressure_block(events: Events, start_s: float, *, x: float, wins: int) -> None:
    """B presiona a A; ``x`` fija: x < 50 es campo rival para B."""
    for index in range(5 - wins):
        events.pressure(start_s + 10 * index, B, f"b-{index + 1}", (x, 40))
    for index in range(wins):
        events.recovery(start_s + 10 * (5 - wins + index), B, "b-6", (x, 60))


def test_sustained_pressure_positive_in_opponent_half() -> None:
    events = Events()
    _pressure_block(events, 10, x=30, wins=2)        # x' de B = 70

    signals = _kinds(_analyze(events.items), "sustained_pressure")

    assert len(signals) == 1 and signals[0].team_id == B
    facts = {f.key: f for f in signals[0].facts if f.window_end_clock_ms == signals[0].clock_ms}
    assert facts["defensive_actions_opponent_half"].value == 5
    assert facts["ball_wins_opponent_half"].value == 2
    assert facts["defensive_actions_opponent_half"].window_ms == 90_000


def test_sustained_pressure_negative_cases() -> None:
    own_half = Events()
    _pressure_block(own_half, 10, x=70, wins=2)      # x' de B = 30: su propio campo
    no_wins = Events()
    _pressure_block(no_wins, 10, x=30, wins=0)       # cinco presiones sin ganar el balón
    spread = Events()
    for index in range(5):
        spread.pressure(10 + 40 * index, B, "b-1", (30, 40), outcome=EventOutcome.SUCCESS)
    spread.recovery(200, B, "b-2", (30, 40))
    spread.recovery(240, B, "b-2", (30, 40))         # más de 90 s entre acciones

    for case in (own_half, no_wins, spread):
        assert _kinds(_analyze(case.items), "sustained_pressure") == []


def test_sustained_pressure_ignores_unpositioned_actions_and_requires_direction() -> None:
    events = Events()
    for index in range(5):
        events.pressure(10 + index, B, "b-1", None)
    events.recovery(16, B, "b-2", None)
    events.recovery(17, B, "b-2", None)

    assert _kinds(_analyze(events.items), "sustained_pressure") == []
    no_direction = _analyze(events.items, metadata(with_directions=False))
    assert any(n.rule == "sustained_pressure@1" for n in no_direction.notes)


def test_scenario_pressure_is_compared_with_the_previous_window() -> None:
    match = generate_analytics_scenario()
    signal = _kinds(_analyze(match.events, match.metadata), "sustained_pressure")[0]
    windows = [f for f in signal.facts if f.key == "defensive_actions_opponent_half"]

    assert signal.team_id == "team-rio" and signal.clock_ms == 190_000
    assert [w.window_end_clock_ms for w in windows] == [190_000, 100_000]
    assert windows[0].value == 5 and windows[1].value == 0  # RF-17


# --- Hitos de jugador (RF-30) -----------------------------------------------------

def test_milestone_is_emitted_once_at_the_exact_event() -> None:
    reached = Events()
    for index in range(12):
        reached.pass_(5 * index + 1, A, "a-1", (30, 50), (35, 50))
    not_reached = Events()
    for index in range(9):
        not_reached.pass_(5 * index + 1, A, "a-1", (30, 50), (35, 50))
    not_reached.pass_(50, A, "a-1", (30, 50), (35, 50), outcome=KO)

    milestones = _kinds(_analyze(reached.items), "player_milestone")
    assert [(s.anchor_event_id, s.facts[0].key, s.facts[0].value) for s in milestones] == [
        ("evt-010", "passes_completed", 10),
    ]
    assert len(milestones[0].facts[0].source_event_ids) == 10
    assert _kinds(_analyze(not_reached.items), "player_milestone") == []


def test_match_record_pass_needs_distance_improvement_and_history() -> None:
    events = Events()
    for index in range(10):
        events.pass_(index + 1, A, "a-1", (30, 50), (35, 50))
    events.pass_(20, A, "a-2", (10, 10), (55, 90))   # 45 m x 40 m = 60,2 m
    events.pass_(25, A, "a-3", (10, 10), (56, 90))   # apenas mejora: no es hito
    early = Events()
    early.pass_(1, A, "a-2", (10, 10), (55, 90))     # largo, pero sin 10 pases previos

    records = [
        s for s in _kinds(_analyze(events.items), "player_milestone")
        if s.facts[0].key == "match_longest_pass_m"
    ]
    assert [(s.anchor_event_id, s.player_ids) for s in records] == [("evt-011", ("a-2",))]
    assert records[0].facts[0].components[0].key == "previous_record_m"
    assert _kinds(_analyze(early.items), "player_milestone") == []


# --- Indicadores (RF-31, RF-32) ----------------------------------------------------

def test_scenario_control_shift_and_chaos_phase_happen_in_their_phases() -> None:
    match = generate_analytics_scenario()
    analyzer = _analyze(match.events, match.metadata)
    shifts = _kinds(analyzer, "control_shift")
    chaos = _kinds(analyzer, "chaos_phase")

    assert shifts[0].team_id == "team-rio" and 148_000 <= shifts[0].clock_ms <= 330_000
    current, previous = shifts[0].facts
    assert current.value >= 60 and previous.value < 50
    assert {c.key for c in current.components} == {
        "possession_time_share", "completed_passes_share", "final_third_actions_share",
    }
    assert len(chaos) == 1 and 332_000 <= chaos[0].clock_ms <= 452_000
    assert any("no es una estadística oficial" in limit for limit in chaos[0].evidence_limits)


def test_one_sided_control_does_not_trigger_a_shift_and_calm_play_is_not_chaos() -> None:
    events = Events()
    for index in range(80):
        x = 30 + (index % 5) * 10
        events.pass_(5 * index + 1, A, f"a-{index % 5 + 1}", (x, 50), (x + 8, 45))

    analyzer = _analyze(events.items)

    assert _kinds(analyzer, "control_shift") == []
    assert _kinds(analyzer, "chaos_phase") == []


def test_chaotic_stretch_triggers_chaos_with_visible_components() -> None:
    events = Events()
    t = 1.0
    for _ in range(12):
        events.pass_(t, A, "a-1", (45, 50), (55, 50), outcome=KO)
        events.recovery(t + 2, B, "b-1", (55, 50))
        events.pass_(t + 4, B, "b-1", (55, 50), (45, 50), outcome=KO)
        events.recovery(t + 6, A, "a-2", (45, 50))
        t += 8

    chaos = _kinds(_analyze(events.items), "chaos_phase")

    assert len(chaos) == 1
    components = {c.key: c for c in chaos[0].facts[0].components}
    assert set(components) == {"possession_changes_per_min", "failed_pass_ratio", "duels_per_min"}
    assert components["failed_pass_ratio"].value == 1.0
    assert all(c.reference is not None and c.weight is not None for c in components.values())
