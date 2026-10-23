"""Selecciona transporte local o Azure para el canal continuo de visión."""

import asyncio
from contextlib import suppress
from dataclasses import dataclass
import os

from match_intelligence.adapters.messaging.azure_vision_observations import (
    VisionObservationConsumer,
    VisionObservationPublisher,
)
from match_intelligence.application.realtime_observations import (
    LiveObservation,
    RealtimeObservationHub,
)


class VisionRuntimeConfigurationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class VisionRuntimeSettings:
    transport: str = "memory"
    namespace: str | None = None
    eventhub_name: str = "vision-observations"
    consumer_group: str = "backend"

    @classmethod
    def from_environment(cls) -> "VisionRuntimeSettings":
        settings = cls(
            transport=os.getenv("VISION_OBSERVATION_TRANSPORT", "memory"),
            namespace=os.getenv("EVENT_HUB_FULLY_QUALIFIED_NAMESPACE"),
            eventhub_name=os.getenv("VISION_EVENT_HUB_NAME", "vision-observations"),
            consumer_group=os.getenv("VISION_EVENT_HUB_CONSUMER_GROUP", "backend"),
        )
        if settings.transport not in {"memory", "azure_event_hubs"}:
            raise VisionRuntimeConfigurationError(
                "VISION_OBSERVATION_TRANSPORT debe ser memory o azure_event_hubs"
            )
        if settings.transport == "azure_event_hubs" and not settings.namespace:
            raise VisionRuntimeConfigurationError(
                "EVENT_HUB_FULLY_QUALIFIED_NAMESPACE es obligatorio para Azure"
            )
        return settings


class VisionObservationRuntime:
    def __init__(self, hub: RealtimeObservationHub, settings: VisionRuntimeSettings) -> None:
        self.hub = hub
        self.settings = settings
        self.publisher: VisionObservationPublisher | None = None
        self.consumer: VisionObservationConsumer | None = None
        self._consumer_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self.settings.transport == "memory":
            return
        assert self.settings.namespace is not None
        self.publisher = VisionObservationPublisher.from_default_credential(
            fully_qualified_namespace=self.settings.namespace,
            eventhub_name=self.settings.eventhub_name,
        )
        self.consumer = VisionObservationConsumer.from_default_credential(
            fully_qualified_namespace=self.settings.namespace,
            eventhub_name=self.settings.eventhub_name,
            consumer_group=self.settings.consumer_group,
            handler=self.hub.publish,
        )
        self._consumer_task = asyncio.create_task(self.consumer.receive())

    async def publish(self, observation: LiveObservation) -> bool:
        if self.settings.transport == "memory":
            return await self.hub.publish(observation)
        if self.publisher is None:
            raise RuntimeError("El transporte Azure no fue iniciado")
        await self.publisher.publish(observation)
        return True

    async def publish_many(
        self, observations: tuple[LiveObservation, ...]
    ) -> int:
        if not observations:
            return 0
        if self.settings.transport == "memory":
            accepted = 0
            for observation in observations:
                accepted += int(await self.hub.publish(observation))
            return accepted
        if self.publisher is None:
            raise RuntimeError("El transporte Azure no fue iniciado")
        await self.publisher.publish_many(observations)
        return len(observations)

    async def close(self) -> None:
        if self._consumer_task is not None:
            self._consumer_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._consumer_task
        if self.publisher is not None:
            await self.publisher.close()
        if self.consumer is not None:
            await self.consumer.close()

    def status(self) -> dict[str, object]:
        return {
            "transport": self.settings.transport,
            "eventhub_name": self.settings.eventhub_name,
            "consumer_group": self.settings.consumer_group,
            "producer_published": self.publisher.published if self.publisher else 0,
            "producer_failures": self.publisher.failures if self.publisher else 0,
            "consumer_accepted": self.consumer.accepted if self.consumer else 0,
            "consumer_rejected": self.consumer.rejected if self.consumer else 0,
            "consumer_failures": self.consumer.failures if self.consumer else 0,
        }
