from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from azure.eventhub import EventData
from azure.eventhub.aio import EventHubConsumerClient, EventHubProducerClient
from azure.identity.aio import DefaultAzureCredential
from pydantic import ValidationError

from match_intelligence.application.deduplication import (
    DuplicateEvent,
    EventDeduplicator,
)
from match_intelligence.application.transport import (
    Clock,
    MatchEventEnvelope,
    MessageIdFactory,
    create_match_event_envelope,
    new_message_id,
    utc_now,
)
from match_intelligence.domain.contracts import MatchEvent


class AsyncCredential(Protocol):
    async def close(self) -> None: ...


class ProducerClient(Protocol):
    async def send_batch(
        self,
        event_data_batch: list[EventData],
        *,
        partition_key: str | None = None,
    ) -> None: ...

    async def close(self) -> None: ...


class ConsumerClient(Protocol):
    async def receive(self, on_event: object, **kwargs: object) -> None: ...

    async def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class PublicationReceipt:
    message_id: str
    event_id: str
    match_id: str
    produced_at: datetime
    publication_started_at: datetime
    published_at: datetime

    @property
    def publication_duration_ms(self) -> float:
        delta = self.published_at - self.publication_started_at
        return delta.total_seconds() * 1_000


@dataclass(frozen=True, slots=True)
class PublicationFailure:
    message_id: str
    event_id: str
    match_id: str
    produced_at: datetime
    publication_started_at: datetime
    failed_at: datetime
    error_type: str
    message: str


class EventPublicationError(RuntimeError):
    """Error observable que conserva el diagnóstico del intento fallido."""

    def __init__(self, failure: PublicationFailure) -> None:
        super().__init__(
            f"No se pudo publicar {failure.message_id}: "
            f"{failure.error_type}: {failure.message}"
        )
        self.failure = failure


class AzureEventHubPublisher:
    """Publica sobres de MatchEvent mediante el cliente asíncrono de Azure."""

    def __init__(
        self,
        client: ProducerClient,
        *,
        producer: str = "synthetic-generator",
        credential: AsyncCredential | None = None,
        clock: Clock = utc_now,
        message_id_factory: MessageIdFactory = new_message_id,
    ) -> None:
        self._client = client
        self._credential = credential
        self._producer = producer
        self._clock = clock
        self._message_id_factory = message_id_factory
        self._receipts: list[PublicationReceipt] = []
        self._failures: list[PublicationFailure] = []

    @classmethod
    def from_default_credential(
        cls,
        *,
        fully_qualified_namespace: str,
        eventhub_name: str,
        producer: str = "synthetic-generator",
    ) -> "AzureEventHubPublisher":
        credential = DefaultAzureCredential()
        client = EventHubProducerClient(
            fully_qualified_namespace=fully_qualified_namespace,
            eventhub_name=eventhub_name,
            credential=credential,
        )
        return cls(client, producer=producer, credential=credential)

    @property
    def receipts(self) -> tuple[PublicationReceipt, ...]:
        return tuple(self._receipts)

    @property
    def failures(self) -> tuple[PublicationFailure, ...]:
        return tuple(self._failures)

    async def publish(self, event: MatchEvent) -> None:
        envelope = create_match_event_envelope(
            event,
            producer=self._producer,
            clock=self._clock,
            message_id_factory=self._message_id_factory,
        )
        started_at = self._clock()
        transport_event = EventData(envelope.model_dump_json())

        try:
            await self._client.send_batch(
                [transport_event],
                partition_key=event.match_id,
            )
        except Exception as error:
            failure = PublicationFailure(
                message_id=envelope.message_id,
                event_id=event.event_id,
                match_id=event.match_id,
                produced_at=envelope.produced_at,
                publication_started_at=started_at,
                failed_at=self._clock(),
                error_type=type(error).__name__,
                message=str(error),
            )
            self._failures.append(failure)
            raise EventPublicationError(failure) from error

        self._receipts.append(
            PublicationReceipt(
                message_id=envelope.message_id,
                event_id=event.event_id,
                match_id=event.match_id,
                produced_at=envelope.produced_at,
                publication_started_at=started_at,
                published_at=self._clock(),
            )
        )

    async def close(self) -> None:
        try:
            await self._client.close()
        finally:
            if self._credential is not None:
                await self._credential.close()


@dataclass(frozen=True, slots=True)
class ReceivedMatchEvent:
    message_id: str
    event: MatchEvent
    produced_at: datetime
    received_at: datetime

    @property
    def transport_latency_ms(self) -> float:
        delta = self.received_at - self.produced_at
        return delta.total_seconds() * 1_000


