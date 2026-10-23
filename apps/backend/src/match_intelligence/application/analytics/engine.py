"""Motor de estado con reconstrucción reproducible.

Política ``rebuild_from_ordered_history@1``, complementaria a la política
``forward_and_flag`` de la ingesta de Persona 1:

1. El motor guarda cada evento en orden deportivo ``(period, clock_ms)``; los
   empates conservan el orden de llegada.
2. Un evento puntual se aplica de forma incremental.
3. Un evento tardío se inserta en su posición y el estado se vuelve a plegar
   desde el inicio. El resultado es idéntico al de haberlo recibido a tiempo.
4. Una corrección explícita reemplaza el evento con el mismo ``event_id`` y
   reconstruye. Un retiro lo elimina y reconstruye.
5. Un evento repetido con el mismo contenido no cambia nada. Uno con el mismo
   ``event_id`` y contenido distinto se rechaza como conflicto: corregir exige
   una llamada explícita a ``correct``.
6. Cada reconstrucción crea una revisión con el marcador y la posesión antes y
   después, y los momentos que aparecen o desaparecen.
"""

from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from match_intelligence.domain.analytics.attention import AttentionReport, MomentDraft
from match_intelligence.domain.analytics.models import MatchSnapshot
from match_intelligence.domain.contracts import MatchEvent, MatchMetadata

from .pipeline import MatchAnalyzer, build_snapshot
from .value_models import ValueModelRegistry

LATE_EVENT_POLICY = "rebuild_from_ordered_history@1"


class IngestOutcome(StrEnum):
    APPLIED = "applied"
    REBUILT = "rebuilt"
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"
    FOREIGN_MATCH = "foreign_match"
    UNKNOWN_EVENT = "unknown_event"


class RevisionReason(StrEnum):
    LATE_EVENT = "late_event"
    CORRECTION = "correction"
    RETRACTION = "retraction"


@dataclass(frozen=True, slots=True)
class StateRevision:
    revision: int
    reason: RevisionReason
    event_id: str
    policy: str
    score_before: dict[str, int]
    score_after: dict[str, int]
    possession_before: str | None
    possession_after: str | None
    withdrawn_moment_ids: tuple[str, ...]
    added_moment_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IngestResult:
    outcome: IngestOutcome
    event_id: str
    revision: StateRevision | None = None
    new_moments: tuple[MomentDraft, ...] = ()


def _key(event: MatchEvent, arrival: int) -> tuple[int, int, int]:
    return (event.period, event.clock_ms, arrival)


