"""Situaciones del partido (``situation@1``): faltas, tarjetas y detenciones."""

from analytics_builders import A, B, Events, metadata

from match_intelligence.adapters.sources.live_scenario import generate_live_scenario
from match_intelligence.application.analytics.pipeline import MatchAnalytics, MatchAnalyzer
from match_intelligence.domain.contracts import EventType


def _situations(events, preferences=None) -> dict[str, list]:
    report = MatchAnalytics().attention_report(metadata(), events, preferences)
    found: dict[str, list] = {}
    for decision in report.decisions:
        found.setdefault(decision.kind, []).append(decision)
    return found


def test_cards_and_fouls_count_per_team_and_player() -> None:
    ev = Events()
    ev.pass_(5, A, "a-4", (40, 50), (55, 50))
    ev.add(10, EventType.FOUL, B, "b-6", start=(55, 50))
    ev.add(12, EventType.YELLOW_CARD, B, "b-6", start=(55, 50))
    ev.add(40, EventType.FOUL, B, "b-6", start=(60, 40))
    analyzer = MatchAnalyzer(metadata())
    analyzer.extend(ev.items)
    fouls = [s for s in analyzer.signals if s.kind == "foul"]
    assert [next(f.value for f in s.facts if f.player_id == "b-6") for s in fouls] == [1, 2]
    # La segunda falta cercana pierde prioridad por repetición y no se emite.
    decisions = _situations(ev.items, {"mode": "analyst"})["foul"]
    assert [d.outcome.value for d in decisions] == ["emitted", "discarded"]
    candidates = MatchAnalytics().candidates(metadata(), ev.items, {"mode": "analyst"})
    card = next(c for c in candidates if c.kind == "yellow_card")
    assert card.source_event_ids == ["evt-003"] and card.player_ids == ["b-6"]
    assert {(f.key, f.team_id, f.value) for f in card.facts} == {("yellow_cards", B, 1)}


def test_red_card_is_always_emitted_and_events_without_situations_are_not() -> None:
    ev = Events()
    ev.pass_(5, A, "a-4", (40, 50), (55, 50))
    ev.add(20, EventType.RED_CARD, A, "a-5", start=(30, 50))
    decisions = _situations(ev.items, {"mode": "casual"})
    assert [d.outcome.value for d in decisions["red_card"]] == ["emitted"]
    assert not {"foul", "yellow_card", "injury_stoppage"} & decisions.keys()


def test_injury_stoppage_reports_the_event_duration_and_its_limit() -> None:
    ev = Events()
    ev.pass_(5, A, "a-4", (40, 50), (55, 50))
    injury = ev.add(30, EventType.INJURY_STOPPAGE, B, "b-10", start=(50, 50))
    ev.items[-1] = injury.model_copy(update={"stoppage_ms": 12_000})
    candidate = next(
        c for c in MatchAnalytics().candidates(metadata(), ev.items) if c.kind == "injury_stoppage"
    )
    assert [(f.key, f.value, f.unit) for f in candidate.facts] == [("stoppage_seconds", 12.0, "seconds")]
    assert any("diagnóstico médico" in limit for limit in candidate.evidence_limits)


def test_casual_viewers_see_cards_but_not_every_foul() -> None:
    match = generate_live_scenario()
    analytics = MatchAnalytics()
    casual = {c.kind for c in analytics.candidates(match.metadata, match.events, {"mode": "casual"})}
    analyst = {c.kind for c in analytics.candidates(match.metadata, match.events, {"mode": "analyst"})}
    assert {"yellow_card", "injury_stoppage"} <= casual
    assert "foul" not in casual and "foul" in analyst
