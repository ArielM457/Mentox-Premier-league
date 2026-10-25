"""Datos ficticios en Supabase (PostgreSQL).

Las pruebas de filas y combinaciones no necesitan base de datos. Las de
integración usan ``SUPABASE_TEST_DB_URL``, que debe apuntar a un PostgreSQL
desechable (por ejemplo, uno local): borran y vuelven a crear el esquema
``match_analytics``. Por seguridad no se ejecutan contra un proyecto de Supabase.
"""

import asyncio
import json
import os
from pathlib import Path

import pytest

from match_intelligence.adapters.messaging.insights_memory import InMemoryInsightPublisher
from match_intelligence.adapters.sources.analytics_scenarios import generate_analytics_scenario
from match_intelligence.adapters.sources.live_scenario import generate_live_scenario
from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.adapters.storage.analytics_files import InMemoryAnalyticsWriter
from match_intelligence.adapters.storage.analytics_sinks import (
    FanOutAnalyticsWriter,
    FirstAvailableMetadataProvider,
)
from match_intelligence.adapters.storage.supabase_store import (
    CatalogEntry,
    SupabaseAnalyticsWriter,
    SupabaseMatchMetadataProvider,
    SupabaseMatchStore,
    SupabaseStoreError,
    event_from_row,
    event_row,
    EVENT_COLUMNS,
    file_content,
    identity_from_row,
    identity_row,
    IDENTITY_COLUMNS,
    metadata_from_rows,
    match_row,
    observation_from_row,
    observation_row,
    OBSERVATION_COLUMNS,
    player_row,
    with_match_id,
)
from match_intelligence.application.analytics.stream import (
    AnalyticsStreamProcessor,
    StaticMetadataProvider,
)
from match_intelligence.application.analytics.tracking_input import tracks_from_observations
from match_intelligence.application.vision_evaluation import PredictionOrigin

from match_intelligence.adapters.sources.tracking_mock import generate_mock_tracking

MIGRATIONS = Path(__file__).resolve().parents[3] / "infra" / "supabase" / "migrations"
TEST_DB_URL = os.getenv("SUPABASE_TEST_DB_URL", "")


def _columns(names: str) -> list[str]:
    return [name.strip() for name in names.split(",")]


# ----- filas <-> contratos, sin base de datos ---------------------------------


@pytest.mark.parametrize("generate", [generate_analytics_scenario, generate_live_scenario])
def test_event_rows_round_trip_every_field(generate) -> None:
    match = generate()
    columns = _columns(EVENT_COLUMNS)
    for sequence, event in enumerate(match.events):
        row = dict(zip(columns, event_row(event, sequence), strict=True))
        assert row["sequence"] == sequence
        assert event_from_row(row) == event


def test_metadata_rows_round_trip_with_roster_order() -> None:
    metadata = generate_acceptance_match().metadata
    catalog = CatalogEntry(title="Aurora FC vs Río Unido", scenario="acceptance", seed=2026)
    row = match_row(metadata, catalog)
    row["attacking_directions"] = json.loads(row["attacking_directions"])
    players = [
        dict(zip(
            ["match_id", "player_id", "roster_order", "team_id", "name", "shirt_number", "is_goalkeeper"],
            player_row(metadata.match_id, order, p, frozenset()),
            strict=True,
        ))
        for order, p in enumerate(metadata.players)
    ]
    assert metadata_from_rows(row, players) == metadata


def test_observation_and_identity_rows_round_trip() -> None:
    match = generate_acceptance_match()
    tracking = generate_mock_tracking(match.metadata, match.events)
    obs_columns, id_columns = _columns(OBSERVATION_COLUMNS), _columns(IDENTITY_COLUMNS)
    for observation in tracking.observations[:200]:
        row = dict(zip(obs_columns, observation_row(observation, tracking.origin), strict=True))
        assert row["origin"] == PredictionOrigin.SIMULATED_FIXTURE.value
        assert observation_from_row(row) == observation
    for identity in tracking.identities:
        assert identity_from_row(dict(zip(id_columns, identity_row(identity), strict=True))) == identity


def test_jsonl_files_become_arrays_and_json_stays_an_object() -> None:
    assert file_content("candidates.jsonl", b'{"a": 1}\n{"a": 2}\n') == [{"a": 1}, {"a": 2}]
    assert file_content("revisions.jsonl", b"") == []
    assert file_content("run.json", b'{"events": 3}') == {"events": 3}


