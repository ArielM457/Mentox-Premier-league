"""Procesador analítico continuo sobre Azure (Persona 2).

Lee ``match-events`` con el grupo ``backend``, calcula estado y momentos y
publica en ``match-insights``. Cuando un partido deja de recibir eventos
durante ``ANALYTICS_IDLE_SECONDS``, guarda su registro en el contenedor
``analytics``. Variables (sin secretos)::

    EVENT_HUB_FULLY_QUALIFIED_NAMESPACE=<namespace>.servicebus.windows.net
    EVENT_HUB_NAME=match-events
    EVENT_HUB_CONSUMER_GROUP=backend
    INSIGHTS_EVENT_HUB_NAME=match-insights
    AZURE_BLOB_SERVICE_ENDPOINT=https://<cuenta>.blob.core.windows.net
    ANALYTICS_IDLE_SECONDS=30          # opcional
    ANALYTICS_RUN_SECONDS=0            # opcional; 0 = sin límite
    VALUE_MODELS_SOURCE=none           # none | blob

Desde la raíz del repositorio::

    python apps/backend/scripts/analytics_stream_worker.py
"""

import asyncio
import json
import os
from contextlib import suppress
from time import monotonic
from uuid import uuid4

from match_intelligence.adapters.messaging.analytics_bridge import EventHubAnalyticsBridge
from match_intelligence.adapters.messaging.azure_event_hubs import AzureEventHubConsumer
from match_intelligence.adapters.messaging.azure_insights import AzureEventHubInsightPublisher
from match_intelligence.adapters.models.loader import registry_from_blob
from match_intelligence.adapters.storage.azure_analytics import (
    AzureBlobAnalyticsWriter,
    AzureBlobMatchMetadataProvider,
)
from match_intelligence.application.analytics.stream import AnalyticsStreamProcessor
from match_intelligence.application.analytics.value_models import ValueModelRegistry


def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Falta la variable obligatoria {name}")
    return value


async def main() -> None:
    namespace = required("EVENT_HUB_FULLY_QUALIFIED_NAMESPACE")
    account_url = required("AZURE_BLOB_SERVICE_ENDPOINT")
    idle_seconds = float(os.getenv("ANALYTICS_IDLE_SECONDS", "30"))
    run_seconds = float(os.getenv("ANALYTICS_RUN_SECONDS", "0"))
    value_models = (
        await registry_from_blob(account_url)
        if os.getenv("VALUE_MODELS_SOURCE", "none") == "blob"
        else ValueModelRegistry()
    )

    consumer = AzureEventHubConsumer.from_default_credential(
        fully_qualified_namespace=namespace,
        eventhub_name=os.getenv("EVENT_HUB_NAME", "match-events"),
        consumer_group=os.getenv("EVENT_HUB_CONSUMER_GROUP", "backend"),
    )
    publisher = AzureEventHubInsightPublisher.from_default_credential(
        fully_qualified_namespace=namespace,
        eventhub_name=os.getenv("INSIGHTS_EVENT_HUB_NAME", "match-insights"),
    )
    metadata = AzureBlobMatchMetadataProvider.from_default_credential(account_url=account_url)
    writer = AzureBlobAnalyticsWriter.from_default_credential(account_url=account_url)
    processor = AnalyticsStreamProcessor(metadata, publisher, value_models=value_models)
    bridge = EventHubAnalyticsBridge(consumer, processor)
    receive_task = asyncio.create_task(consumer.receive(starting_position="@latest", max_wait_time=1))

    started = monotonic()
    last_seen: dict[str, float] = {}
    try:
        while not run_seconds or monotonic() - started < run_seconds:
            for step in await bridge.drain():
                last_seen[step.result.match_id] = monotonic()
                print(json.dumps({
                    "match_id": step.result.match_id,
                    "event_id": step.result.event_id,
                    "arrival": step.arrival_status,
                    "outcome": step.result.outcome,
                    "published": [item.value for item in step.result.published],
                    "transport_ms": round(step.received.transport_latency_ms, 1),
                    "processing_ms": round(step.result.processing_ms, 2),
                }))
            for match_id, seen in list(last_seen.items()):
                if monotonic() - seen >= idle_seconds:
                    locations = await processor.finalize(match_id, writer, run_id=f"run-{uuid4()}")
                    print(json.dumps({"match_id": match_id, "stored": locations}))
                    del last_seen[match_id]
            await asyncio.sleep(0.2)
    finally:
        receive_task.cancel()
        with suppress(asyncio.CancelledError):
            await receive_task
        await consumer.close()
        await publisher.close()
        await metadata.close()
        await writer.close()


if __name__ == "__main__":
    asyncio.run(main())
