"""Transporte Azure separado para observaciones que aún no son MatchEvent."""

from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable
from datetime import UTC, datetime
from typing import Protocol

from azure.eventhub import EventData
from azure.eventhub.aio import EventHubConsumerClient, EventHubProducerClient
from azure.identity.aio import DefaultAzureCredential
from pydantic import ValidationError

from match_intelligence.application.realtime_observations import (
    LiveObservation,
    VisionObservationEnvelope,
)


class AsyncCredential(Protocol):
    async def close(self) -> None: ...


class VisionObservationPublisher:
    def __init__(
        self,
        client: object,
        *,
        credential: AsyncCredential | None = None,
    ) -> None:
        self._client = client
        self._credential = credential
        self.published = 0
        self.failures = 0

    @classmethod
    def from_default_credential(
        cls, *, fully_qualified_namespace: str, eventhub_name: str
    ) -> "VisionObservationPublisher":
        credential = DefaultAzureCredential()
        client = EventHubProducerClient(
            fully_qualified_namespace=fully_qualified_namespace,
            eventhub_name=eventhub_name,
            credential=credential,
        )
        return cls(client, credential=credential)

    async def publish(self, observation: LiveObservation) -> None:
        event = self._event_data(observation)
        try:
            await self._client.send_batch([event], partition_key=observation.source)
        except Exception:
            self.failures += 1
            raise
        self.published += 1

    @staticmethod
    def _event_data(observation: LiveObservation) -> EventData:
        envelope = VisionObservationEnvelope(
            observation_id=observation.observation_id,
            source=observation.source,
            kind=observation.kind,
            timestamp_ms=observation.timestamp_ms,
            payload=observation.payload,
            produced_at=datetime.now(UTC),
        )
        return EventData(envelope.model_dump_json())

    async def publish_many(
        self,
        observations: Iterable[LiveObservation],
        *,
        chunk_size: int = 100,
    ) -> None:
        grouped: dict[str, list[LiveObservation]] = defaultdict(list)
        for observation in observations:
            grouped[observation.source].append(observation)
        for source, items in grouped.items():
            for offset in range(0, len(items), chunk_size):
                chunk = items[offset : offset + chunk_size]
                try:
                    await self._client.send_batch(
                        [self._event_data(item) for item in chunk],
                        partition_key=source,
                    )
                except Exception:
                    self.failures += len(chunk)
                    raise
                self.published += len(chunk)

    async def close(self) -> None:
        try:
            await self._client.close()
        finally:
            if self._credential is not None:
                await self._credential.close()


class VisionObservationConsumer:
    def __init__(
        self,
        client: object,
        handler: Callable[[LiveObservation], Awaitable[bool]],
        *,
        credential: AsyncCredential | None = None,
    ) -> None:
        self._client = client
        self._handler = handler
        self._credential = credential
        self.accepted = 0
        self.rejected = 0
        self.failures = 0

    @classmethod
    def from_default_credential(
        cls,
        *,
        fully_qualified_namespace: str,
        eventhub_name: str,
        consumer_group: str,
        handler: Callable[[LiveObservation], Awaitable[bool]],
    ) -> "VisionObservationConsumer":
        credential = DefaultAzureCredential()
        client = EventHubConsumerClient(
            fully_qualified_namespace=fully_qualified_namespace,
            eventhub_name=eventhub_name,
            consumer_group=consumer_group,
            credential=credential,
        )
        return cls(client, handler, credential=credential)

    async def consume_message(self, event: EventData) -> bool:
        try:
            envelope = VisionObservationEnvelope.model_validate_json(
                event.body_as_str(encoding="UTF-8")
            )
        except (ValidationError, UnicodeError, TypeError, ValueError):
            self.rejected += 1
            return False
        accepted = await self._handler(
            LiveObservation(
                observation_id=envelope.observation_id,
                source=envelope.source,
                kind=envelope.kind,
                timestamp_ms=envelope.timestamp_ms,
                payload=envelope.payload,
                received_at=datetime.now(UTC),
            )
        )
        self.accepted += int(accepted)
        return accepted

    async def _on_event(self, partition_context: object, event: EventData | None) -> None:
        if event is None:
            return
        await self.consume_message(event)
        await getattr(partition_context, "update_checkpoint")(event)

    async def _on_error(self, _: object, __: Exception) -> None:
        self.failures += 1

    async def receive(self) -> None:
        await self._client.receive(
            on_event=self._on_event,
            on_error=self._on_error,
            starting_position="@latest",
        )

    async def close(self) -> None:
        try:
            await self._client.close()
        finally:
            if self._credential is not None:
                await self._credential.close()
