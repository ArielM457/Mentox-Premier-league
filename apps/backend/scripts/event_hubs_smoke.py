"""Prueba manual de ida y vuelta para DV-US-07.

Requiere recursos desplegados, roles RBAC y las tres variables descritas en
``infra/azure/README.md``. No usa cadenas de conexión.
"""

import asyncio
import json
import os
from contextlib import suppress
from time import monotonic
from uuid import uuid4

from match_intelligence.adapters.messaging.azure_event_hubs import (
    AzureEventHubConsumer,
    AzureEventHubPublisher,
)
from match_intelligence.adapters.sources.synthetic import generate_acceptance_match


def required_setting(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Falta la variable obligatoria {name}")
    return value


async def main() -> None:
    namespace = required_setting("EVENT_HUB_FULLY_QUALIFIED_NAMESPACE")
    eventhub_name = required_setting("EVENT_HUB_NAME")
    consumer_group = required_setting("EVENT_HUB_CONSUMER_GROUP")
    match = generate_acceptance_match(match_id=f"azure-smoke-{uuid4()}")
    event = match.events[0]
    publisher = AzureEventHubPublisher.from_default_credential(
        fully_qualified_namespace=namespace,
        eventhub_name=eventhub_name,
        producer="dv-us-07-smoke",
    )
    consumer = AzureEventHubConsumer.from_default_credential(
        fully_qualified_namespace=namespace,
        eventhub_name=eventhub_name,
        consumer_group=consumer_group,
    )
    receive_task = asyncio.create_task(
        consumer.receive(starting_position="@latest", max_wait_time=1)
    )

    try:
        # Da tiempo al consumidor para reclamar las particiones antes de publicar.
        await asyncio.sleep(5)
        await publisher.publish(event)
        await publisher.publish(event)

        deadline = monotonic() + 30
        while monotonic() < deadline:
            if len(consumer.accepted) == 1 and len(consumer.duplicates) == 1:
                break
            if consumer.failures:
                break
            await asyncio.sleep(0.25)

        result = {
            "match_id": event.match_id,
            "event_id": event.event_id,
            "published": len(publisher.receipts),
            "publication_failures": len(publisher.failures),
            "accepted": len(consumer.accepted),
            "duplicates": len(consumer.duplicates),
            "rejected": len(consumer.rejected),
            "consumer_failures": len(consumer.failures),
            "publication_duration_ms": [
                receipt.publication_duration_ms for receipt in publisher.receipts
            ],
            "transport_latency_ms": [
                received.transport_latency_ms for received in consumer.accepted
            ],
        }
        print(json.dumps(result, indent=2))

        if result["accepted"] != 1 or result["duplicates"] != 1:
            raise RuntimeError("La prueba no recibió un aceptado y un duplicado")
    finally:
        receive_task.cancel()
        with suppress(asyncio.CancelledError):
            await receive_task
        await publisher.close()
        await consumer.close()


if __name__ == "__main__":
    asyncio.run(main())
