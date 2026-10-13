"""Reconstrucción ante tardíos, correcciones y retiros (RF-05, DV-US-05)."""

import asyncio

from analytics_builders import A, Events, metadata

from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.application.analytics.engine import (
    IngestOutcome,
    MatchStateEngine,
    RevisionReason,
    replay,
)
from match_intelligence.application.event_order import ArrivalStatus, EventOrderTracker
from match_intelligence.application.video_sync import VideoSynchronizedReplay
from match_intelligence.domain.contracts import EventOutcome


def _comparable(snapshot):
    data = snapshot.model_dump(mode="json")
    for key in ("state_revision", "late_event_ids", "corrected_event_ids"):
        data.pop(key)
    return data


def test_late_event_rebuilds_the_same_state_as_on_time_arrival() -> None:
    match = generate_acceptance_match()
    events = list(match.events)
    in_order = replay(match.metadata, events)
    late_arrival = events[:4] + events[5:8] + [events[4]] + events[8:]

    engine = MatchStateEngine(match.metadata)
    tracker = EventOrderTracker()
    outcomes = []
    for event in late_arrival:
        status = tracker.process((event,)).forwarded[0].status
        outcomes.append((status, engine.ingest(event, arrival_status=status).outcome))

    assert (ArrivalStatus.LATE, IngestOutcome.REBUILT) in outcomes
    assert _comparable(engine.snapshot()) == _comparable(in_order.snapshot())
    assert engine.snapshot().late_event_ids == ["evt-005"]
    assert engine.snapshot().state_revision == 1
    assert [c.candidate_id for c in engine.attention().candidates] == [
        c.candidate_id for c in in_order.attention().candidates
    ]
    revision = engine.revisions[0]
    assert revision.reason is RevisionReason.LATE_EVENT and revision.event_id == "evt-005"
    assert revision.policy == "rebuild_from_ordered_history@1"


def test_correction_replaces_the_event_and_withdraws_moments_it_supported() -> None:
    match = generate_acceptance_match()
    engine = replay(match.metadata, match.events)
    goal = match.events[-1]

    result = engine.correct(goal.model_copy(update={"outcome": EventOutcome.SAVED}))

    assert result.outcome is IngestOutcome.REBUILT
    assert engine.snapshot().score == {"team-aurora": 0, "team-rio": 0}
    assert engine.snapshot().corrected_event_ids == ["evt-010"]
    revision = result.revision
    assert revision.reason is RevisionReason.CORRECTION
    assert revision.score_before == {"team-aurora": 1, "team-rio": 0}
    assert revision.score_after == {"team-aurora": 0, "team-rio": 0}
    kinds = {c.candidate_id: c.kind for c in engine.attention().candidates}
    assert kinds["moment-evt-010"] == "shot"


def test_retraction_removes_the_event_from_every_figure() -> None:
    match = generate_acceptance_match()
    engine = replay(match.metadata, match.events)

    result = engine.retract("evt-010")

    assert result.revision.reason is RevisionReason.RETRACTION
    assert "moment-evt-010" in result.revision.withdrawn_moment_ids
    snapshot = engine.snapshot()
    assert snapshot.score["team-aurora"] == 0
    assert all("evt-010" not in m.source_event_ids for m in snapshot.metrics)


def test_duplicates_are_idempotent_and_conflicts_need_explicit_correction() -> None:
    events = Events()
    first = events.pass_(1, A, "a-1", (20, 50), (30, 50))
    engine = MatchStateEngine(metadata())
    engine.ingest(first)

    assert engine.ingest(first).outcome is IngestOutcome.DUPLICATE
    changed = first.model_copy(update={"outcome": EventOutcome.FAILURE})
    assert engine.ingest(changed).outcome is IngestOutcome.CONFLICT
    assert engine.events == [first]
    assert engine.correct(changed).outcome is IngestOutcome.REBUILT
    assert engine.events == [changed]
    assert engine.retract("missing").outcome is IngestOutcome.UNKNOWN_EVENT


def test_engine_implements_the_video_seek_rebuilder_of_persona_1() -> None:
    match = generate_acceptance_match()
    engine = MatchStateEngine(match.metadata)

    class NoPublish:
        async def publish(self, event) -> None:
            return None

    replay_video = VideoSynchronizedReplay(match.events, NoPublish(), engine)
    asyncio.run(replay_video.seek(30_000))

    snapshot = engine.snapshot()
    assert snapshot.last_event_id == "evt-008"
    assert snapshot.score == {"team-aurora": 0, "team-rio": 0}
    assert snapshot.state_revision == 0  # un salto de vídeo no es una revisión
