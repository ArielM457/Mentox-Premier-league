from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from match_intelligence.domain.contracts import MatchEvent


@dataclass(frozen=True, order=True, slots=True)
class MatchTime:
    """Posición comparable en el reloj deportivo de un partido."""

    period: int
    clock_ms: int


class ArrivalStatus(StrEnum):
    ON_TIME = "on_time"
    LATE = "late"


class LateEventPolicy(StrEnum):
    """Política de ingesta; no decide cómo reconstruir el estado."""

    FORWARD_AND_FLAG = "forward_and_flag"


@dataclass(frozen=True, slots=True)
class ClassifiedEvent:
    event: MatchEvent
    status: ArrivalStatus
    arrival_sequence: int
    watermark_before: MatchTime | None


@dataclass(frozen=True, slots=True)
class LateEventRecord:
    """Diagnóstico reproducible de un evento anterior al reloj máximo visto."""

    index: int
    match_id: str
    event_id: str
    event_time: MatchTime
    watermark: MatchTime
    arrival_sequence: int


@dataclass(frozen=True, slots=True)
class EventOrderReport:
    """Eventos reenviados en orden de llegada y tardíos observados."""

    forwarded: tuple[ClassifiedEvent, ...]
    late: tuple[LateEventRecord, ...]
    policy: LateEventPolicy = LateEventPolicy.FORWARD_AND_FLAG

    @property
    def forwarded_count(self) -> int:
        return len(self.forwarded)

    @property
    def late_count(self) -> int:
        return len(self.late)


class EventOrderTracker:
    """Detecta retrocesos del reloj sin descartar ni reordenar eventos.

    Debe recibir eventos validados y deduplicados. Cada partido mantiene su
    propio reloj máximo. Un evento tardío se reenvía marcado y no reduce ese
    reloj; Persona 2 decidirá cómo reconstruir el estado a partir de la marca.
    """

    policy = LateEventPolicy.FORWARD_AND_FLAG

    def __init__(self) -> None:
        self._watermarks: dict[str, MatchTime] = {}
        self._late_events: list[LateEventRecord] = []
        self._arrival_sequence = 0

    @property
    def late_events(self) -> tuple[LateEventRecord, ...]:
        return tuple(self._late_events)

    def watermark_for(self, match_id: str) -> MatchTime | None:
        return self._watermarks.get(match_id)

    def process(self, events: Iterable[MatchEvent]) -> EventOrderReport:
        forwarded: list[ClassifiedEvent] = []
        late: list[LateEventRecord] = []

        for index, event in enumerate(events):
            event_time = MatchTime(period=event.period, clock_ms=event.clock_ms)
            watermark = self._watermarks.get(event.match_id)
            arrival_sequence = self._arrival_sequence
            self._arrival_sequence += 1
            is_late = watermark is not None and event_time < watermark

            forwarded.append(
                ClassifiedEvent(
                    event=event,
                    status=ArrivalStatus.LATE if is_late else ArrivalStatus.ON_TIME,
                    arrival_sequence=arrival_sequence,
                    watermark_before=watermark,
                )
            )

            if is_late:
                record = LateEventRecord(
                    index=index,
                    match_id=event.match_id,
                    event_id=event.event_id,
                    event_time=event_time,
                    watermark=watermark,
                    arrival_sequence=arrival_sequence,
                )
                late.append(record)
                self._late_events.append(record)
                continue

            if watermark is None or event_time > watermark:
                self._watermarks[event.match_id] = event_time

        return EventOrderReport(
            forwarded=tuple(forwarded),
            late=tuple(late),
        )