def test_replay_copy_changes_only_the_match_id() -> None:
    match = generate_acceptance_match()
    copy = with_match_id(match, "synthetic-acceptance-001-live-1")
    assert copy.metadata.match_id == "synthetic-acceptance-001-live-1"
    assert {e.match_id for e in copy.events} == {"synthetic-acceptance-001-live-1"}
    assert [e.event_id for e in copy.events] == [e.event_id for e in match.events]
    assert copy.metadata.players == match.metadata.players


def test_store_is_optional_without_its_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    assert SupabaseMatchStore.from_env() is None


# ----- combinaciones del procesador continuo ---------------------------------


class _Metadata:
    def __init__(self, known: dict) -> None:
        self.known = known
        self.asked: list[str] = []

    async def get(self, match_id: str):
        self.asked.append(match_id)
        return self.known.get(match_id)


def test_first_available_metadata_provider_falls_back_in_order() -> None:
    metadata = generate_acceptance_match().metadata
    first, second = _Metadata({}), _Metadata({metadata.match_id: metadata})
    provider = FirstAvailableMetadataProvider(first, second)
    assert asyncio.run(provider.get(metadata.match_id)) == metadata
    assert asyncio.run(provider.get("missing")) is None
    assert first.asked == second.asked == [metadata.match_id, "missing"]


def test_fan_out_writer_writes_every_file_everywhere() -> None:
    blob, database = InMemoryAnalyticsWriter(), InMemoryAnalyticsWriter()
    writer = FanOutAnalyticsWriter(blob, database)
    location = asyncio.run(writer.write(
        match_id="m", run_id="r", name="run.json", content=b"{}", content_type="application/json"
    ))
    assert location == "memory://analytics/m/r/run.json"
    assert blob.files == database.files


# ----- integración con PostgreSQL ----------------------------------------------

needs_database = pytest.mark.skipif(
    not TEST_DB_URL or "supabase.co" in TEST_DB_URL or "supabase.com" in TEST_DB_URL,
    reason="Necesita SUPABASE_TEST_DB_URL con un PostgreSQL desechable (nunca el de Supabase)",
)


@pytest.fixture(scope="module")
def store() -> SupabaseMatchStore:
    store = SupabaseMatchStore.from_url(TEST_DB_URL)
    store.apply_sql("drop schema if exists match_analytics cascade")
    for migration in sorted(MIGRATIONS.glob("*.sql")):
        script = migration.read_text(encoding="utf-8")
        store.apply_sql(script)
        store.apply_sql(script)  # idempotente
    return store


@pytest.fixture(scope="module")
def seeded(store: SupabaseMatchStore) -> dict:
    from supabase_seed_data import DEFAULT_MATCHES, prepare, write

    prepared = {spec.match_id: asyncio.run(prepare(spec)) for spec in DEFAULT_MATCHES}
    for item in prepared.values():
        write(store, item)
    return prepared


def _query(store: SupabaseMatchStore, sql: str, params: tuple = ()) -> list[dict]:
    with store._transaction() as connection:
        return store._rows(connection, sql, params)


@needs_database
def test_seeded_matches_read_back_identical(store: SupabaseMatchStore, seeded: dict) -> None:
    for match_id, prepared in seeded.items():
        loaded = store.load_match(match_id)
        assert loaded.metadata == prepared.match.metadata
        assert loaded.events == prepared.match.events
    assert [m.metadata.match_id for m in store.load_matches()] == list(seeded)


@needs_database
def test_seeded_tracking_gives_the_same_tracks(store: SupabaseMatchStore, seeded: dict) -> None:
    prepared = seeded["synthetic-analytics-001"]
    tracking = store.load_tracking("synthetic-analytics-001")
    assert tracking.origin is PredictionOrigin.SIMULATED_FIXTURE
    assert tracking.identities == prepared.tracking.identities
    assert tracking.goalkeeper_player_ids == prepared.tracking.goalkeeper_player_ids
    match = prepared.match
    assert (
        tracks_from_observations(match.metadata, match.events, tracking).tracks
        == tracks_from_observations(match.metadata, match.events, prepared.tracking).tracks
    )


