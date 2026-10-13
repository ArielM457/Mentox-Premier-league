"""Procesamiento continuo con puertos locales: mismas salidas que se publican en Azure."""

import asyncio
import json
from datetime import datetime, timezone

from match_intelligence.adapters.messaging.analytics_bridge import EventHubAnalyticsBridge
from match_intelligence.adapters.messaging.azure_event_hubs import ReceivedMatchEvent
from match_intelligence.adapters.messaging.insights_memory import InMemoryInsightPublisher
from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.adapters.storage.analytics_files import InMemoryAnalyticsWriter
from match_intelligence.application.analytics.pipeline import MatchAnalytics
from match_intelligence.application.analytics.stream import (
    AnalyticsMessageType,
    AnalyticsStreamProcessor,
    StaticMetadataProvider,
)

FIXED = datetime(2026, 10, 9, 18, 0, tzinfo=timezone.utc)


def _processor(publisher, match):
    counter = iter(range(10_000))
    return AnalyticsStreamProcessor(
        StaticMetadataProvider(match.metadata),
        publisher,
        clock=lambda: FIXED,
        message_id_factory=lambda: f"msg-{next(counter)}",
    )


def test_each_event_publishes_a_snapshot_and_new_moments_once() -> None:
    match = generate_acceptance_match()
    publisher = InMemoryInsightPublisher()
    processor = _processor(publisher, match)

    async def run() -> None:
        for event in match.events:
            await processor.process(event)
        await processor.process(match.events[0])  # duplicado: no publica nada

    asyncio.run(run())

    snapshots = publisher.of_type(AnalyticsMessageType.SNAPSHOT_UPDATED)
    proposals = publisher.of_type(AnalyticsMessageType.CANDIDATE_PROPOSED)
    assert len(snapshots) == len(match.events)
    assert snapshots[-1].payload["score"] == {"team-aurora": 1, "team-rio": 0}
    assert [p.payload["candidate_id"] for p in proposals] == ["moment-evt-009", "moment-evt-010"]
    assert all(p.correlation_id == match.metadata.match_id for p in publisher.envelopes)
    local = MatchAnalytics().candidates(match.metadata, match.events)
    assert [p.payload for p in proposals] == [c.model_dump(mode="json") for c in local]


def test_late_event_publishes_revision_and_withdraws_or_updates_moments() -> None:
    match = generate_acceptance_match()
    events = list(match.events)
    publisher = InMemoryInsightPublisher()
    processor = _processor(publisher, match)
    goal = events[-1]
    # El tiro llega antes que el pase que lo precede: la jugada se recompone.
    arrival = events[:8] + [goal, events[8]]

    async def run() -> None:
        for event in arrival:
            await processor.process(event)

    asyncio.run(run())

    revisions = publisher.of_type(AnalyticsMessageType.STATE_REVISED)
    assert [r.payload["event_id"] for r in revisions] == ["evt-009"]
    assert revisions[0].payload["reason"] == "late_event"
    final = {c.candidate_id: c for c in processor.published_candidates(match.metadata.match_id)}
    expected = {c.candidate_id: c for c in MatchAnalytics().candidates(match.metadata, events)}
    assert final == expected


def test_missing_metadata_is_recorded_without_publishing() -> None:
    match = generate_acceptance_match()
    publisher = InMemoryInsightPublisher()
    processor = AnalyticsStreamProcessor(StaticMetadataProvider(), publisher)

    result = asyncio.run(processor.process(match.events[0]))

    assert result.outcome == "missing_metadata"
    assert publisher.envelopes == ()
    assert processor.missing_metadata_event_ids == ("evt-001",)


def test_finalize_writes_traceable_run_files_with_hashes() -> None:
    match = generate_acceptance_match()
    processor = _processor(InMemoryInsightPublisher(), match)
    writer = InMemoryAnalyticsWriter()

    async def run() -> list[str]:
        for event in match.events:
            await processor.process(event)
        return await processor.finalize(match.metadata.match_id, writer, run_id="run-1")

    locations = asyncio.run(run())

    names = [location.rsplit("/", 1)[-1] for location in locations]
    assert names == [
        "final-snapshot.json", "state-timeline.jsonl", "candidates.jsonl", "withdrawals.jsonl",
        "attention-decisions.jsonl", "revisions.jsonl", "run.json",
    ]
    manifest = json.loads(writer.files[locations[-1]][0])
    assert manifest["events"] == 10 and manifest["candidates"] == 2
    assert manifest["late_event_policy"] == "rebuild_from_ordered_history@1"
    assert {m["name"]: m["enabled"] for m in manifest["value_models"]} == {"xt": False, "xg": False, "vaep": False}
    assert manifest["processing_ms"]["count"] == 10
    from hashlib import sha256
    for location, name in zip(locations, names):
        if name != "run.json":
            assert manifest["files"][name] == sha256(writer.files[location][0]).hexdigest()


def test_bridge_connects_persona_1_ingestion_to_the_processor_in_arrival_order() -> None:
    match = generate_acceptance_match()
    events = list(match.events)
    accepted = [
        ReceivedMatchEvent(message_id=f"m-{i}", event=e, produced_at=FIXED, received_at=FIXED)
        for i, e in enumerate(events[:4] + events[5:8] + [events[4]] + events[8:])
    ]

    class Source:
        def __init__(self) -> None:
            self.accepted: list[ReceivedMatchEvent] = []

    source = Source()
    publisher = InMemoryInsightPublisher()
    bridge = EventHubAnalyticsBridge(source, _processor(publisher, match))

    async def run():
        source.accepted.extend(accepted[:5])
        first = await bridge.drain()
        source.accepted.extend(accepted[5:])
        second = await bridge.drain()
        return first + second

    steps = asyncio.run(run())

    assert bridge.processed == 10
    assert [s.arrival_status for s in steps].count("late") == 1
    late = next(s for s in steps if s.arrival_status == "late")
    assert late.received.event.event_id == "evt-005" and late.result.outcome == "rebuilt"
