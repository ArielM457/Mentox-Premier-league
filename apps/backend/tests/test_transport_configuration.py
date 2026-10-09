import asyncio
from pathlib import Path

import pytest
from azure.eventhub import EventData

from match_intelligence.adapters.messaging.azure_event_hubs import (
    AzureEventHubConsumer,
    AzureEventHubPublisher,
)
from match_intelligence.adapters.messaging.configuration import (
    EventTransport,
    EventTransportSettings,
    TransportConfigurationError,
    build_event_consumer,
    build_event_publisher,
)
from match_intelligence.adapters.messaging.memory import (
    InMemoryEventConsumer,
    InMemoryEventPublisher,
)
from match_intelligence.adapters.sources.synthetic import generate_acceptance_match


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class RecordingProducerClient:
    def __init__(self) -> None:
        self.events: list[EventData] = []

    async def send_batch(
        self,
        event_data_batch: list[EventData],
        *,
        partition_key: str | None = None,
    ) -> None:
        self.events.extend(event_data_batch)

    async def close(self) -> None:
        pass


class RecordingConsumerClient:
    async def receive(self, on_event: object, **kwargs: object) -> None:
        pass

    async def close(self) -> None:
        pass


def _azure_settings() -> EventTransportSettings:
    return EventTransportSettings.from_mapping(
        {
            "EVENT_TRANSPORT": "azure_event_hubs",
            "EVENT_HUB_FULLY_QUALIFIED_NAMESPACE": (
                "example.servicebus.windows.net"
            ),
            "EVENT_HUB_NAME": "match-events",
            "EVENT_HUB_CONSUMER_GROUP": "backend",
            "EVENT_PRODUCER": "configuration-test",
        }
    )


def test_memory_is_the_default_without_azure_configuration() -> None:
    settings = EventTransportSettings.from_mapping({})

    assert settings.transport is EventTransport.MEMORY
    assert isinstance(build_event_publisher(settings), InMemoryEventPublisher)
    assert isinstance(build_event_consumer(settings), InMemoryEventConsumer)


def test_invalid_transport_is_rejected_with_allowed_values() -> None:
    with pytest.raises(TransportConfigurationError, match="memory, azure_event_hubs"):
        EventTransportSettings.from_mapping({"EVENT_TRANSPORT": "unknown"})


def test_azure_transport_requires_names_but_not_secrets() -> None:
    with pytest.raises(TransportConfigurationError) as captured:
        EventTransportSettings.from_mapping(
            {"EVENT_TRANSPORT": "azure_event_hubs"}
        )

    message = str(captured.value)
    assert "EVENT_HUB_FULLY_QUALIFIED_NAMESPACE" in message
    assert "EVENT_HUB_NAME" in message
    assert "EVENT_HUB_CONSUMER_GROUP" in message
    assert "CONNECTION_STRING" not in message


def test_factories_select_injected_azure_adapters() -> None:
    settings = _azure_settings()

    publisher = build_event_publisher(
        settings,
        azure_client=RecordingProducerClient(),
    )
    consumer = build_event_consumer(
        settings,
        azure_client=RecordingConsumerClient(),
    )

    assert isinstance(publisher, AzureEventHubPublisher)
    assert isinstance(consumer, AzureEventHubConsumer)


def test_same_sequence_is_equivalent_in_memory_and_azure_modes() -> None:
    async def scenario() -> None:
        match = generate_acceptance_match()
        memory_settings = EventTransportSettings.from_mapping(
            {"EVENT_TRANSPORT": "memory"}
        )
        memory_publisher = build_event_publisher(memory_settings)
        memory_consumer = build_event_consumer(memory_settings)
        assert isinstance(memory_publisher, InMemoryEventPublisher)
        assert isinstance(memory_consumer, InMemoryEventConsumer)

        azure_client = RecordingProducerClient()
        azure_publisher = build_event_publisher(
            _azure_settings(),
            azure_client=azure_client,
        )
        azure_consumer = build_event_consumer(
            _azure_settings(),
            azure_client=RecordingConsumerClient(),
        )
        assert isinstance(azure_publisher, AzureEventHubPublisher)
        assert isinstance(azure_consumer, AzureEventHubConsumer)

        for event in match.events:
            await memory_publisher.publish(event)
            await azure_publisher.publish(event)

        memory_consumer.consume(memory_publisher.events)
        for transport_event in azure_client.events:
            azure_consumer.consume_message(transport_event)

        assert memory_consumer.events == match.events
        assert azure_consumer.events == match.events
        assert azure_consumer.events == memory_consumer.events

    asyncio.run(scenario())


def test_synthetic_generator_does_not_import_azure_sdk() -> None:
    generator = (
        REPOSITORY_ROOT
        / "apps/backend/src/match_intelligence/adapters/sources/synthetic.py"
    ).read_text(encoding="utf-8")

    assert "azure" not in generator.lower()


def test_example_configuration_contains_no_credentials() -> None:
    example = (REPOSITORY_ROOT / "apps/backend/.env.example").read_text(
        encoding="utf-8"
    )

    assert "EVENT_TRANSPORT=memory" in example
    assert "CONNECTION_STRING" not in example
    assert "PASSWORD" not in example
    assert "TOKEN" not in example
