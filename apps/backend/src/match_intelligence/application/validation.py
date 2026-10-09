from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from pydantic import ValidationError

from match_intelligence.domain.contracts import MatchEvent


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """Detalle estable de un error, independiente del adaptador de entrada."""

    location: tuple[str | int, ...]
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class RejectedEvent:
    """Candidato rechazado y posición que ocupaba en el lote."""

    index: int
    event_id: str | None
    issues: tuple[ValidationIssue, ...]


@dataclass(frozen=True, slots=True)
class EventValidationReport:
    """Resultado completo de validar un lote sin detenerse ante errores."""

    accepted: tuple[MatchEvent, ...]
    rejected: tuple[RejectedEvent, ...]

    @property
    def accepted_count(self) -> int:
        return len(self.accepted)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)


def validate_event_batch(candidates: Iterable[object]) -> EventValidationReport:
    """Valida candidatos en orden y aísla los fallos de cada elemento.

    Un error de contrato se registra en ``rejected`` y no interrumpe la
    validación de los candidatos posteriores.
    """

    accepted: list[MatchEvent] = []
    rejected: list[RejectedEvent] = []

    for index, candidate in enumerate(candidates):
        try:
            accepted.append(MatchEvent.model_validate(candidate))
        except ValidationError as error:
            rejected.append(
                RejectedEvent(
                    index=index,
                    event_id=_candidate_event_id(candidate),
                    issues=tuple(
                        ValidationIssue(
                            location=tuple(detail["loc"]),
                            code=detail["type"],
                            message=detail["msg"],
                        )
                        for detail in error.errors(
                            include_url=False,
                            include_context=False,
                            include_input=False,
                        )
                    ),
                )
            )

    return EventValidationReport(
        accepted=tuple(accepted),
        rejected=tuple(rejected),
    )


def _candidate_event_id(candidate: object) -> str | None:
    if not isinstance(candidate, Mapping):
        return None

    event_id = candidate.get("event_id")
    return event_id if isinstance(event_id, str) else None
