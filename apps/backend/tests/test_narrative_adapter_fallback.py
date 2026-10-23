from match_intelligence.adapters.agents.narrative_port import Persona3NarrativeAdapter
from match_intelligence.adapters.provisional.analytics import ProvisionalAnalytics
from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.domain.presentation import VerificationStatus, ViewerPreferences


class FailingGateway:
    def __init__(self) -> None:
        self.calls = 0

    def plan(self, *args, **kwargs):
        self.calls += 1
        raise TimeoutError("provider unavailable")


def _context():
    match = generate_acceptance_match()
    analytics = ProvisionalAnalytics()
    snapshot = analytics.snapshot(match.metadata, match.events, video_time_ms=40_000)
    candidates = analytics.candidates(match.metadata, match.events, ViewerPreferences(mode="analyst"))
    return match, snapshot, candidates


def test_unavailable_model_publishes_grounded_local_fallback() -> None:
    match, snapshot, candidates = _context()
    gateway = FailingGateway()
    adapter = Persona3NarrativeAdapter(gateway)

    first = adapter.live(match.metadata, snapshot, candidates[0], ViewerPreferences(mode="analyst"))
    second = adapter.live(match.metadata, snapshot, candidates[-1], ViewerPreferences(mode="analyst"))

    assert first.verification_status is VerificationStatus.APPROVED
    assert second.verification_status is VerificationStatus.APPROVED
    assert first.source_event_ids and second.source_event_ids
    assert "provider:fallback-local" in first.applied_preferences
    assert gateway.calls == 1


def test_fixture_assistant_receives_metrics_and_player_identity() -> None:
    match, snapshot, _ = _context()
    adapter = Persona3NarrativeAdapter.fixture()

    answer = adapter.answer(
        match.metadata,
        match.events,
        snapshot,
        "¿Cuántos tiros tiene M. Luz?",
        ViewerPreferences(mode="analyst", level="advanced"),
    )

    assert answer.source_event_ids
    assert "M. Luz" in f"{answer.headline} {answer.explanation}"


def test_fixture_live_moment_uses_names_instead_of_internal_ids() -> None:
    match, snapshot, candidates = _context()
    adapter = Persona3NarrativeAdapter.fixture()
    goal = next(candidate for candidate in candidates if candidate.kind == "goal")

    moment = adapter.live(match.metadata, snapshot, goal, ViewerPreferences(mode="analyst"))

    assert "M. Luz" in f"{moment.headline} {moment.explanation}"
    assert "aurora-9" not in f"{moment.headline} {moment.explanation}"


def test_open_question_uses_latest_recorded_action() -> None:
    match, snapshot, _ = _context()
    adapter = Persona3NarrativeAdapter.fixture()

    answer = adapter.answer(
        match.metadata,
        match.events,
        snapshot,
        "¿Qué está pasando en el partido?",
        ViewerPreferences(mode="analyst"),
    )

    assert answer.source_event_ids
    assert "Datos insuficientes" not in answer.headline
