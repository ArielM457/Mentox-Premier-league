import asyncio
import json

import pytest

from match_intelligence.adapters.messaging.azure_community import (
    AzureEventHubsMessageBus,
    build_community_bus,
)
from match_intelligence.application.community import InMemoryMessageBus


def run(test):
    """Las pruebas usan asyncio.run como el resto del backend (no hay pytest-asyncio)."""

    def wrapper():
        asyncio.run(test())

    wrapper.__name__ = test.__name__
    return wrapper


class FakeHub:
    """Un Event Hub en memoria: lo que envía el productor lo reciben los consumidores."""

    def __init__(self) -> None:
        self.handlers = []
        self.sent = []
        self.fail = False

    def producer(self):
        hub = self

        class Producer:
            closed = False

            async def send_batch(self, batch, *, partition_key=None):
                if hub.fail:
                    raise ConnectionError("sin red")
                for event in batch:
                    hub.sent.append((partition_key, event))
                    for handler in list(hub.handlers):
                        await handler(None, event)

            async def close(self):
                self.closed = True

        return Producer()

    def consumer(self):
        hub = self

        class Consumer:
            starting_position = None

            async def receive(self, on_event, **kwargs):
                self.starting_position = kwargs.get("starting_position")
                hub.handlers.append(on_event)
                await asyncio.Event().wait()

            async def close(self):
                pass

        return Consumer()


async def _next(stream, timeout=1.0):
    return await asyncio.wait_for(anext(stream), timeout)


@run
async def test_events_travel_through_the_hub_to_every_replica():
    hub = FakeHub()
    first = AzureEventHubsMessageBus(hub.producer(), hub.consumer())
    second = AzureEventHubsMessageBus(hub.producer(), hub.consumer())
    await first.start()
    await second.start()
    await asyncio.sleep(0)
    stream = second.subscribe("community/m1/d1")
    local = first.subscribe("community/m1/d1")

    first.publish("community/m1/d1", {"type": "vote", "vote": "approve"})

    assert await _next(stream) == {"type": "vote", "vote": "approve"}
    assert await _next(local) == {"type": "vote", "vote": "approve"}
    partition_key, event = hub.sent[0]
    assert partition_key == "community/m1/d1"
    assert json.loads(event.body_as_str())["topic"] == "community/m1/d1"
    assert first.counts["sent"] == 1 and second.counts["received"] == 1
    await first.close()
    await second.close()


@run
async def test_reads_only_new_events():
    hub = FakeHub()
    consumer = hub.consumer()
    bus = AzureEventHubsMessageBus(hub.producer(), consumer)
    await bus.start()
    await asyncio.sleep(0)
    assert consumer.starting_position == "@latest"
    await bus.close()


@run
async def test_falls_back_to_local_delivery_when_azure_fails():
    hub = FakeHub()
    hub.fail = True
    bus = AzureEventHubsMessageBus(hub.producer(), hub.consumer())
    await bus.start()
    stream = bus.subscribe("t")

    bus.publish("t", {"type": "message"})

    assert await _next(stream) == {"type": "message"}
    assert bus.counts["fallback"] == 1
    await bus.close()


@run
async def test_delivers_locally_before_the_bus_starts():
    bus = AzureEventHubsMessageBus(FakeHub().producer(), FakeHub().consumer())
    stream = bus.subscribe("t")
    bus.publish("t", {"type": "vote"})
    assert await _next(stream) == {"type": "vote"}


@run
async def test_ignores_malformed_events():
    hub = FakeHub()
    bus = AzureEventHubsMessageBus(hub.producer(), hub.consumer())

    class Broken:
        def body_as_str(self):
            return "no es json"

    await bus._on_event(None, Broken())
    await bus._on_event(None, None)
    assert bus.counts["received"] == 0


def test_transport_is_chosen_from_the_environment(monkeypatch):
    monkeypatch.delenv("COMMUNITY_TRANSPORT", raising=False)
    assert isinstance(build_community_bus(), InMemoryMessageBus)
    monkeypatch.setenv("COMMUNITY_TRANSPORT", "mqtt")
    with pytest.raises(ValueError):
        build_community_bus()