@dataclass(frozen=True, slots=True)
class RejectedTransportMessage:
    arrival_sequence: int
    received_at: datetime
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class DuplicateTransportMessage:
    message_id: str
    received_at: datetime
    duplicate: DuplicateEvent


@dataclass(frozen=True, slots=True)
class ConsumerFailure:
    occurred_at: datetime
    error_type: str
    message: str


class AzureEventHubConsumer:
    """Valida, deduplica y registra mensajes recibidos desde Event Hubs."""

    def __init__(
        self,
        client: ConsumerClient,
        *,
        credential: AsyncCredential | None = None,
        deduplicator: EventDeduplicator | None = None,
        clock: Clock = utc_now,
    ) -> None:
        self._client = client
        self._credential = credential
        self._deduplicator = deduplicator or EventDeduplicator()
        self._clock = clock
        self._accepted: list[ReceivedMatchEvent] = []
        self._rejected: list[RejectedTransportMessage] = []
        self._duplicates: list[DuplicateTransportMessage] = []
        self._failures: list[ConsumerFailure] = []
        self._arrival_sequence = 0

    @classmethod
    def from_default_credential(
        cls,
        *,
        fully_qualified_namespace: str,
        eventhub_name: str,
        consumer_group: str,
    ) -> "AzureEventHubConsumer":
        credential = DefaultAzureCredential()
        client = EventHubConsumerClient(
            fully_qualified_namespace=fully_qualified_namespace,
            eventhub_name=eventhub_name,
            consumer_group=consumer_group,
            credential=credential,
        )
        return cls(client, credential=credential)

    @property
    def accepted(self) -> tuple[ReceivedMatchEvent, ...]:
        return tuple(self._accepted)

    @property
    def events(self) -> tuple[MatchEvent, ...]:
        """Eventos deportivos aceptados, equivalentes a los del modo local."""
        return tuple(received.event for received in self._accepted)

    @property
    def rejected(self) -> tuple[RejectedTransportMessage, ...]:
        return tuple(self._rejected)

    @property
    def duplicates(self) -> tuple[DuplicateTransportMessage, ...]:
        return tuple(self._duplicates)

    @property
    def failures(self) -> tuple[ConsumerFailure, ...]:
        return tuple(self._failures)

    def consume_message(
        self,
        event_data: EventData,
        *,
        received_at: datetime | None = None,
    ) -> ReceivedMatchEvent | None:
        received_at = received_at or self._clock()
        arrival_sequence = self._arrival_sequence
        self._arrival_sequence += 1

        try:
            envelope = MatchEventEnvelope.model_validate_json(
                event_data.body_as_str(encoding="UTF-8")
            )
        except (ValidationError, UnicodeError, TypeError, ValueError) as error:
            self._rejected.append(
                RejectedTransportMessage(
                    arrival_sequence=arrival_sequence,
                    received_at=received_at,
                    code=type(error).__name__,
                    message=str(error),
                )
            )
            return None

        report = self._deduplicator.process((envelope.payload,))
        if report.duplicates:
            self._duplicates.append(
                DuplicateTransportMessage(
                    message_id=envelope.message_id,
                    received_at=received_at,
                    duplicate=report.duplicates[0],
                )
            )
            return None

        received = ReceivedMatchEvent(
            message_id=envelope.message_id,
            event=report.accepted[0],
            produced_at=envelope.produced_at,
            received_at=received_at,
        )
        self._accepted.append(received)
        return received

    async def _on_event(self, partition_context: object, event: EventData | None) -> None:
        if event is None:
            return
        self.consume_message(event)
        update_checkpoint = getattr(partition_context, "update_checkpoint")
        await update_checkpoint(event)

    async def _on_error(self, _: object, error: Exception) -> None:
        self._failures.append(
            ConsumerFailure(
                occurred_at=self._clock(),
                error_type=type(error).__name__,
                message=str(error),
            )
        )

    async def receive(
        self,
        *,
        starting_position: str = "@latest",
        max_wait_time: float | None = None,
    ) -> None:
        await self._client.receive(
            on_event=self._on_event,
            on_error=self._on_error,
            starting_position=starting_position,
            max_wait_time=max_wait_time,
        )

    async def close(self) -> None:
        try:
            await self._client.close()
        finally:
            if self._credential is not None:
                await self._credential.close()
