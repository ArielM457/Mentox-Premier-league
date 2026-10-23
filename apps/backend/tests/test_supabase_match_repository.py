from match_intelligence.adapters.provisional.analytics import ProvisionalAnalytics
from match_intelligence.adapters.provisional.narrative import ProvisionalNarrative
from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.adapters.storage.supabase_match import SupabaseMatchRepository
from match_intelligence.application.match_session import MatchSession
from match_intelligence.application.persistence import NullMatchPersistence
from match_intelligence.domain.presentation import ViewerPreferences


class FakeQuery:
    def __init__(self, table: str, writes: list[tuple[str, str, object]]) -> None:
        self.table = table
        self.writes = writes

    def upsert(self, value):
        self.writes.append((self.table, "upsert", value))
        return self

    def insert(self, value):
        self.writes.append((self.table, "insert", value))
        return self

    def execute(self):
        return None


class FakeClient:
    def __init__(self) -> None:
        self.writes: list[tuple[str, str, object]] = []

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(name, self.writes)


def test_disabled_supabase_uses_noop(monkeypatch) -> None:
    monkeypatch.setenv("SUPABASE_ENABLED", "false")
    assert isinstance(SupabaseMatchRepository.from_environment(), NullMatchPersistence)


def test_match_moments_and_questions_are_written_idempotently() -> None:
    match = generate_acceptance_match()
    client = FakeClient()
    repository = SupabaseMatchRepository(client)
    session = MatchSession(
        metadata=match.metadata,
        events=match.events,
        analytics=ProvisionalAnalytics(),
        narrative=ProvisionalNarrative(),
        correction_narrative=ProvisionalNarrative(),
        persistence=repository,
    )

    repository.save_match(match.metadata, match.events)
    first = session.overlays(ViewerPreferences(mode="analyst"))
    session.overlays(ViewerPreferences(mode="analyst"))
    session.ask("¿Qué está pasando en el partido?", 40_000, ViewerPreferences())

    tables = [table for table, _, _ in client.writes]
    assert tables.count("matches") == 1
    assert tables.count("match_events") == 1
    assert tables.count("moments") == 1
    assert tables.count("assistant_messages") == 1
    assert first.overlays
