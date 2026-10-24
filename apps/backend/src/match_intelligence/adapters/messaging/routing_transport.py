"""Transportes configurables para ingreso, métricas e importantes."""

from __future__ import annotations

import json
import os
from typing import Any, Protocol

from azure.eventhub import EventData
from azure.eventhub.aio import EventHubProducerClient
from azure.identity.aio import DefaultAzureCredential
from azure.servicebus import ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient

from match_intelligence.application.routing.pipeline import MemoryRoutingTransport


class EventHubProducer(Protocol):
    async def send_batch(self, events: list[EventData], *, partition_key: str) -> None: ...
    async def close(self) -> None: ...


class ServiceBusSender(Protocol):
    async def send_messages(self, message: ServiceBusMessage) -> None: ...
    async def close(self) -> None: ...


class AzureRoutingTransport:
    def __init__(
        self,
        ingress: EventHubProducer,
        metrics: EventHubProducer,
        important: ServiceBusSender,
        *,
        credential: Any | None = None,
        service_bus_client: Any | None = None,
    ) -> None:
        self._ingress = ingress
        self._metrics = metrics
        self._important = important
        self._credential = credential
        self._service_bus_client = service_bus_client
        self._counts = {"ingress": 0, "metrics": 0, "important": 0}

    @classmethod
    def from_environment(cls) -> "AzureRoutingTransport":
        event_namespace = os.environ["EVENT_HUB_FULLY_QUALIFIED_NAMESPACE"]
        service_namespace = os.environ["SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE"]
        credential = DefaultAzureCredential()
        ingress = EventHubProducerClient(
            fully_qualified_namespace=event_namespace,
            eventhub_name=os.getenv("EVENT_HUB_NAME", "match-events"),
            credential=credential,
        )
        metrics = EventHubProducerClient(
            fully_qualified_namespace=event_namespace,
            eventhub_name=os.getenv("METRICS_EVENT_HUB_NAME", "match-metrics"),
            credential=credential,
        )
        service_bus_client = ServiceBusClient(
            fully_qualified_namespace=service_namespace,
            credential=credential,
        )
        important = service_bus_client.get_queue_sender(
            queue_name=os.getenv("IMPORTANT_EVENTS_QUEUE_NAME", "important-events")
        )
        return cls(
            ingress,
            metrics,
            important,
            credential=credential,
            service_bus_client=service_bus_client,
        )

    @staticmethod
    def _body(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    async def publish_ingress(self, payload: dict[str, Any], *, partition_key: str) -> None:
        await self._ingress.send_batch([EventData(self._body(payload))], partition_key=partition_key)
        self._counts["ingress"] += 1

    async def publish_metrics(self, payload: dict[str, Any], *, partition_key: str) -> None:
        await self._metrics.send_batch([EventData(self._body(payload))], partition_key=partition_key)
        self._counts["metrics"] += 1

    async def publish_important(self, payload: dict[str, Any], *, message_id: str) -> None:
        message = ServiceBusMessage(
            self._body(payload),
            message_id=message_id,
            application_properties={"contract": "RoutingOutcome", "version": "1"},
        )
        await self._important.send_messages(message)
        self._counts["important"] += 1

    def status(self) -> dict[str, Any]:
        return {
            "transport": "azure",
            "ingress_published": self._counts["ingress"],
            "metrics_published": self._counts["metrics"],
            "important_published": self._counts["important"],
        }

    async def close(self) -> None:
        await self._ingress.close()
        await self._metrics.close()
        await self._important.close()
        if self._service_bus_client is not None:
            await self._service_bus_client.close()
        if self._credential is not None:
            await self._credential.close()


def build_routing_transport() -> MemoryRoutingTransport | AzureRoutingTransport:
    mode = os.getenv("ROUTING_TRANSPORT", "memory").strip().lower()
    if mode == "memory":
        return MemoryRoutingTransport()
    if mode == "azure":
        return AzureRoutingTransport.from_environment()
    raise ValueError("ROUTING_TRANSPORT debe ser 'memory' o 'azure'")