@needs_database
def test_views_expose_the_analysis(store: SupabaseMatchStore, seeded: dict) -> None:
    emitted = _query(store, """
        select kind, count(*) as n from match_analytics.attention_decisions
        where match_id = 'synthetic-analytics-001' and outcome = 'emitted' group by kind
    """)
    assert {row["kind"] for row in emitted} >= {"goal", "shot", "control_shift"}
    metrics = _query(store, """
        select key, metric -> 'tracking_evidence' ->> 'source' as tracking
        from match_analytics.final_metrics
        where match_id = 'synthetic-analytics-001' and key in ('possession_share', 'top_speed_kmh')
    """)
    assert {(row["key"], row["tracking"]) for row in metrics} == {
        ("possession_share", None), ("top_speed_kmh", "simulated_fixture"),
    }
    alerts = _query(store, "select origin from match_analytics.tracking_alerts")
    assert alerts and {row["origin"] for row in alerts} == {"simulated_fixture"}


@needs_database
def test_reseeding_replaces_instead_of_duplicating(store: SupabaseMatchStore, seeded: dict) -> None:
    from supabase_seed_data import write

    write(store, seeded["synthetic-acceptance-001"])
    rows = _query(store, """
        select (select count(*) from match_analytics.match_events where match_id = %s) as events,
               (select count(*) from match_analytics.analytics_runs where match_id = %s) as runs
    """, ("synthetic-acceptance-001", "synthetic-acceptance-001"))
    assert rows == [{"events": 10, "runs": 1}]


@needs_database
def test_stream_worker_sinks_store_its_run_and_find_metadata(store: SupabaseMatchStore, seeded: dict) -> None:
    source = store.load_match("synthetic-acceptance-001")
    replay = with_match_id(source, "synthetic-acceptance-001-live-test")
    store.replace_match(replay, CatalogEntry(title="Repetición", scenario="replay"))
    assert "synthetic-acceptance-001-live-test" not in [m.metadata.match_id for m in store.load_matches()]

    async def run() -> list[str]:
        metadata = FirstAvailableMetadataProvider(
            SupabaseMatchMetadataProvider(store), StaticMetadataProvider()
        )
        processor = AnalyticsStreamProcessor(metadata, InMemoryInsightPublisher())
        for event in replay.events:
            await processor.process(event)
        writer = FanOutAnalyticsWriter(
            InMemoryAnalyticsWriter(), SupabaseAnalyticsWriter(store, produced_by="stream-worker")
        )
        return await processor.finalize(replay.metadata.match_id, writer, run_id="run-test")

    assert len(asyncio.run(run())) == 7
    runs = _query(store, """
        select produced_by, event_count, candidate_count, engine_version
        from match_analytics.analytics_runs where run_id = 'run-test'
    """)
    assert runs[0]["produced_by"] == "stream-worker" and runs[0]["event_count"] == 10
    assert runs[0]["engine_version"] == "match-state@1"


@needs_database
def test_store_rejects_data_of_another_match(store: SupabaseMatchStore, seeded: dict) -> None:
    tracking = seeded["synthetic-acceptance-001"].tracking
    with pytest.raises(SupabaseStoreError):
        store.replace_tracking("synthetic-analytics-001", tracking)
    with pytest.raises(SupabaseStoreError):
        store.save_run_file(
            match_id="synthetic-analytics-001", run_id="seed-synthetic-acceptance-001",
            name="extra.json", content=b"{}", content_type="application/json", produced_by="x",
        )


@needs_database
def test_api_loads_matches_and_tracking_from_the_database(
    store: SupabaseMatchStore, seeded: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    from match_intelligence.adapters.http.registry import _default_registry

    monkeypatch.setenv("SUPABASE_DB_URL", TEST_DB_URL)
    monkeypatch.setenv("MATCH_SOURCE", "supabase")
    monkeypatch.setenv("ANALYTICS_ENGINE", "persona2")
    registry = _default_registry()
    assert sorted(s.match_id for s in registry.all()) == sorted(seeded)
    snapshot = registry.get("synthetic-analytics-001").snapshot(300_000)
    speeds = [m for m in snapshot.metrics if m.key == "top_speed_kmh" and m.available]
    assert speeds and all(m.value > 0 for m in speeds)
