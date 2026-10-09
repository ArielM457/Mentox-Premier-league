from match_intelligence.application.deduplication import (
    DeduplicationReport,
    DuplicateEvent,
    EventDeduplicator,
)
from match_intelligence.domain.contracts import MatchEvent


class InMemoryEventPublisher:
    """Publicador local para desarrollo y pruebas sin servicios externos."""

    def __init__(self) -> None:
        self._events: list[MatchEvent] = []

    @property
    def events(self) -> tuple[MatchEvent, ...]:
        return tuple(self._events)

    async def publish(self, event: MatchEvent) -> None:
        self._events.append(event)

    def clear(self) -> None:
        self._events.clear()


class InMemoryEventConsumer:
    """Consumidor local que entrega una sola vez cada evento deportivo."""

    def __init__(self, deduplicator: EventDeduplicator | None = None) -> None:
        self._deduplicator = deduplicator or EventDeduplicator()
        self._events: list[MatchEvent] = []

    @property
    def events(self) -> tuple[MatchEvent, ...]:
        return tuple(self._events)

    @property
    def duplicates(self) -> tuple[DuplicateEvent, ...]:
        return self._deduplicator.duplicates

    def consume(self, events: tuple[MatchEvent, ...]) -> DeduplicationReport:
        report = self._deduplicator.process(events)
        self._events.extend(report.accepted)
        return report
