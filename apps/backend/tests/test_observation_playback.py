import asyncio

from match_intelligence.application.observation_playback import (
    ObservationPlaybackSession,
    PlaybackObservation,
    load_playback_observations,
)


class RecordingPublisher:
    def __init__(self) -> None:
        self.items = []

    async def publish(self, observation) -> bool:
        self.items.append(observation)
        return True

    async def publish_many(self, observations) -> int:
        self.items.extend(observations)
        return len(observations)


def observations() -> tuple[PlaybackObservation, ...]:
    return (
        PlaybackObservation("det-100", "roboflow", "spatial_detection", 100, {}),
        PlaybackObservation("act-200", "soccernet", "temporal_action", 200, {}),
        PlaybackObservation("det-300", "roboflow", "spatial_detection", 300, {}),
    )


def test_observation_at_zero_is_published_after_play() -> None:
    async def scenario() -> None:
        publisher = RecordingPublisher()
        items = (
            PlaybackObservation("det-000", "roboflow", "spatial_detection", 0, {}),
        )
        session = ObservationPlaybackSession(items, publisher)

        await session.play(0)
        await session.advance(0)

        assert [item.observation_id for item in publisher.items] == ["det-000"]

    asyncio.run(scenario())


def test_play_and_pause_gate_publication() -> None:
    async def scenario() -> None:
        publisher = RecordingPublisher()
        session = ObservationPlaybackSession(observations(), publisher)

        await session.advance(150)
        assert publisher.items == []

        await session.play(0)
        await session.advance(150)
        await session.pause(250)
        await session.advance(400)

        assert [item.observation_id for item in publisher.items] == [
            "det-100",
            "act-200",
        ]
        assert session.snapshot()["playback_state"] == "paused"
        assert session.snapshot()["position_ms"] == 250

    asyncio.run(scenario())


def test_seek_moves_cursor_without_republishing_history() -> None:
    async def scenario() -> None:
        publisher = RecordingPublisher()
        session = ObservationPlaybackSession(observations(), publisher)

        await session.seek(250)
        assert publisher.items == []
        assert session.snapshot()["cursor"] == 2

        await session.play(250)
        await session.advance(350)
        assert [item.observation_id for item in publisher.items] == ["det-300"]

    asyncio.run(scenario())


def test_restart_pauses_and_resets_session_counters() -> None:
    async def scenario() -> None:
        publisher = RecordingPublisher()
        session = ObservationPlaybackSession(observations(), publisher)
        await session.play(0)
        await session.advance(350)

        snapshot = await session.restart()

        assert snapshot["playback_state"] == "paused"
        assert snapshot["position_ms"] == 0
        assert snapshot["cursor"] == 0
        assert snapshot["published_in_session"] == 0

    asyncio.run(scenario())


def test_loader_includes_each_roboflow_model_role() -> None:
    class Pipeline:
        roboflow = {
            "predictions": [
                {"prediction_id": "p", "timestamp_ms": 20, "model_role": "player"},
                {"prediction_id": "b", "timestamp_ms": 10, "model_role": "ball"},
            ],
            "pitch_observations": [
                {"prediction_id": "k", "timestamp_ms": 15, "model_role": "pitch"}
            ],
        }
        soccernet = {"predictions": []}

    items = load_playback_observations(Pipeline())

    assert [item.observation_id for item in items] == ["b", "k", "p"]
    assert [item.source for item in items] == [
        "roboflow-ball",
        "roboflow-pitch",
        "roboflow-player",
    ]
