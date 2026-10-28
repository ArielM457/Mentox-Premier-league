from match_intelligence.adapters.provisional.analytics import ProvisionalAnalytics
from match_intelligence.adapters.provisional.narrative import ProvisionalNarrative
from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.application.callouts import DEFAULT_CALLOUTS, select_callout
from match_intelligence.application.match_session import MatchSession
from match_intelligence.domain.presentation import Language, ViewerMode, ViewerPreferences


def test_local_catalog_has_fifty_action_specific_phrases() -> None:
    assert len(DEFAULT_CALLOUTS) == 50
    assert len({item.callout_id for item in DEFAULT_CALLOUTS}) == 50
    assert {item.kind for item in DEFAULT_CALLOUTS} == {
        "goal",
        "shot",
        "progressive_pass",
        "foul",
        "yellow_card",
        "red_card",
        "recovery",
        "turnover",
        "pressure",
        "generic",
    }


def test_callout_is_stable_for_the_same_play_and_localized_without_spanish_data() -> None:
    first = select_callout(
        DEFAULT_CALLOUTS, kind="shot", language=Language.ES, stable_id="candidate-9"
    )
    second = select_callout(
        DEFAULT_CALLOUTS, kind="shot", language=Language.ES, stable_id="candidate-9"
    )
    assert first == second
    assert select_callout(
        DEFAULT_CALLOUTS, kind="shot", language=Language.PT, stable_id="candidate-9"
    ) == "Descubra por que esta jogada importa."


def test_every_generated_overlay_exposes_an_attention_callout() -> None:
    match = generate_acceptance_match()
    session = MatchSession(
        metadata=match.metadata,
        events=match.events,
        analytics=ProvisionalAnalytics(),
        narrative=ProvisionalNarrative(),
        correction_narrative=ProvisionalNarrative(),
    )

    batch = session.overlays(ViewerPreferences(mode=ViewerMode.ANALYST))

    assert batch.overlays
    assert all(message.call_to_action.strip() for message in batch.overlays)
