"""Une la ingesta de Persona 1 con el procesador analítico de Persona 2.

``AzureEventHubConsumer`` (Persona 1) valida y deduplica; ``EventOrderTracker``
(Persona 1) marca los tardíos sin reordenarlos; el procesador reconstruye el
estado con ``rebuild_from_ordered_history@1``. El puente lee los eventos
aceptados por posición, sin modificar el consumidor.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from match_intelligence.adapters.messaging.azure_event_hubs import ReceivedMatchEvent
from match_intelligence.application.analytics.stream import (
    AnalyticsStreamProcessor,
    StreamStepResult,
)
from match_intelligence.application.event_order import EventOrderTracker


class AcceptedEventSource(Protocol):
    @property
    def accepted(self) -> Sequence[ReceivedMatchEvent]: ...


@dataclass(frozen=True, slots=True)
class BridgeStep:
    received: ReceivedMatchEvent
    arrival_status: str
    result: StreamStepResult


class EventHubAnalyticsBridge:
    def __init__(
        self,
        source: AcceptedEventSource,
        processor: AnalyticsStreamProcessor,
        *,
        tracker: EventOrderTracker | None = None,
    ) -> None:
        self._source = source
        self._processor = processor
        self._tracker = tracker or EventOrderTracker()
        self._cursor = 0

    @property
    def processed(self) -> int:
        return self._cursor

    async def drain(self) -> list[BridgeStep]:
        """Procesa los eventos aceptados desde la última llamada, en orden de llegada."""
        accepted = self._source.accepted
        steps = []
        while self._cursor < len(accepted):
            received = accepted[self._cursor]
            self._cursor += 1
            classified = self._tracker.process((received.event,)).forwarded[0]
            result = await self._processor.process(
                received.event, arrival_status=classified.status
            )
            steps.append(BridgeStep(received, classified.status.value, result))
        return steps
