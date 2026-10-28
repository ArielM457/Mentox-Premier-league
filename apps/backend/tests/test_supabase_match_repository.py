from match_intelligence.adapters.provisional.analytics import ProvisionalAnalytics
from match_intelligence.adapters.provisional.narrative import ProvisionalNarrative
from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.adapters.storage.supabase_match import SupabaseMatchRepository
from match_intelligence.application.match_session import MatchSession
from match_intelligence.application.persistence import NullMatchPersistence
from match_intelligence.domain.presentation import ViewerPreferences
from types import SimpleNamespace


class FakeQuery:
    def __init__(self, table: str, writes: list[tuple[str, str, object]], rows: dict[str, list[dict]]) -> None:
        self.table = table
        self.writes = writes
        self.rows = rows
        self.operation = "select"

    def upsert(self, value):
        self.operation = "upsert"
        self.writes.append((self.table, "upsert", value))
        return self

    def insert(self, value):
        self.operation = "insert"
        self.writes.append((self.table, "insert", value))
        return self

    def select(self, _fields):
        return self

    def eq(self, _field, _value):
        return self

    def execute(self):
        return SimpleNamespace(data=self.rows.get(self.table, []) if self.operation == "select" else [])


class FakeClient:
    def __init__(self, rows: dict[str, list[dict]] | None = None) -> None:
        self.writes: list[tuple[str, str, object]] = []
        self.rows = rows or {}

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(name, self.writes, self.rows)


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
    session.summary(ViewerPreferences())

    tables = [table for table, _, _ in client.writes]
    assert tables.count("matches") == 1
    assert tables.count("match_events") == 1
    assert tables.count("moments") == 1
    assert tables.count("assistant_messages") == 1
    assert tables.count("match_summaries") == 1
    summary_write = next(value for table, operation, value in client.writes if table == "match_summaries" and operation == "upsert")
    assert summary_write["summary_type"] == "extended"
    assert summary_write["player_id"] is None
    assert first.overlays


def test_action_callouts_are_loaded_from_supabase() -> None:
    client = FakeClient({
        "action_callouts": [{
            "callout_id": "cta-shot-test",
            "kind": "shot",
            "language": "es",
            "text": "¿Entraba ese remate? Revisa la jugada.",
        }]
    })

    callouts = SupabaseMatchRepository(client).load_callouts()

    assert len(callouts) == 1
    assert callouts[0].kind == "shot"
    assert callouts[0].text.startswith("¿Entraba")
