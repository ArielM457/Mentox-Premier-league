from analytics_builders import A, B, KO, Events, metadata

from analytics_scenarios import generate_analytics_scenario
from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.application.analytics.pipeline import MatchAnalytics, build_snapshot
from match_intelligence.domain.analytics.catalog import METRIC_CATALOG
from match_intelligence.domain.analytics.models import MetricOrigin
from match_intelligence.domain.contracts import EventOutcome, EventType

COUNT_RULES = {
    "goals": lambda e: e.type is EventType.SHOT and e.outcome is EventOutcome.GOAL,
    "shots": lambda e: e.type is EventType.SHOT,
    "shots_on_target": lambda e: e.type is EventType.SHOT
    and e.outcome in {EventOutcome.GOAL, EventOutcome.SAVED},
    "passes_attempted": lambda e: e.type is EventType.PASS,
    "passes_completed": lambda e: e.type is EventType.PASS and e.outcome is EventOutcome.SUCCESS,
    "recoveries": lambda e: e.type is EventType.RECOVERY,
    "tackles": lambda e: e.type is EventType.TACKLE,
    "tackles_won": lambda e: e.type is EventType.TACKLE and e.outcome is EventOutcome.SUCCESS,
    "pressures": lambda e: e.type is EventType.PRESSURE,
}


def _metric(snapshot, key, team_id=None, player_id=None):
    return next(
        m for m in snapshot.metrics
        if m.key == key and m.team_id == team_id and m.player_id == player_id
    )


def test_every_count_can_be_recalculated_from_its_source_events() -> None:
    match = generate_analytics_scenario()
    by_id = {event.event_id: event for event in match.events}
    snapshot = build_snapshot(match.metadata, match.events)

    checked = 0
    for item in snapshot.metrics:
        if item.key not in COUNT_RULES:
            continue
        sources = [by_id[event_id] for event_id in item.source_event_ids]
        assert item.value == len(sources)
        assert all(COUNT_RULES[item.key](event) for event in sources)
        owner = [e for e in match.events if e.team_id == item.team_id
                 and (item.player_id is None or e.player_id == item.player_id)]
        assert item.value == sum(1 for e in owner if COUNT_RULES[item.key](e))
        checked += 1
    assert checked > 50


def test_pass_accuracy_uses_known_outcomes_and_shows_its_denominator() -> None:
    events = Events()
    events.pass_(1, A, "a-1", (20, 50), (30, 50))
    events.pass_(2, A, "a-1", (30, 50), (40, 50))
    events.pass_(3, A, "a-1", (40, 50), (50, 50), outcome=KO)
    events.pass_(4, A, "a-1", (50, 50), (60, 50), outcome=EventOutcome.UNKNOWN)

    snapshot = build_snapshot(metadata(), events.items)
    accuracy = _metric(snapshot, "pass_accuracy", A)

    assert accuracy.value == 66.7
    assert accuracy.source_event_ids == ["evt-001", "evt-002", "evt-003"]
    assert [(c.key, c.value) for c in accuracy.components] == [
        ("passes_completed", 2), ("passes_with_known_outcome", 3),
    ]
    assert _metric(snapshot, "passes_attempted", A).value == 4


def test_ratio_without_data_is_unavailable_instead_of_zero() -> None:
    events = Events()
    events.pass_(1, A, "a-1", (20, 50), (30, 50))

    snapshot = build_snapshot(metadata(), events.items)
    accuracy_b = _metric(snapshot, "pass_accuracy", B)

    assert accuracy_b.available is False
    assert accuracy_b.value is None
    assert accuracy_b.unavailable_reason
    assert _metric(snapshot, "shots", B).value == 0  # un conteo observado sí vale cero


def test_progressive_passes_follow_the_attack_direction_of_each_period() -> None:
    events = Events()
    events.pass_(1, A, "a-1", (30, 50), (45, 50))                # +15 m hacia B: progresivo
    events.pass_(2, A, "a-1", (45, 50), (40, 50))                # hacia atrás
    events.pass_(3, A, "a-1", (70, 50), (55, 50), period=2)      # período 2: A ataca hacia x=0
    events.pass_(4, A, "a-1", (55, 50), (70, 50), period=2)      # hacia atrás en el período 2

    snapshot = build_snapshot(metadata(), events.items)
    progressive = _metric(snapshot, "progressive_passes", A)

    assert progressive.value == 2
    assert progressive.source_event_ids == ["evt-001", "evt-003"]


def test_spatial_metrics_without_direction_are_unavailable() -> None:
    events = Events()
    events.pass_(1, A, "a-1", (30, 50), (60, 50))

    snapshot = build_snapshot(metadata(with_directions=False), events.items)

    assert _metric(snapshot, "progressive_passes", A).available is False
    assert _metric(snapshot, "final_third_entries", A).available is False
    # La distancia no depende de la dirección de ataque.
    assert _metric(snapshot, "avg_pass_distance_m", A).value == 30.0


def test_pass_distance_uses_pitch_dimensions() -> None:
    events = Events()
    events.pass_(1, A, "a-1", (10, 10), (40, 90))  # dx = 30 m, dy = 80 % de 50 m = 40 m

    snapshot = build_snapshot(metadata(), events.items)

    assert _metric(snapshot, "longest_pass_m", A).value == 50.0


def test_speed_metrics_are_declared_unavailable_with_reason() -> None:
    snapshot = build_snapshot(generate_acceptance_match().metadata, generate_acceptance_match().events)

    for key in ("ball_speed_kmh", "shot_speed_kmh"):
        item = _metric(snapshot, key)
        assert item.available is False and "MatchEvent 1.0" in item.unavailable_reason
    assert _metric(snapshot, "distance_covered_m", "team-aurora", "aurora-9").available is False


def test_player_metrics_only_use_identified_events() -> None:
    events = Events()
    events.pass_(1, A, "a-1", (20, 50), (30, 50))
    events.pass_(2, A, None, (30, 50), (40, 50))
    events.pass_(3, A, "a-2", (40, 50), (50, 50))

    snapshot = build_snapshot(metadata(), events.items)

    assert _metric(snapshot, "involvement", A, "a-1").source_event_ids == ["evt-001"]
    assert _metric(snapshot, "passes_attempted", A).value == 3
    assert not any(m.player_id == "a-3" for m in snapshot.metrics)  # sin eventos, sin cifras


def test_every_emitted_metric_is_in_the_catalog_with_its_version() -> None:
    match = generate_analytics_scenario()
    analytics = MatchAnalytics()
    snapshot = analytics.snapshot(match.metadata, match.events)
    candidates = analytics.candidates(match.metadata, match.events, {"mode": "analyst"})

    for item in snapshot.metrics + [fact for c in candidates for fact in c.facts]:
        definition = METRIC_CATALOG[item.key]
        assert item.unit == definition.unit
        assert item.origin is definition.origin
        if definition.origin is not MetricOrigin.VALUE_MODEL:
            assert item.formula_version == definition.formula_version
