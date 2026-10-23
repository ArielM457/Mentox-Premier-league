"""Prueba real de productor y consumidor de vision-observations."""

import asyncio
from contextlib import suppress
from datetime import UTC, datetime
import json
import os
from time import monotonic
from uuid import uuid4

from match_intelligence.adapters.messaging.azure_vision_observations import (
    VisionObservationConsumer,
    VisionObservationPublisher,
)
from match_intelligence.application.realtime_observations import (
    LiveObservation,
    RealtimeObservationHub,
)


def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Falta la variable {name}")
    return value


async def main() -> None:
    namespace = required("EVENT_HUB_FULLY_QUALIFIED_NAMESPACE")
    eventhub_name = os.getenv("VISION_EVENT_HUB_NAME", "vision-observations")
    consumer_group = os.getenv("VISION_EVENT_HUB_CONSUMER_GROUP", "diagnostics")
    hub = RealtimeObservationHub()
    publisher = VisionObservationPublisher.from_default_credential(
        fully_qualified_namespace=namespace,
        eventhub_name=eventhub_name,
    )
    consumer = VisionObservationConsumer.from_default_credential(
        fully_qualified_namespace=namespace,
        eventhub_name=eventhub_name,
        consumer_group=consumer_group,
        handler=hub.publish,
    )
    observation = LiveObservation(
        observation_id=f"vision-smoke-{uuid4()}",
        source="roboflow",
        kind="spatial_detection",
        timestamp_ms=1_000,
        payload={
            "label": "ball",
            "confidence": 0.91,
            "track_id": 1,
            "player_id": None,
            "prediction_origin": "smoke_test",
        },
        received_at=datetime.now(UTC),
    )
    receive_task = asyncio.create_task(consumer.receive())
    try:
        await asyncio.sleep(5)
        await publisher.publish(observation)
        await publisher.publish(observation)
        deadline = monotonic() + 30
        while monotonic() < deadline:
            if hub.accepted == 1 and hub.duplicates == 1:
                break
            await asyncio.sleep(0.25)
        result = {
            "eventhub_name": eventhub_name,
            "published": publisher.published,
            "publication_failures": publisher.failures,
            "accepted": hub.accepted,
            "duplicates": hub.duplicates,
            "rejected": consumer.rejected,
            "consumer_failures": consumer.failures,
            "match_events_created": 0,
        }
        print(json.dumps(result, indent=2))
        if result["accepted"] != 1 or result["duplicates"] != 1:
            raise RuntimeError("No se obtuvo un aceptado y un duplicado")
    finally:
        receive_task.cancel()
        with suppress(asyncio.CancelledError):
            await receive_task
        await publisher.close()
        await consumer.close()


if __name__ == "__main__":
    asyncio.run(main())
