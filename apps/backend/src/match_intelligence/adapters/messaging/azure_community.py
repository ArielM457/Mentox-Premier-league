"""Bus de la comunidad sobre Azure Event Hubs.

Cada voto o mensaje se envía al Event Hub ``community-events`` con el tema
(``community/{match}/{draft}``) como clave de partición, así se conserva el
orden dentro de cada resumen. Cada réplica de la API lee el hub desde el
último evento, sin puntos de control, y reparte lo que llega a sus propias
conexiones SSE con el bus en memoria. Así varias réplicas comparten el
mismo chat en vivo.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
from collections.abc import AsyncIterator
from typing import Any, Protocol

from azure.eventhub import EventData
from azure.eventhub.aio import EventHubConsumerClient, EventHubProducerClient
from azure.identity.aio import DefaultAzureCredential

from match_intelligence.application.community import InMemoryMessageBus, MessageBus

logger = logging.getLogger(__name__)

OUTBOX_SIZE = 1000


class ProducerClient(Protocol):
    async def send_batch(self, event_data_batch: list[EventData], *, partition_key: str | None = None) -> None: ...

    async def close(self) -> None: ...


class ConsumerClient(Protocol):
    async def receive(self, on_event: Any, **kwargs: Any) -> None: ...

    async def close(self) -> None: ...


class AzureEventHubsMessageBus:
    """Publica en Event Hubs y entrega a los suscriptores locales lo que recibe."""

    def __init__(
        self,
        producer: ProducerClient,
        consumer: ConsumerClient,
        *,
        credential: Any | None = None,
        local: InMemoryMessageBus | None = None,
    ) -> None:
        self._producer = producer
        self._consumer = consumer
        self._credential = credential
        self._local = local or InMemoryMessageBus()
        self._outbox: asyncio.Queue[tuple[str, dict]] = asyncio.Queue(maxsize=OUTBOX_SIZE)
        self._tasks: list[asyncio.Task] = []
        self.counts = {"sent": 0, "received": 0, "fallback": 0}

    @classmethod
    def from_environment(cls) -> "AzureEventHubsMessageBus":
        namespace = os.environ["EVENT_HUB_FULLY_QUALIFIED_NAMESPACE"]
        hub = os.getenv("COMMUNITY_EVENT_HUB_NAME", "community-events")
        credential = DefaultAzureCredential()
        producer = EventHubProducerClient(
            fully_qualified_namespace=namespace,
            eventhub_name=hub,
            credential=credential,
        )
        consumer = EventHubConsumerClient(
            fully_qualified_namespace=namespace,
            eventhub_name=hub,
            consumer_group=os.getenv("COMMUNITY_EVENT_HUB_CONSUMER_GROUP", "$Default"),
            credential=credential,
        )
        return cls(producer, consumer, credential=credential)

    def subscribers(self, topic: str) -> int:
        return self._local.subscribers(topic)

    def publish(self, topic: str, event: dict) -> None:
        # Las rutas son síncronas: el envío real lo hace la tarea de fondo.
        if not self._tasks:
            self._local.publish(topic, event)
            self.counts["fallback"] += 1
            return
        try:
            self._outbox.put_nowait((topic, event))
        except asyncio.QueueFull:
            self._local.publish(topic, event)
            self.counts["fallback"] += 1

    def subscribe(self, topic: str) -> AsyncIterator[dict]:
        return self._local.subscribe(topic)

    async def start(self) -> None:
        if self._tasks:
            return
        self._tasks = [
            asyncio.create_task(self._send_loop(), name="community-send"),
            asyncio.create_task(self._receive_loop(), name="community-receive"),
        ]

    async def close(self) -> None:
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._tasks = []
        await self._producer.close()
        await self._consumer.close()
        if self._credential is not None:
            await self._credential.close()

    async def _send_loop(self) -> None:
        while True:
            topic, event = await self._outbox.get()
            body = json.dumps({"topic": topic, "event": event}, ensure_ascii=False, separators=(",", ":"))
            try:
                await self._producer.send_batch([EventData(body)], partition_key=topic)
                self.counts["sent"] += 1
            except Exception:
                # Si Azure falla, al menos esta réplica sigue viendo el cambio.
                logger.exception("No se pudo enviar el evento de la comunidad a Event Hubs")
                self._local.publish(topic, event)
                self.counts["fallback"] += 1

    async def _receive_loop(self) -> None:
        await self._consumer.receive(on_event=self._on_event, starting_position="@latest")

    async def _on_event(self, _partition: Any, event: EventData | None) -> None:
        if event is None:
            return
        try:
            data = json.loads(event.body_as_str())
            topic, payload = data["topic"], data["event"]
        except (ValueError, KeyError, TypeError):
            logger.warning("Evento de la comunidad inválido; se ignora")
            return
        self.counts["received"] += 1
        self._local.publish(topic, payload)


def build_community_bus() -> MessageBus:
    mode = os.getenv("COMMUNITY_TRANSPORT", "memory").strip().lower()
    if mode == "memory":
        return InMemoryMessageBus()
    if mode == "azure_event_hubs":
        return AzureEventHubsMessageBus.from_environment()
    raise ValueError("COMMUNITY_TRANSPORT debe ser 'memory' o 'azure_event_hubs'")
