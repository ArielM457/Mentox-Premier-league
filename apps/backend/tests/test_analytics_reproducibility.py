"""Dos ejecuciones del mismo partido producen lo mismo (RNF-01) y los momentos son causales."""

from analytics_scenarios import generate_analytics_scenario
from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.application.analytics.pipeline import MatchAnalytics, build_snapshot

PROFILES = (None, {"mode": "casual"}, {"mode": "analyst"}, {"mode": "player", "favorite_player_id": "aurora-8"})


def _run(match) -> list[str]:
    analytics = MatchAnalytics()
    outputs = [build_snapshot(match.metadata, match.events).model_dump_json()]
    for preferences in PROFILES:
        report = analytics.attention_report(match.metadata, match.events, preferences)
        outputs.extend(c.model_dump_json() for c in report.candidates)
        outputs.extend(d.model_dump_json() for d in report.decisions)
    return outputs


def test_two_runs_of_the_same_match_are_identical() -> None:
    for generate in (generate_acceptance_match, generate_analytics_scenario):
        assert _run(generate()) == _run(generate())


def test_scenario_generator_is_deterministic_and_seed_sensitive() -> None:
    assert generate_analytics_scenario().events == generate_analytics_scenario().events
    assert generate_analytics_scenario(seed=8).events != generate_analytics_scenario().events


def test_moments_of_a_prefix_never_change_when_more_events_arrive() -> None:
    match = generate_analytics_scenario()
    full = MatchAnalytics().candidates(match.metadata, match.events, {"mode": "analyst"})

    for cut in (40, 90, 140, len(match.events)):
        prefix = match.events[:cut]
        fresh = MatchAnalytics().candidates(match.metadata, prefix, {"mode": "analyst"})
        anchors = {e.event_id for e in prefix}
        assert fresh == [c for c in full if c.anchor_event_id in anchors]


def test_cached_analytics_answers_growing_and_shrinking_prefixes_like_fresh_runs() -> None:
    match = generate_analytics_scenario()
    cached = MatchAnalytics()
    for cut in (30, 120, 60, 178, 10, 150):
        prefix = match.events[:cut]
        assert cached.candidates(match.metadata, prefix) == MatchAnalytics().candidates(match.metadata, prefix)


def test_input_order_does_not_change_the_result() -> None:
    match = generate_analytics_scenario()
    shuffled = list(reversed(match.events))

    analytics = MatchAnalytics()
    assert analytics.candidates(match.metadata, shuffled) == analytics.candidates(match.metadata, match.events)
    assert build_snapshot(match.metadata, shuffled) == build_snapshot(match.metadata, match.events)
