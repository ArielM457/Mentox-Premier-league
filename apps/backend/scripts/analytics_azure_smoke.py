"""Prueba de humo de extremo a extremo de Persona 2 en Azure.

1. Guarda un partido sintético nuevo en Blob ``matches`` (adaptador de Persona 1).
2. Publica sus eventos en ``match-events`` con un duplicado y un tardío.
3. El puente analítico los consume, reconstruye el estado y publica en
   ``match-insights``; un consumidor de diagnóstico los recibe.
4. Guarda el registro en Blob ``analytics``.
5. Compara los momentos recibidos desde Azure con el cálculo local.

Requiere los recursos de ``main.bicep`` y ``analytics.bicep`` y los roles
``Azure Event Hubs Data Owner`` y ``Storage Blob Data Contributor``::

    EVENT_HUB_FULLY_QUALIFIED_NAMESPACE=<namespace>.servicebus.windows.net
    EVENT_HUB_NAME=match-events
    EVENT_HUB_CONSUMER_GROUP=diagnostics
    INSIGHTS_EVENT_HUB_NAME=match-insights
    INSIGHTS_CONSUMER_GROUP=diagnostics
    AZURE_BLOB_SERVICE_ENDPOINT=https://<cuenta>.blob.core.windows.net
"""

import asyncio
import json
import os
from contextlib import suppress
from time import monotonic
from uuid import uuid4

from match_intelligence.adapters.messaging.analytics_bridge import EventHubAnalyticsBridge
from match_intelligence.adapters.messaging.azure_event_hubs import (
    AzureEventHubConsumer,
    AzureEventHubPublisher,
)
from match_intelligence.adapters.messaging.azure_insights import (
    AzureEventHubInsightConsumer,
    AzureEventHubInsightPublisher,
)
from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.adapters.storage.azure_analytics import (
    AzureBlobAnalyticsWriter,
    AzureBlobMatchMetadataProvider,
)
from match_intelligence.adapters.storage.azure_blob import AzureBlobArtifactStore
from match_intelligence.application.analytics.pipeline import MatchAnalytics
from match_intelligence.application.analytics.stream import (
    AnalyticsMessageType,
    AnalyticsStreamProcessor,
)
from match_intelligence.application.artifacts import Artifact, ArtifactKind, ArtifactProvenance


def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Falta la variable obligatoria {name}")
    return value


async def main() -> None:
    namespace = required("EVENT_HUB_FULLY_QUALIFIED_NAMESPACE")
    account_url = required("AZURE_BLOB_SERVICE_ENDPOINT")
    match = generate_acceptance_match(match_id=f"analytics-smoke-{uuid4()}")
    events = list(match.events)

    store = AzureBlobArtifactStore.from_default_credential(account_url=account_url)
    try:
        await store.store(Artifact(
            artifact_id="match.json",
            match_id=match.metadata.match_id,
            kind=ArtifactKind.SYNTHETIC_MATCH,
            provenance=ArtifactProvenance.SYNTHETIC,
            origin="analytics-smoke",
            content_type="application/json",
            content=json.dumps({
                "metadata": match.metadata.model_dump(mode="json"),
                "events": [event.model_dump(mode="json") for event in events],
            }, sort_keys=True).encode("utf-8"),
        ))
    finally:
        await store.close()

    event_consumer = AzureEventHubConsumer.from_default_credential(
        fully_qualified_namespace=namespace,
        eventhub_name=os.getenv("EVENT_HUB_NAME", "match-events"),
        consumer_group=os.getenv("EVENT_HUB_CONSUMER_GROUP", "diagnostics"),
    )
    insights_consumer = AzureEventHubInsightConsumer.from_default_credential(
        fully_qualified_namespace=namespace,
        eventhub_name=os.getenv("INSIGHTS_EVENT_HUB_NAME", "match-insights"),
        consumer_group=os.getenv("INSIGHTS_CONSUMER_GROUP", "diagnostics"),
    )
    event_publisher = AzureEventHubPublisher.from_default_credential(
        fully_qualified_namespace=namespace,
        eventhub_name=os.getenv("EVENT_HUB_NAME", "match-events"),
        producer="analytics-smoke",
    )
    insights_publisher = AzureEventHubInsightPublisher.from_default_credential(
        fully_qualified_namespace=namespace,
        eventhub_name=os.getenv("INSIGHTS_EVENT_HUB_NAME", "match-insights"),
    )
    metadata = AzureBlobMatchMetadataProvider.from_default_credential(account_url=account_url)
    writer = AzureBlobAnalyticsWriter.from_default_credential(account_url=account_url)
    processor = AnalyticsStreamProcessor(metadata, insights_publisher, producer="analytics-smoke")
    bridge = EventHubAnalyticsBridge(event_consumer, processor)
    tasks = [
        asyncio.create_task(event_consumer.receive(starting_position="@latest", max_wait_time=1)),
        asyncio.create_task(insights_consumer.receive(starting_position="@latest", max_wait_time=1)),
    ]
    match_id = match.metadata.match_id

    try:
        await asyncio.sleep(5)
        # evt-005 llega después de evt-007: tardío. evt-001 se repite: duplicado.
        arrival = events[:4] + events[5:7] + [events[4]] + events[7:] + [events[0]]
        for event in arrival:
            await event_publisher.publish(event)

        deadline = monotonic() + 60
        while monotonic() < deadline:
            await bridge.drain()
            proposals = [
                item for item in insights_consumer.received
                if item.envelope.correlation_id == match_id
                and item.envelope.message_type is AnalyticsMessageType.CANDIDATE_PROPOSED
            ]
            if bridge.processed >= len(events) and len(proposals) >= 2:
                break
            await asyncio.sleep(0.25)

        locations = await processor.finalize(match_id, writer, run_id=f"run-{uuid4()}")
        received = [i for i in insights_consumer.received if i.envelope.correlation_id == match_id]
        remote: dict[str, int] = {}
        for item in received:
            payload = item.envelope.payload
            if item.envelope.message_type is AnalyticsMessageType.CANDIDATE_PROPOSED:
                remote[payload["candidate_id"]] = payload["priority"]
            elif item.envelope.message_type is AnalyticsMessageType.CANDIDATE_WITHDRAWN:
                remote.pop(payload["candidate_id"], None)
        local = {c.candidate_id: c.priority for c in MatchAnalytics().candidates(match.metadata, events)}
        by_type: dict[str, int] = {}
        for item in received:
            by_type[item.envelope.message_type.value] = by_type.get(item.envelope.message_type.value, 0) + 1
        result = {
            "match_id": match_id,
            "published_events": len(arrival),
            "accepted_events": len(event_consumer.accepted),
            "duplicates": len(event_consumer.duplicates),
            "late_event_ids": list(processor.engine(match_id).late_event_ids) if processor.engine(match_id) else [],
            "insights_by_type": by_type,
            "remote_candidates": remote,
            "local_candidates": local,
            "matches_local": remote == local,
            "insight_transport_ms": [round(i.transport_latency_ms, 1) for i in received],
            "stored": locations,
            "failures": list(insights_consumer.failures) + [f.message for f in event_consumer.failures],
        }
        print(json.dumps(result, indent=2))
        if not result["matches_local"]:
            raise RuntimeError("Los momentos recibidos desde Azure no coinciden con el cálculo local")
    finally:
        for task in tasks:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        await event_consumer.close()
        await insights_consumer.close()
        await event_publisher.close()
        await insights_publisher.close()
        await metadata.close()
        await writer.close()


if __name__ == "__main__":
    asyncio.run(main())
