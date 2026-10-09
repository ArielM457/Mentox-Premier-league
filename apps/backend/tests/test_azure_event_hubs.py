import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from azure.eventhub import EventData

from match_intelligence.adapters.messaging.azure_event_hubs import (
    AzureEventHubConsumer,
    AzureEventHubPublisher,
    EventPublicationError,
)
from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.application.transport import (
    MatchEventEnvelope,
    create_match_event_envelope,
)


UTC = timezone.utc


class SequenceClock:
    def __init__(self, *values: datetime) -> None:
        self._values = iter(values)

    def __call__(self) -> datetime:
        return next(self._values)


class RecordingProducerClient:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.batches: list[list[EventData]] = []
        self.partition_keys: list[str | None] = []
        self.closed = False

    async def send_batch(
        self,
        event_data_batch: list[EventData],
        *,
        partition_key: str | None = None,
    ) -> None:
        self.batches.append(event_data_batch)
        self.partition_keys.append(partition_key)
        if self.error is not None:
            raise self.error

    async def close(self) -> None:
        self.closed = True


class RecordingConsumerClient:
    def __init__(self) -> None:
        self.receive_kwargs: dict[str, object] = {}
        self.closed = False

    async def receive(self, on_event: object, **kwargs: object) -> None:
        self.receive_kwargs = {"on_event": on_event, **kwargs}

    async def close(self) -> None:
        self.closed = True


class RecordingCredential:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class RecordingPartitionContext:
    def __init__(self) -> None:
        self.checkpointed: list[EventData] = []

    async def update_checkpoint(self, event: EventData) -> None:
        self.checkpointed.append(event)


def _enveloped_event(index: int = 0, *, message_id: str = "msg-test") -> EventData:
    event = generate_acceptance_match().events[index]
    envelope = create_match_event_envelope(
        event,
        producer="test-producer",
        clock=lambda: datetime(2026, 10, 9, 12, 0, tzinfo=UTC),
        message_id_factory=lambda: message_id,
    )
    return EventData(envelope.model_dump_json())


def test_envelope_round_trip_preserves_match_event() -> None:
    event = generate_acceptance_match().events[0]
    envelope = create_match_event_envelope(
        event,
        producer="test-producer",
        clock=lambda: datetime(2026, 10, 9, 12, 0, tzinfo=UTC),
        message_id_factory=lambda: "msg-001",
    )

    restored = MatchEventEnvelope.model_validate_json(envelope.model_dump_json())

    assert restored == envelope
    assert restored.payload == event
    assert restored.correlation_id == event.match_id


def test_publisher_sends_documented_envelope_and_records_timings() -> None:
    async def scenario() -> None:
        event = generate_acceptance_match().events[0]
        produced = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
        started = produced + timedelta(milliseconds=2)
        published = produced + timedelta(milliseconds=12)
        client = RecordingProducerClient()
        publisher = AzureEventHubPublisher(
            client,
            producer="test-producer",
            clock=SequenceClock(produced, started, published),
            message_id_factory=lambda: "msg-001",
        )

        await publisher.publish(event)

        assert client.partition_keys == [event.match_id]
        envelope = MatchEventEnvelope.model_validate_json(
            client.batches[0][0].body_as_str()
        )
        assert envelope.message_id == "msg-001"
        assert envelope.message_type == "match_event.created"
        assert envelope.payload == event
        receipt = publisher.receipts[0]
        assert receipt.produced_at == produced
        assert receipt.publication_started_at == started
        assert receipt.published_at == published
        assert receipt.publication_duration_ms == 10

    asyncio.run(scenario())


def test_publication_failure_is_visible_and_does_not_mutate_event() -> None:
    async def scenario() -> None:
        event = generate_acceptance_match().events[0]
        original = event.model_dump(mode="json")
        now = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
        client = RecordingProducerClient(ConnectionError("network unavailable"))
        publisher = AzureEventHubPublisher(
            client,
            clock=SequenceClock(now, now, now),
            message_id_factory=lambda: "msg-failed",
        )

        with pytest.raises(EventPublicationError) as captured:
            await publisher.publish(event)

        assert captured.value.failure.message_id == "msg-failed"
        assert captured.value.failure.error_type == "ConnectionError"
        assert publisher.failures == (captured.value.failure,)
        assert publisher.receipts == ()
        assert event.model_dump(mode="json") == original

    asyncio.run(scenario())


