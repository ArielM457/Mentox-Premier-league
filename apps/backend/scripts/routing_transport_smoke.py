"""Publica una ruta de métricas y otra durable en la topología Azure real."""

from __future__ import annotations

import asyncio
import json
import os
from uuid import uuid4

from azure.identity.aio import DefaultAzureCredential
from azure.servicebus.aio import ServiceBusClient

from match_intelligence.adapters.messaging.routing_transport import AzureRoutingTransport
from match_intelligence.application.routing import RoutedEventPipeline, RoutingEvaluationRequest


def _request(match_id: str, *, event_type: str, outcome: str) -> RoutingEvaluationRequest:
    return RoutingEvaluationRequest.model_validate(
        {
            "match_id": match_id,
            "events": [
                {
                    "schema_version": "1.0",
                    "event_id": f"evt-{uuid4()}",
                    "match_id": match_id,
                    "period": 1,
                    "clock_ms": 1_000,
                    "video_time_ms": 1_000,
                    "type": event_type,
                    "team_id": "team-a",
                    "start": {"x": 88, "y": 50} if event_type == "shot" else None,
                    "outcome": outcome,
                    "source": "synthetic",
                }
            ],
        }
    )


async def main() -> None:
    required = (
        "EVENT_HUB_FULLY_QUALIFIED_NAMESPACE",
        "SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE",
    )
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise SystemExit("Faltan variables: " + ", ".join(missing))

    match_id = f"azure-routing-smoke-{uuid4()}"
    transport = AzureRoutingTransport.from_environment()
    pipeline = RoutedEventPipeline(transport)
    try:
        metric = await pipeline.evaluate(
            _request(match_id, event_type="pass", outcome="success")
        )
        important = await pipeline.evaluate(
            _request(match_id, event_type="shot", outcome="goal")
        )
        consume_smoke = os.getenv("ROUTING_SMOKE_CONSUME", "1") == "1"
        credential = DefaultAzureCredential()
        service_bus = ServiceBusClient(
            fully_qualified_namespace=os.environ["SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE"],
            credential=credential,
        )
        consumed_test_messages = 0
        try:
            async with service_bus:
                receiver = service_bus.get_queue_receiver(
                    queue_name=os.getenv("IMPORTANT_EVENTS_QUEUE_NAME", "important-events"),
                    max_wait_time=10,
                )
                async with receiver:
                    if not consume_smoke:
                        messages = []
                    else:
                        messages = await receiver.receive_messages(max_message_count=10)
                    for message in messages:
                        try:
                            body = json.loads(str(message))
                            candidate_match_id = body.get("decision", {}).get("match_id", "")
                        except (AttributeError, json.JSONDecodeError, TypeError):
                            candidate_match_id = ""
                        if candidate_match_id.startswith("azure-routing-smoke-"):
                            await receiver.complete_message(message)
                            consumed_test_messages += 1
                        else:
                            await receiver.abandon_message(message)
        finally:
            await credential.close()

        print(
            json.dumps(
                {
                    "match_id": match_id,
                    "metric_route": metric.decision.route,
                    "important_route": important.decision.route,
                    "important_message_id": important.decision.decision_id,
                    "consumed_test_messages": consumed_test_messages,
                    "transport": pipeline.status(),
                },
                indent=2,
            )
        )
    finally:
        await transport.close()


if __name__ == "__main__":
    asyncio.run(main())
