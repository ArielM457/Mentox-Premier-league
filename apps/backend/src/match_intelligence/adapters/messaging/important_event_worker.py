"""Worker Azure Service Bus para ``important-events``."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from azure.identity.aio import DefaultAzureCredential
from azure.servicebus.aio import AutoLockRenewer, ServiceBusClient
from pydantic import ValidationError

from match_intelligence.application.important_event_worker import ImportantEventProcessor
from match_intelligence.application.routing import RoutingOutcome


class AzureImportantEventWorker:
    def __init__(
        self,
        receiver: Any,
        processor: ImportantEventProcessor,
        *,
        lock_renewer: Any | None = None,
        result_sink: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.receiver = receiver
        self.processor = processor
        self.lock_renewer = lock_renewer
        self.result_sink = result_sink or (lambda _: None)

    async def process_message(self, message: Any) -> str:
        if self.lock_renewer is not None:
            self.lock_renewer.register(
                self.receiver,
                message,
                max_lock_renewal_duration=300,
            )
        try:
            outcome = RoutingOutcome.model_validate_json(str(message))
        except (ValidationError, ValueError, TypeError) as error:
            await self.receiver.dead_letter_message(
                message,
                reason="InvalidRoutingOutcome",
                error_description=str(error)[:4096],
            )
            return "dead_lettered"
        try:
            result = await self.processor.process(outcome)
        except Exception:
            await self.receiver.abandon_message(message)
            return "abandoned"
        self.result_sink(result.model_dump(mode="json"))
        await self.receiver.complete_message(message)
        return result.status

    async def run_once(self, *, max_messages: int = 10, max_wait_time: float = 10) -> dict[str, int]:
        counts = {"processed": 0, "duplicate": 0, "abandoned": 0, "dead_lettered": 0}
        messages = await self.receiver.receive_messages(
            max_message_count=max_messages,
            max_wait_time=max_wait_time,
        )
        for message in messages:
            outcome = await self.process_message(message)
            counts[outcome] += 1
        return counts


async def build_azure_worker(processor: ImportantEventProcessor):
    namespace = os.environ["SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE"]
    queue = os.getenv("IMPORTANT_EVENTS_QUEUE_NAME", "important-events")
    credential = DefaultAzureCredential()
    client = ServiceBusClient(fully_qualified_namespace=namespace, credential=credential)
    receiver = client.get_queue_receiver(queue_name=queue, max_wait_time=10)
    renewer = AutoLockRenewer()
    return AzureImportantEventWorker(receiver, processor, lock_renewer=renewer), client, credential, renewer
