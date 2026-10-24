import asyncio
from datetime import UTC, datetime

from azure.eventhub import EventData

from match_intelligence.adapters.messaging.azure_vision_observations import (
    VisionObservationConsumer,
    VisionObservationPublisher,
)
from match_intelligence.application.realtime_observations import (
    LiveObservation,
    RealtimeObservationHub,
)
from match_intelligence.application.vision_runtime import (
    VisionObservationRuntime,
    VisionRuntimeSettings,
)


class ProducerClient:
    def __init__(self) -> None:
        self.events: list[EventData] = []
        self.partition_keys: list[str | None] = []

    async def send_batch(
        self, events: list[EventData], *, partition_key: str | None = None
    ) -> None:
        self.events.extend(events)
        self.partition_keys.append(partition_key)

    async def close(self) -> None:
        pass


class ConsumerClient:
    async def close(self) -> None:
        pass


def observation() -> LiveObservation:
    return LiveObservation(
        observation_id="frame-001-det-001",
        source="roboflow",
        kind="spatial_detection",
        timestamp_ms=40,
        payload={"label": "ball", "track_id": 9, "player_id": None},
        received_at=datetime.now(UTC),
    )


def test_azure_round_trip_preserves_observation_without_match_event() -> None:
    async def scenario() -> None:
        hub = RealtimeObservationHub()
        producer_client = ProducerClient()
        publisher = VisionObservationPublisher(producer_client)
        consumer = VisionObservationConsumer(ConsumerClient(), hub.publish)

        await publisher.publish(observation())
        accepted = await consumer.consume_message(producer_client.events[0])

        assert accepted
        assert producer_client.partition_keys == ["roboflow"]
        latest = hub.snapshot()["latest"]
        assert latest["payload"]["track_id"] == 9
        assert latest["payload"]["player_id"] is None
        assert "event_id" not in latest

    asyncio.run(scenario())


def test_invalid_azure_observation_is_rejected() -> None:
    async def scenario() -> None:
        hub = RealtimeObservationHub()
        consumer = VisionObservationConsumer(ConsumerClient(), hub.publish)

        accepted = await consumer.consume_message(EventData('{"invalid": true}'))

        assert not accepted
        assert consumer.rejected == 1
        assert hub.snapshot()["accepted"] == 0

    asyncio.run(scenario())


def test_memory_runtime_delivers_without_azure() -> None:
    async def scenario() -> None:
        hub = RealtimeObservationHub()
        runtime = VisionObservationRuntime(
            hub,
            VisionRuntimeSettings(transport="memory"),
        )
        await runtime.start()

        assert await runtime.publish(observation())
        assert hub.snapshot()["accepted"] == 1
        assert runtime.status()["transport"] == "memory"

        await runtime.close()

    asyncio.run(scenario())


def test_azure_publisher_groups_observations_into_batches_by_source() -> None:
    async def scenario() -> None:
        producer_client = ProducerClient()
        publisher = VisionObservationPublisher(producer_client)
        first = observation()
        second = LiveObservation(
            observation_id="action-002",
            source="soccernet",
            kind="temporal_action",
            timestamp_ms=80,
            payload={"label": "pass"},
            received_at=datetime.now(UTC),
        )

        await publisher.publish_many((first, first, second))

        assert producer_client.partition_keys == ["roboflow", "soccernet"]
        assert len(producer_client.events) == 3
        assert publisher.published == 3

    asyncio.run(scenario())
