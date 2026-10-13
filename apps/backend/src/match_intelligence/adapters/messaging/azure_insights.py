"""Salidas de Persona 2 en Azure Event Hubs (``match-insights``).

Publica ``AnalyticsEnvelope`` con ``match_id`` como clave de partición para
conservar el orden de cada partido. Usa ``DefaultAzureCredential``: no hay
cadenas de conexión ni claves compartidas.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from azure.eventhub import EventData
from azure.eventhub.aio import EventHubConsumerClient, EventHubProducerClient
from azure.identity.aio import DefaultAzureCredential
from pydantic import ValidationError

from match_intelligence.adapters.messaging.azure_event_hubs import (
    AsyncCredential,
    ConsumerClient,
    ProducerClient,
)
from match_intelligence.application.analytics.stream import AnalyticsEnvelope
from match_intelligence.application.transport import utc_now

Clock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class InsightPublicationReceipt:
    message_id: str
    message_type: str
    match_id: str
    duration_ms: float


@dataclass(frozen=True, slots=True)
class InsightPublicationFailure:
    message_id: str
    message_type: str
    match_id: str
    error_type: str
    message: str


class InsightPublicationError(RuntimeError):
    def __init__(self, failure: InsightPublicationFailure) -> None:
        super().__init__(
            f"No se pudo publicar {failure.message_id}: {failure.error_type}: {failure.message}"
        )
        self.failure = failure


class AzureEventHubInsightPublisher:
    def __init__(
        self,
        client: ProducerClient,
        *,
        credential: AsyncCredential | None = None,
        clock: Clock = utc_now,
    ) -> None:
        self._client = client
        self._credential = credential
        self._clock = clock
        self._receipts: list[InsightPublicationReceipt] = []
        self._failures: list[InsightPublicationFailure] = []

    @classmethod
    def from_default_credential(
        cls, *, fully_qualified_namespace: str, eventhub_name: str
    ) -> "AzureEventHubInsightPublisher":
        credential = DefaultAzureCredential()
        client = EventHubProducerClient(
            fully_qualified_namespace=fully_qualified_namespace,
            eventhub_name=eventhub_name,
            credential=credential,
        )
        return cls(client, credential=credential)

    @property
    def receipts(self) -> tuple[InsightPublicationReceipt, ...]:
        return tuple(self._receipts)

    @property
    def failures(self) -> tuple[InsightPublicationFailure, ...]:
        return tuple(self._failures)

    async def publish(self, envelope: AnalyticsEnvelope) -> None:
        started = self._clock()
        data = EventData(envelope.model_dump_json())
        data.properties = {"message_type": envelope.message_type.value}
        try:
            await self._client.send_batch([data], partition_key=envelope.correlation_id)
        except Exception as error:
            failure = InsightPublicationFailure(
                message_id=envelope.message_id,
                message_type=envelope.message_type.value,
                match_id=envelope.correlation_id,
                error_type=type(error).__name__,
                message=str(error),
            )
            self._failures.append(failure)
            raise InsightPublicationError(failure) from error
        self._receipts.append(
            InsightPublicationReceipt(
                message_id=envelope.message_id,
                message_type=envelope.message_type.value,
                match_id=envelope.correlation_id,
                duration_ms=(self._clock() - started).total_seconds() * 1_000,
            )
        )

    async def close(self) -> None:
        try:
            await self._client.close()
        finally:
            if self._credential is not None:
                await self._credential.close()


@dataclass(frozen=True, slots=True)
class ReceivedInsight:
    envelope: AnalyticsEnvelope
    received_at: datetime

    @property
    def transport_latency_ms(self) -> float:
        return (self.received_at - self.envelope.produced_at).total_seconds() * 1_000


class AzureEventHubInsightConsumer:
    """Lee ``match-insights``; lo usan Persona 3, Persona 4 y la prueba de humo."""

    def __init__(
        self,
        client: ConsumerClient,
        *,
        credential: AsyncCredential | None = None,
        clock: Clock = utc_now,
    ) -> None:
        self._client = client
        self._credential = credential
        self._clock = clock
        self._received: list[ReceivedInsight] = []
        self._rejected: list[str] = []
        self._failures: list[str] = []

    @classmethod
    def from_default_credential(
        cls, *, fully_qualified_namespace: str, eventhub_name: str, consumer_group: str
    ) -> "AzureEventHubInsightConsumer":
        credential = DefaultAzureCredential()
        client = EventHubConsumerClient(
            fully_qualified_namespace=fully_qualified_namespace,
            eventhub_name=eventhub_name,
            consumer_group=consumer_group,
            credential=credential,
        )
        return cls(client, credential=credential)

    @property
    def received(self) -> tuple[ReceivedInsight, ...]:
        return tuple(self._received)

    @property
    def rejected(self) -> tuple[str, ...]:
        return tuple(self._rejected)

    @property
    def failures(self) -> tuple[str, ...]:
        return tuple(self._failures)

    def consume_message(self, event_data: EventData) -> ReceivedInsight | None:
        try:
            envelope = AnalyticsEnvelope.model_validate_json(event_data.body_as_str(encoding="UTF-8"))
        except (ValidationError, UnicodeError, TypeError, ValueError) as error:
            self._rejected.append(f"{type(error).__name__}: {error}")
            return None
        received = ReceivedInsight(envelope=envelope, received_at=self._clock())
        self._received.append(received)
        return received

    async def _on_event(self, partition_context: object, event: EventData | None) -> None:
        if event is None:
            return
        self.consume_message(event)
        await getattr(partition_context, "update_checkpoint")(event)

    async def _on_error(self, _: object, error: Exception) -> None:
        self._failures.append(f"{type(error).__name__}: {error}")

    async def receive(
        self, *, starting_position: str = "@latest", max_wait_time: float | None = None
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
