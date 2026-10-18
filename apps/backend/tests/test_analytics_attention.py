"""Motor de atención: selección, repetición, preferencias y motivos (RF-14, RF-24 a RF-26)."""

from analytics_builders import A, B, Events, metadata

from match_intelligence.adapters.sources.analytics_scenarios import generate_analytics_scenario
from match_intelligence.application.analytics.pipeline import MatchAnalytics
from match_intelligence.domain.analytics.models import AttentionOutcome, RelevancePreferences
from match_intelligence.domain.contracts import EventOutcome


def _repeated_shots() -> Events:
    """Cinco tiros parecidos de A en menos de 2 minutos."""
    events = Events()
    for index in range(5):
        events.shot(10 + 15 * index, A, "a-9", (75, 30), outcome=EventOutcome.OFF_TARGET)
    return events


def test_similar_repeated_moments_are_limited_with_visible_reason() -> None:
    report = MatchAnalytics().attention_report(metadata(), _repeated_shots().items)

    outcomes = [d.outcome for d in report.decisions]
    assert outcomes[0] is AttentionOutcome.EMITTED
    assert outcomes.count(AttentionOutcome.DISCARDED) >= 3
    discarded = report.discarded[0]
    codes = [reason.code for reason in discarded.reasons]
    assert "repetition" in codes and "below_threshold" in codes
    assert discarded.priority == sum(r.points for r in discarded.reasons if r.code != "below_threshold")


def test_priority_is_the_visible_sum_of_reasons_and_stays_in_range() -> None:
    match = generate_analytics_scenario()
    for preferences in (None, {"mode": "casual"}, {"mode": "analyst"}, {"mode": "player", "favorite_player_id": "aurora-8"}):
        report = MatchAnalytics().attention_report(match.metadata, match.events, preferences)
        for decision in report.decisions:
            total = sum(reason.points for reason in decision.reasons)
            assert decision.priority == max(0, min(100, total))
        for candidate in report.candidates:
            assert candidate.source_event_ids and candidate.reasons
            assert candidate.anchor_event_id in candidate.source_event_ids


def test_rival_goal_is_emitted_even_for_the_other_favorite_club() -> None:
    match = generate_analytics_scenario()
    analytics = MatchAnalytics()
    fan_of_aurora = analytics.candidates(
        match.metadata, match.events, {"mode": "casual", "favorite_team_id": "team-aurora"}
    )

    rio_goals = [c for c in fan_of_aurora if c.kind == "goal" and c.team_id == "team-rio"]
    assert len(rio_goals) == 1
    assert any(r.code == "decisive_fact" for r in rio_goals[0].reasons)


def test_favorite_club_raises_its_moments_without_changing_facts() -> None:
    match = generate_analytics_scenario()
    analytics = MatchAnalytics()
    neutral = {c.candidate_id: c for c in analytics.candidates(match.metadata, match.events, {"mode": "casual"})}
    rio_fan = {
        c.candidate_id: c
        for c in analytics.candidates(match.metadata, match.events, {"mode": "casual", "favorite_team_id": "team-rio"})
    }

    raised = [cid for cid in rio_fan if cid in neutral and rio_fan[cid].team_id == "team-rio"]
    assert raised
    for candidate_id in raised:
        assert rio_fan[candidate_id].priority > neutral[candidate_id].priority or rio_fan[candidate_id].priority == 100
    for candidate_id in set(neutral) & set(rio_fan):
        assert rio_fan[candidate_id].facts == neutral[candidate_id].facts
        assert rio_fan[candidate_id].source_event_ids == neutral[candidate_id].source_event_ids
    assert len(rio_fan) > len(neutral)  # momentos de Río que pasan el umbral solo para su afición


def test_favorite_player_changes_only_moments_where_they_take_part() -> None:
    match = generate_analytics_scenario()
    analytics = MatchAnalytics()
    base = {d.candidate_id: d for d in analytics.attention_report(match.metadata, match.events, {"mode": "analyst"}).decisions}
    fan = {
        d.candidate_id: d
        for d in analytics.attention_report(
            match.metadata, match.events, {"mode": "analyst", "favorite_player_id": "aurora-8"}
        ).decisions
    }
    candidates = {c.candidate_id: c for c in analytics.candidates(match.metadata, match.events, {"mode": "analyst"})}

    for candidate_id, decision in fan.items():
        codes = {r.code for r in decision.reasons}
        candidate = candidates.get(candidate_id)
        if candidate is not None and "aurora-8" not in candidate.player_ids:
            assert "favorite_player" not in codes
        if "favorite_player" in codes:
            assert decision.priority >= base[candidate_id].priority


def test_player_mode_follows_the_player_and_keeps_decisive_goals() -> None:
    match = generate_analytics_scenario()
    candidates = MatchAnalytics().candidates(
        match.metadata, match.events, {"mode": "player", "favorite_player_id": "aurora-8"}
    )

    assert candidates
    for candidate in candidates:
        assert "aurora-8" in candidate.player_ids or candidate.kind == "goal"
    assert {c.team_id for c in candidates if c.kind == "goal"} == {"team-aurora", "team-rio"}


def test_casual_and_analyst_receive_different_selections_of_the_same_facts() -> None:
    match = generate_analytics_scenario()
    analytics = MatchAnalytics()
    casual = analytics.candidates(match.metadata, match.events, {"mode": "casual"})
    analyst = analytics.candidates(match.metadata, match.events, {"mode": "analyst"})

    assert len(analyst) > len(casual)
    analyst_by_id = {c.candidate_id: c for c in analyst}
    for candidate in casual:
        assert candidate.candidate_id in analyst_by_id
        assert analyst_by_id[candidate.candidate_id].facts == candidate.facts


def test_persona_4_preferences_object_is_accepted() -> None:
    from pydantic import BaseModel

    class ViewerPreferences(BaseModel):  # misma forma que la de Persona 4
        language: str = "en"
        mode: str = "analyst"
        level: str = "advanced"
        favorite_team_id: str | None = B
        favorite_player_id: str | None = None

    preferences = RelevancePreferences.from_any(ViewerPreferences())

    assert preferences.mode.value == "analyst"
    assert preferences.favorite_team_id == B
    assert preferences.profile == "mode=analyst;team=team-b"
