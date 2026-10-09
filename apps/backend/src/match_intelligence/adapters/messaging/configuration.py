import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from match_intelligence.adapters.messaging.azure_event_hubs import (
    AzureEventHubConsumer,
    AzureEventHubPublisher,
    ConsumerClient,
    ProducerClient,
)
from match_intelligence.adapters.messaging.memory import (
    InMemoryEventConsumer,
    InMemoryEventPublisher,
)


class EventTransport(StrEnum):
    MEMORY = "memory"
    AZURE_EVENT_HUBS = "azure_event_hubs"


class TransportConfigurationError(ValueError):
    """Configuración ausente o incompatible con el transporte elegido."""


@dataclass(frozen=True, slots=True)
class EventTransportSettings:
    transport: EventTransport = EventTransport.MEMORY
    fully_qualified_namespace: str | None = None
    eventhub_name: str | None = None
    consumer_group: str | None = None
    producer: str = "synthetic-generator"

    @classmethod
    def from_mapping(
        cls,
        values: Mapping[str, str] = os.environ,
    ) -> "EventTransportSettings":
        raw_transport = values.get("EVENT_TRANSPORT", EventTransport.MEMORY.value)
        try:
            transport = EventTransport(raw_transport)
        except ValueError as error:
            allowed = ", ".join(item.value for item in EventTransport)
            raise TransportConfigurationError(
                f"EVENT_TRANSPORT debe ser uno de: {allowed}"
            ) from error

        settings = cls(
            transport=transport,
            fully_qualified_namespace=values.get(
                "EVENT_HUB_FULLY_QUALIFIED_NAMESPACE"
            ),
            eventhub_name=values.get("EVENT_HUB_NAME"),
            consumer_group=values.get("EVENT_HUB_CONSUMER_GROUP"),
            producer=values.get("EVENT_PRODUCER", "synthetic-generator"),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if not self.producer:
            raise TransportConfigurationError("EVENT_PRODUCER no puede estar vacío")
        if self.transport is EventTransport.MEMORY:
            return

        required = {
            "EVENT_HUB_FULLY_QUALIFIED_NAMESPACE": self.fully_qualified_namespace,
            "EVENT_HUB_NAME": self.eventhub_name,
            "EVENT_HUB_CONSUMER_GROUP": self.consumer_group,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise TransportConfigurationError(
                "Faltan variables para azure_event_hubs: " + ", ".join(missing)
            )


EventPublisherAdapter = InMemoryEventPublisher | AzureEventHubPublisher
EventConsumerAdapter = InMemoryEventConsumer | AzureEventHubConsumer


def build_event_publisher(
    settings: EventTransportSettings,
    *,
    azure_client: ProducerClient | None = None,
) -> EventPublisherAdapter:
    settings.validate()
    if settings.transport is EventTransport.MEMORY:
        return InMemoryEventPublisher()
    if azure_client is not None:
        return AzureEventHubPublisher(azure_client, producer=settings.producer)
    return AzureEventHubPublisher.from_default_credential(
        fully_qualified_namespace=_required(settings.fully_qualified_namespace),
        eventhub_name=_required(settings.eventhub_name),
        producer=settings.producer,
    )


def build_event_consumer(
    settings: EventTransportSettings,
    *,
    azure_client: ConsumerClient | None = None,
) -> EventConsumerAdapter:
    settings.validate()
    if settings.transport is EventTransport.MEMORY:
        return InMemoryEventConsumer()
    if azure_client is not None:
        return AzureEventHubConsumer(azure_client)
    return AzureEventHubConsumer.from_default_credential(
        fully_qualified_namespace=_required(settings.fully_qualified_namespace),
        eventhub_name=_required(settings.eventhub_name),
        consumer_group=_required(settings.consumer_group),
    )


def _required(value: str | None) -> str:
    # ``validate`` garantiza este caso; la función mantiene tipos concretos.
    if value is None:
        raise TransportConfigurationError("Configuración Azure incompleta")
    return value
