import asyncio

import pytest

from match_intelligence.adapters.messaging.routing_transport import AzureRoutingTransport
from match_intelligence.application.routing import (
    MemoryRoutingTransport,
    RoutedEventPipeline,
    RoutingEvaluationRequest,
)


def request(kind: str = "pass", *, outcome: str = "success") -> RoutingEvaluationRequest:
    return RoutingEvaluationRequest.model_validate(
        {
            "match_id": "routing-transport-001",
            "events": [
                {
                    "schema_version": "1.0",
                    "event_id": f"evt-{kind}",
                    "match_id": "routing-transport-001",
                    "period": 1,
                    "clock_ms": 1_000,
                    "video_time_ms": 1_000,
                    "type": kind,
                    "team_id": "team-a",
                    "start": {"x": 85, "y": 50} if kind == "shot" else None,
                    "outcome": outcome,
                    "source": "synthetic",
                }
            ],
        }
    )


def test_metrics_and_important_use_different_channels() -> None:
    async def scenario() -> None:
        transport = MemoryRoutingTransport()
        pipeline = RoutedEventPipeline(transport)

        metrics = await pipeline.evaluate(request())
        important = await pipeline.evaluate(request("shot", outcome="blocked"))

        assert metrics.decision.route == "metrics_only"
        assert important.decision.route == "danger_immediate"
        assert len(transport.ingress) == 2
        assert len(transport.metrics) == 1
        assert len(transport.important) == 1
        assert transport.important[0]["message_id"] == important.decision.decision_id

    asyncio.run(scenario())


class FailingMetricsTransport(MemoryRoutingTransport):
    async def publish_metrics(self, payload, *, partition_key):
        raise RuntimeError("telemetry unavailable")


class FailingImportantTransport(MemoryRoutingTransport):
    async def publish_important(self, payload, *, message_id):
        raise RuntimeError("durable queue unavailable")


def test_metrics_failure_is_observable_but_does_not_lose_ingress() -> None:
    async def scenario() -> None:
        transport = FailingMetricsTransport()
        pipeline = RoutedEventPipeline(transport)
        result = await pipeline.evaluate(request())

        assert result.decision.route == "metrics_only"
        assert len(transport.ingress) == 1
        assert pipeline.status()["telemetry_failures"] == 1

    asyncio.run(scenario())


def test_important_failure_is_propagated_for_retry() -> None:
    async def scenario() -> None:
        transport = FailingImportantTransport()
        pipeline = RoutedEventPipeline(transport)

        with pytest.raises(RuntimeError, match="durable queue unavailable"):
            await pipeline.evaluate(request("shot", outcome="goal"))
        assert len(transport.ingress) == 1

    asyncio.run(scenario())


class RecordingEventHub:
    def __init__(self) -> None:
        self.calls = []

    async def send_batch(self, events, *, partition_key):
        self.calls.append((events, partition_key))

    async def close(self):
        return None


class RecordingServiceBus:
    def __init__(self) -> None:
        self.messages = []

    async def send_messages(self, message):
        self.messages.append(message)

    async def close(self):
        return None


def test_azure_transport_preserves_partition_and_idempotency_keys() -> None:
    async def scenario() -> None:
        ingress = RecordingEventHub()
        metrics = RecordingEventHub()
        important = RecordingServiceBus()
        transport = AzureRoutingTransport(ingress, metrics, important)

        await transport.publish_ingress({"kind": "input"}, partition_key="match-1")
        await transport.publish_metrics({"kind": "metric"}, partition_key="match-1")
        await transport.publish_important({"kind": "goal"}, message_id="decision-1")

        assert ingress.calls[0][1] == "match-1"
        assert metrics.calls[0][1] == "match-1"
        assert important.messages[0].message_id == "decision-1"
        assert transport.status()["important_published"] == 1

    asyncio.run(scenario())
