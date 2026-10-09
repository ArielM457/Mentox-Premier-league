import asyncio

import pytest

from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.application.video_sync import (
    SynchronizedEvent,
    VideoPlaybackState,
    VideoSynchronizedReplay,
    VideoSyncError,
    VideoTimingBasis,
)
from match_intelligence.domain.contracts import EventSource, MatchEvent


class RecordingSynchronizedPublisher:
    def __init__(self) -> None:
        self.events: list[SynchronizedEvent] = []

    async def publish(self, event: SynchronizedEvent) -> None:
        self.events.append(event)


class RecordingStateRebuilder:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[MatchEvent, ...], int]] = []

    async def rebuild(
        self,
        events: tuple[MatchEvent, ...],
        *,
        video_time_ms: int,
    ) -> None:
        self.calls.append((events, video_time_ms))


def build_replay() -> tuple[
    tuple[MatchEvent, ...],
    RecordingSynchronizedPublisher,
    RecordingStateRebuilder,
    VideoSynchronizedReplay,
]:
    events = generate_acceptance_match().events
    publisher = RecordingSynchronizedPublisher()
    rebuilder = RecordingStateRebuilder()
    replay = VideoSynchronizedReplay(events, publisher, rebuilder)
    return events, publisher, rebuilder, replay


def test_synchronized_event_preserves_match_and_video_times() -> None:
    async def scenario() -> None:
        events, publisher, _, replay = build_replay()
        replay.play()

        delivered = await replay.advance_to(events[0].video_time_ms or 0)

        assert delivered == tuple(publisher.events)
        assert delivered[0].event == events[0]
        assert delivered[0].clock_ms == events[0].clock_ms
        assert delivered[0].video_time_ms == events[0].video_time_ms

    asyncio.run(scenario())


def test_pause_does_not_emit_or_move_to_a_future_position() -> None:
    async def scenario() -> None:
        events, publisher, _, replay = build_replay()
        replay.play()
        await replay.advance_to(events[0].video_time_ms or 0)
        replay.pause()
        paused_at = replay.video_time_ms

        delivered = await replay.advance_to(events[-1].video_time_ms or 0)

        assert delivered == ()
        assert replay.state is VideoPlaybackState.PAUSED
        assert replay.video_time_ms == paused_at
        assert [item.event for item in publisher.events] == [events[0]]

    asyncio.run(scenario())


def test_seek_forward_rebuilds_state_without_publishing_old_messages() -> None:
    async def scenario() -> None:
        events, publisher, rebuilder, replay = build_replay()
        target = events[5].video_time_ms or 0

        history = await replay.seek(target)

        assert history == events[:6]
        assert rebuilder.calls == [(events[:6], target)]
        assert replay.position == 6
        assert replay.video_time_ms == target
        assert publisher.events == []

    asyncio.run(scenario())


def test_play_after_seek_only_publishes_events_after_the_destination() -> None:
    async def scenario() -> None:
        events, publisher, _, replay = build_replay()
        await replay.seek(events[5].video_time_ms or 0)
        replay.play()

        delivered = await replay.advance_to(events[7].video_time_ms or 0)

        assert [item.event for item in delivered] == list(events[6:8])
        assert [item.event for item in publisher.events] == list(events[6:8])

    asyncio.run(scenario())


def test_seek_backward_rebuilds_the_shorter_prefix_without_visible_messages() -> None:
    async def scenario() -> None:
        events, publisher, rebuilder, replay = build_replay()
        await replay.seek(events[7].video_time_ms or 0)

        history = await replay.seek(events[2].video_time_ms or 0)

        assert history == events[:3]
        assert rebuilder.calls[-1] == (events[:3], events[2].video_time_ms)
        assert publisher.events == []

    asyncio.run(scenario())


def test_restart_pauses_and_reconstructs_the_beginning() -> None:
    async def scenario() -> None:
        events, publisher, rebuilder, replay = build_replay()
        replay.play()
        await replay.advance_to(events[3].video_time_ms or 0)

        await replay.restart()

        assert replay.state is VideoPlaybackState.PAUSED
        assert replay.video_time_ms == 0
        assert replay.position == 0
        assert rebuilder.calls[-1] == ((), 0)
        assert [item.event for item in publisher.events] == list(events[:4])

    asyncio.run(scenario())


def test_video_timestamp_is_explicitly_alignment_not_detection() -> None:
    async def scenario() -> None:
        events, _, _, replay = build_replay()
        replay.play()

        delivered = await replay.advance_to(events[0].video_time_ms or 0)

        assert delivered[0].timing_basis is VideoTimingBasis.PROVIDED_EVENT_TIMESTAMP
        assert delivered[0].event.source is EventSource.SYNTHETIC

    asyncio.run(scenario())


def test_event_without_video_time_is_rejected() -> None:
    events, publisher, rebuilder, _ = build_replay()
    without_video_time = events[0].model_copy(update={"video_time_ms": None})

    with pytest.raises(VideoSyncError, match="no tiene video_time_ms"):
        VideoSynchronizedReplay((without_video_time,), publisher, rebuilder)


def test_events_must_be_ordered_by_video_time() -> None:
    events, publisher, rebuilder, _ = build_replay()

    with pytest.raises(VideoSyncError, match="ordenados por video_time_ms"):
        VideoSynchronizedReplay((events[1], events[0]), publisher, rebuilder)


def test_events_must_belong_to_the_same_match() -> None:
    events, publisher, rebuilder, _ = build_replay()
    another_match = events[1].model_copy(update={"match_id": "synthetic-other"})

    with pytest.raises(VideoSyncError, match="mismo partido"):
        VideoSynchronizedReplay((events[0], another_match), publisher, rebuilder)


def test_backward_advance_requires_an_explicit_seek() -> None:
    async def scenario() -> None:
        events, _, _, replay = build_replay()
        replay.play()
        await replay.advance_to(events[2].video_time_ms or 0)

        with pytest.raises(VideoSyncError, match="usar seek"):
            await replay.advance_to(events[0].video_time_ms or 0)

    asyncio.run(scenario())


@pytest.mark.parametrize("invalid_position", [-1, 1.5, True])
def test_video_position_must_be_a_non_negative_integer(
    invalid_position: object,
) -> None:
    async def scenario() -> None:
        _, _, _, replay = build_replay()
        replay.play()

        with pytest.raises(VideoSyncError):
            await replay.advance_to(invalid_position)  # type: ignore[arg-type]

    asyncio.run(scenario())