class MatchStateEngine:
    """Estado de un partido que acepta eventos tardíos, correcciones y retiros."""

    policy = LATE_EVENT_POLICY

    def __init__(
        self, metadata: MatchMetadata, *, value_models: ValueModelRegistry | None = None
    ) -> None:
        self.metadata = metadata
        self._value_models = value_models or ValueModelRegistry()
        self._entries: list[tuple[tuple[int, int, int], MatchEvent]] = []
        self._by_id: dict[str, MatchEvent] = {}
        self._arrivals = 0
        self._revisions: list[StateRevision] = []
        self._late: list[str] = []
        self._corrected: list[str] = []
        self._analyzer = MatchAnalyzer(metadata, value_models=self._value_models)

    @property
    def events(self) -> list[MatchEvent]:
        return [event for _, event in self._entries]

    @property
    def revisions(self) -> tuple[StateRevision, ...]:
        return tuple(self._revisions)

    @property
    def revision(self) -> int:
        return len(self._revisions)

    @property
    def late_event_ids(self) -> tuple[str, ...]:
        return tuple(self._late)

    @property
    def corrected_event_ids(self) -> tuple[str, ...]:
        return tuple(self._corrected)

    @property
    def analyzer(self) -> MatchAnalyzer:
        return self._analyzer

    def ingest(self, event: MatchEvent, *, arrival_status: object | None = None) -> IngestResult:
        """Aplica un evento nuevo. ``arrival_status`` de Persona 1 solo se registra."""
        if event.match_id != self.metadata.match_id:
            return IngestResult(IngestOutcome.FOREIGN_MATCH, event.event_id)
        existing = self._by_id.get(event.event_id)
        if existing is not None:
            outcome = IngestOutcome.DUPLICATE if existing == event else IngestOutcome.CONFLICT
            return IngestResult(outcome, event.event_id)

        key = _key(event, self._arrivals)
        self._arrivals += 1
        position = bisect_right([entry_key for entry_key, _ in self._entries], key)
        self._entries.insert(position, (key, event))
        self._by_id[event.event_id] = event

        if position == len(self._entries) - 1:
            moments = self._analyzer.add(event)
            return IngestResult(IngestOutcome.APPLIED, event.event_id, new_moments=moments)

        self._late.append(event.event_id)
        revision = self._refold(RevisionReason.LATE_EVENT, event.event_id)
        return IngestResult(IngestOutcome.REBUILT, event.event_id, revision)

    def correct(self, event: MatchEvent) -> IngestResult:
        existing = self._by_id.get(event.event_id)
        if existing is None:
            return IngestResult(IngestOutcome.UNKNOWN_EVENT, event.event_id)
        if existing == event:
            return IngestResult(IngestOutcome.DUPLICATE, event.event_id)
        index = next(i for i, (_, item) in enumerate(self._entries) if item.event_id == event.event_id)
        arrival = self._entries[index][0][2]
        del self._entries[index]
        key = _key(event, arrival)
        position = bisect_right([entry_key for entry_key, _ in self._entries], key)
        self._entries.insert(position, (key, event))
        self._by_id[event.event_id] = event
        self._corrected.append(event.event_id)
        revision = self._refold(RevisionReason.CORRECTION, event.event_id)
        return IngestResult(IngestOutcome.REBUILT, event.event_id, revision)

    def retract(self, event_id: str) -> IngestResult:
        if event_id not in self._by_id:
            return IngestResult(IngestOutcome.UNKNOWN_EVENT, event_id)
        self._entries = [(key, event) for key, event in self._entries if event.event_id != event_id]
        del self._by_id[event_id]
        revision = self._refold(RevisionReason.RETRACTION, event_id)
        return IngestResult(IngestOutcome.REBUILT, event_id, revision)

    def snapshot(self, *, video_time_ms: int | None = None) -> MatchSnapshot:
        return build_snapshot(
            self.metadata,
            self.events,
            video_time_ms=video_time_ms,
            value_models=self._value_models,
            state_revision=self.revision,
            late_event_ids=self._late,
            corrected_event_ids=self._corrected,
        )

    def attention(self, preferences: object | None = None) -> AttentionReport:
        return self._analyzer.attention(preferences)

    async def rebuild(self, events: tuple[MatchEvent, ...], *, video_time_ms: int) -> None:
        """``MatchStateRebuilder`` de Persona 1: reposiciona el estado al saltar en el vídeo.

        Un salto no es una revisión del partido: reinicia el historial con los
        eventos anteriores a la nueva posición del vídeo.
        """
        self._entries = []
        self._by_id = {}
        self._arrivals = 0
        self._revisions = []
        self._late = []
        self._corrected = []
        self._analyzer = MatchAnalyzer(self.metadata, value_models=self._value_models)
        for event in events:
            self.ingest(event)

    def _refold(self, reason: RevisionReason, event_id: str) -> StateRevision:
        before_state = self._analyzer.state
        before_moments = {moment.candidate_id for moment in self._analyzer.moments()}
        score_before = dict(before_state.score)
        possession_before = before_state.possession_team_id

        analyzer = MatchAnalyzer(self.metadata, value_models=self._value_models)
        analyzer.extend(self.events)
        self._analyzer = analyzer

        after_moments = {moment.candidate_id for moment in analyzer.moments()}
        revision = StateRevision(
            revision=len(self._revisions) + 1,
            reason=reason,
            event_id=event_id,
            policy=self.policy,
            score_before=score_before,
            score_after=dict(analyzer.state.score),
            possession_before=possession_before,
            possession_after=analyzer.state.possession_team_id,
            withdrawn_moment_ids=tuple(sorted(before_moments - after_moments)),
            added_moment_ids=tuple(sorted(after_moments - before_moments)),
        )
        self._revisions.append(revision)
        return revision


def replay(
    metadata: MatchMetadata,
    events: Sequence[MatchEvent],
    *,
    value_models: ValueModelRegistry | None = None,
) -> MatchStateEngine:
    """Reproduce una secuencia completa en su orden de llegada."""
    engine = MatchStateEngine(metadata, value_models=value_models)
    for event in events:
        engine.ingest(event)
    return engine
