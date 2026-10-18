"""Datos ficticios para Supabase: partidos, seguimiento simulado y su análisis.

Todo es sintético:

* los partidos salen del generador de Persona 1 y del escenario de Persona 2;
* las posiciones salen de ``tracking_mock`` con el formato de visión de
  Persona 1 y origen ``simulated_fixture``;
* el análisis es el del procesador continuo de Persona 2, con los mismos
  archivos que guarda en Blob, más las cifras y avisos de seguimiento.

Lo usan ``scripts/supabase_seed.py`` y las pruebas.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from match_intelligence.adapters.messaging.insights_memory import InMemoryInsightPublisher
from match_intelligence.adapters.sources.analytics_scenarios import generate_analytics_scenario
from match_intelligence.adapters.sources.synthetic import SyntheticMatch, generate_acceptance_match
from match_intelligence.adapters.storage.analytics_files import InMemoryAnalyticsWriter
from match_intelligence.adapters.storage.supabase_store import CatalogEntry, SupabaseMatchStore
from match_intelligence.application.analytics.stream import (
    AnalyticsStreamProcessor,
    StaticMetadataProvider,
)
from match_intelligence.application.analytics.tracking_input import (
    TrackingInput,
    tracks_from_observations,
)
from match_intelligence.domain.analytics.tracking import tracking_alerts, tracking_metrics

from tracking_mock import generate_mock_tracking

PRODUCED_BY = "supabase-seed"
GENERATORS = {
    "acceptance": generate_acceptance_match,
    "analytics": generate_analytics_scenario,
}


@dataclass(frozen=True, slots=True)
class SeedMatch:
    scenario: str
    seed: int
    match_id: str
    label: str
    kickoff_at: datetime


DEFAULT_MATCHES: tuple[SeedMatch, ...] = (
    SeedMatch(
        "acceptance", 2026, "synthetic-acceptance-001", "partido corto de aceptación",
        datetime(2026, 10, 20, 19, 0, tzinfo=UTC),
    ),
    SeedMatch(
        "analytics", 7, "synthetic-analytics-001", "dos tiempos para la analítica",
        datetime(2026, 10, 21, 19, 0, tzinfo=UTC),
    ),
)


@dataclass(frozen=True, slots=True)
class PreparedMatch:
    spec: SeedMatch
    match: SyntheticMatch
    catalog: CatalogEntry
    goalkeeper_player_ids: frozenset[str]
    tracking: TrackingInput
    run_id: str
    files: dict[str, tuple[bytes, str]]


def _jsonl(rows: Sequence[object]) -> bytes:
    lines = [row.model_dump_json() for row in rows]  # type: ignore[attr-defined]
    return ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")


async def prepare(spec: SeedMatch) -> PreparedMatch:
    generate = GENERATORS[spec.scenario]
    match = generate(seed=spec.seed, match_id=spec.match_id)
    metadata = match.metadata
    tracking = generate_mock_tracking(metadata, match.events)

    processor = AnalyticsStreamProcessor(
        StaticMetadataProvider(metadata), InMemoryInsightPublisher(), producer=PRODUCED_BY
    )
    for event in match.events:
        await processor.process(event)
    run_id = f"seed-{spec.match_id}"
    writer = InMemoryAnalyticsWriter()
    await processor.finalize(spec.match_id, writer, run_id=run_id)
    files = {location.rsplit("/", 1)[1]: value for location, value in writer.files.items()}

    tracks = tracks_from_observations(metadata, match.events, tracking).tracks
    team_ids = [metadata.home_team.team_id, metadata.away_team.team_id]
    files["tracking-metrics.jsonl"] = (
        _jsonl(tracking_metrics(tracks, team_ids, match.events)), "application/x-ndjson"
    )
    files["tracking-alerts.jsonl"] = (_jsonl(tracking_alerts(tracks)), "application/x-ndjson")

    title = f"{metadata.home_team.name} vs {metadata.away_team.name} · {spec.label}"
    return PreparedMatch(
        spec=spec,
        match=match,
        catalog=CatalogEntry(
            title=title, scenario=spec.scenario, seed=spec.seed, kickoff_at=spec.kickoff_at
        ),
        goalkeeper_player_ids=tracking.goalkeeper_player_ids,
        tracking=tracking,
        run_id=run_id,
        files=files,
    )


def summary(prepared: PreparedMatch) -> dict[str, object]:
    return {
        "match_id": prepared.spec.match_id,
        "title": prepared.catalog.title,
        "events": len(prepared.match.events),
        "players": len(prepared.match.metadata.players),
        "observations": len(prepared.tracking.observations),
        "identities": len(prepared.tracking.identities),
        "tracking_origin": prepared.tracking.origin.value,
        "run_id": prepared.run_id,
        "files": {name: len(content) for name, (content, _) in sorted(prepared.files.items())},
    }


def write(store: SupabaseMatchStore, prepared: PreparedMatch) -> list[str]:
    """Reemplaza el partido y todo lo que depende de él, incluidos sus análisis anteriores."""
    store.replace_match(
        prepared.match, prepared.catalog, goalkeeper_player_ids=prepared.goalkeeper_player_ids
    )
    store.replace_tracking(prepared.spec.match_id, prepared.tracking)
    ordered = sorted(prepared.files.items(), key=lambda item: item[0] == "run.json")
    return [
        store.save_run_file(
            match_id=prepared.spec.match_id, run_id=prepared.run_id, name=name,
            content=content, content_type=content_type, produced_by=PRODUCED_BY,
        )
        for name, (content, content_type) in ordered
    ]
