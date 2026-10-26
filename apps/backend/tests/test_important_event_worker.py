import asyncio

from match_intelligence.adapters.messaging.important_event_worker import AzureImportantEventWorker
from match_intelligence.application.important_event_worker import (
    DispatchRecordingHandler,
    ImportantEventProcessor,
)
from match_intelligence.application.routing import AgentRoutingService, RoutingEvaluationRequest


def _outcome():
    request = RoutingEvaluationRequest.model_validate({
        "match_id": "worker-001",
        "events": [{
            "schema_version": "1.0", "event_id": "shot-1", "match_id": "worker-001",
            "period": 1, "clock_ms": 1000, "video_time_ms": 1000, "type": "shot",
            "team_id": "team-a", "start": {"x": 90, "y": 50}, "outcome": "goal",
            "source": "synthetic",
        }],
    })
    return AgentRoutingService().evaluate(request)


class Message:
    def __init__(self, body): self.body = body
    def __str__(self): return self.body


class Receiver:
    def __init__(self, messages=()):
        self.messages = list(messages); self.completed = []; self.abandoned = []; self.dead = []
    async def receive_messages(self, **_): return self.messages
    async def complete_message(self, message): self.completed.append(message)
    async def abandon_message(self, message): self.abandoned.append(message)
    async def dead_letter_message(self, message, **kwargs): self.dead.append((message, kwargs))


def test_worker_completes_valid_message_and_deduplicates() -> None:
    async def scenario():
        payload = _outcome().model_dump_json()
        receiver = Receiver([Message(payload), Message(payload)])
        worker = AzureImportantEventWorker(
            receiver, ImportantEventProcessor(DispatchRecordingHandler())
        )
        counts = await worker.run_once()
        assert counts == {"processed": 1, "duplicate": 1, "abandoned": 0, "dead_lettered": 0}
        assert len(receiver.completed) == 2
    asyncio.run(scenario())


def test_worker_dead_letters_invalid_contract() -> None:
    async def scenario():
        receiver = Receiver([Message('{"invalid": true}')])
        worker = AzureImportantEventWorker(
            receiver, ImportantEventProcessor(DispatchRecordingHandler())
        )
        counts = await worker.run_once()
        assert counts["dead_lettered"] == 1
        assert receiver.dead[0][1]["reason"] == "InvalidRoutingOutcome"
    asyncio.run(scenario())