def test_consumer_restores_payload_and_measures_transport_latency() -> None:
    produced = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
    received = produced + timedelta(milliseconds=25)
    event = generate_acceptance_match().events[0]
    envelope = create_match_event_envelope(
        event,
        producer="test-producer",
        clock=lambda: produced,
        message_id_factory=lambda: "msg-001",
    )
    consumer = AzureEventHubConsumer(RecordingConsumerClient())

    result = consumer.consume_message(
        EventData(envelope.model_dump_json()),
        received_at=received,
    )

    assert result is not None
    assert result.event == event
    assert result.message_id == "msg-001"
    assert result.transport_latency_ms == 25
    assert consumer.accepted == (result,)


def test_invalid_message_is_recorded_without_stopping_later_message() -> None:
    consumer = AzureEventHubConsumer(RecordingConsumerClient())

    rejected = consumer.consume_message(EventData('{"not": "an envelope"}'))
    accepted = consumer.consume_message(_enveloped_event())

    assert rejected is None
    assert accepted is not None
    assert len(consumer.rejected) == 1
    assert consumer.rejected[0].arrival_sequence == 0
    assert consumer.rejected[0].code == "ValidationError"
    assert len(consumer.accepted) == 1


def test_retried_event_is_accepted_once_and_duplicate_is_recorded() -> None:
    consumer = AzureEventHubConsumer(RecordingConsumerClient())

    first = consumer.consume_message(_enveloped_event(message_id="msg-first"))
    retry = consumer.consume_message(_enveloped_event(message_id="msg-retry"))

    assert first is not None
    assert retry is None
    assert len(consumer.accepted) == 1
    assert len(consumer.duplicates) == 1
    assert consumer.duplicates[0].message_id == "msg-retry"
    assert consumer.duplicates[0].duplicate.event_id == first.event.event_id


def test_consumer_callback_checkpoints_processed_messages() -> None:
    async def scenario() -> None:
        consumer = AzureEventHubConsumer(RecordingConsumerClient())
        context = RecordingPartitionContext()
        message = _enveloped_event()

        await consumer._on_event(context, message)

        assert context.checkpointed == [message]
        assert len(consumer.accepted) == 1

    asyncio.run(scenario())


def test_receive_passes_callbacks_and_position_to_sdk_client() -> None:
    async def scenario() -> None:
        client = RecordingConsumerClient()
        consumer = AzureEventHubConsumer(client)

        await consumer.receive(starting_position="-1", max_wait_time=2.5)

        assert client.receive_kwargs["on_event"] == consumer._on_event
        assert client.receive_kwargs["on_error"] == consumer._on_error
        assert client.receive_kwargs["starting_position"] == "-1"
        assert client.receive_kwargs["max_wait_time"] == 2.5

    asyncio.run(scenario())


def test_consumer_sdk_error_is_recorded() -> None:
    async def scenario() -> None:
        now = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
        consumer = AzureEventHubConsumer(
            RecordingConsumerClient(),
            clock=lambda: now,
        )

        await consumer._on_error(None, ConnectionError("connection lost"))

        assert len(consumer.failures) == 1
        assert consumer.failures[0].occurred_at == now
        assert consumer.failures[0].error_type == "ConnectionError"
        assert consumer.failures[0].message == "connection lost"

    asyncio.run(scenario())


def test_close_releases_client_and_owned_credential() -> None:
    async def scenario() -> None:
        producer_client = RecordingProducerClient()
        producer_credential = RecordingCredential()
        publisher = AzureEventHubPublisher(
            producer_client,
            credential=producer_credential,
        )
        consumer_client = RecordingConsumerClient()
        consumer_credential = RecordingCredential()
        consumer = AzureEventHubConsumer(
            consumer_client,
            credential=consumer_credential,
        )

        await publisher.close()
        await consumer.close()

        assert producer_client.closed
        assert producer_credential.closed
        assert consumer_client.closed
        assert consumer_credential.closed

    asyncio.run(scenario())


def test_default_credential_factories_can_be_created_and_closed() -> None:
    async def scenario() -> None:
        publisher = AzureEventHubPublisher.from_default_credential(
            fully_qualified_namespace="example.servicebus.windows.net",
            eventhub_name="match-events",
        )
        consumer = AzureEventHubConsumer.from_default_credential(
            fully_qualified_namespace="example.servicebus.windows.net",
            eventhub_name="match-events",
            consumer_group="diagnostics",
        )

        await publisher.close()
        await consumer.close()

    asyncio.run(scenario())
