from collections.abc import Iterable
from dataclasses import dataclass

from match_intelligence.domain.contracts import MatchEvent

EventKey = tuple[str, str]


@dataclass(frozen=True, slots=True)
class DuplicateEvent:
    """Reintento ignorado y posición en la que fue observado."""

    index: int
    match_id: str
    event_id: str
    first_seen_sequence: int
    duplicate_sequence: int

    @property
    def key(self) -> EventKey:
        return (self.match_id, self.event_id)


@dataclass(frozen=True, slots=True)
class DeduplicationReport:
    """Eventos nuevos y duplicados encontrados en una operación de ingesta."""

    accepted: tuple[MatchEvent, ...]
    duplicates: tuple[DuplicateEvent, ...]

    @property
    def accepted_count(self) -> int:
        return len(self.accepted)

    @property
    def duplicate_count(self) -> int:
        return len(self.duplicates)


class EventDeduplicator:
    """Aplica idempotencia por ``(match_id, event_id)`` entre operaciones.

    La instancia representa el registro de un consumidor. El adaptador local y
    el futuro consumidor de Event Hubs pueden conservar una instancia durante
    su ciclo de vida y pasarle únicamente eventos que ya fueron validados.
    """

    def __init__(self) -> None:
        self._first_seen: dict[EventKey, int] = {}
        self._duplicates: list[DuplicateEvent] = []
        self._sequence = 0

    @property
    def duplicates(self) -> tuple[DuplicateEvent, ...]:
        """Registro acumulado para diagnóstico durante el ciclo de vida."""
        return tuple(self._duplicates)

    @property
    def seen_count(self) -> int:
        return len(self._first_seen)

    def process(self, events: Iterable[MatchEvent]) -> DeduplicationReport:
        """Acepta la primera aparición de cada clave y registra reintentos."""
        accepted: list[MatchEvent] = []
        duplicates: list[DuplicateEvent] = []

        for index, event in enumerate(events):
            sequence = self._sequence
            self._sequence += 1
            key = (event.match_id, event.event_id)
            first_seen_sequence = self._first_seen.get(key)

            if first_seen_sequence is None:
                self._first_seen[key] = sequence
                accepted.append(event)
                continue

            duplicate = DuplicateEvent(
                index=index,
                match_id=event.match_id,
                event_id=event.event_id,
                first_seen_sequence=first_seen_sequence,
                duplicate_sequence=sequence,
            )
            duplicates.append(duplicate)
            self._duplicates.append(duplicate)

        return DeduplicationReport(
            accepted=tuple(accepted),
            duplicates=tuple(duplicates),
        )
