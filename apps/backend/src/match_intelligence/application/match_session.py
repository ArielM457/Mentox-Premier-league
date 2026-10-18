"""Casos de uso de presentación: une analítica y narración para la pantalla.

Persona 4 es dueña de este módulo. No calcula métricas ni redacta textos;
delega en ``AnalyticsPort`` y ``NarrativePort`` y decide cuándo y cómo se
muestra cada mensaje.
"""

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from match_intelligence.application.ports import (
    AnalyticsPort,
    NarrativePort,
    VerificationOutcome,
)
from match_intelligence.application.video_sync import (
    SynchronizedEvent,
    VideoSynchronizedReplay,
    VideoSyncError,
)
from match_intelligence.domain.contracts import MatchEvent, MatchMetadata
from match_intelligence.domain.presentation import (
    ContentKind,
    DetailLevel,
    EditorialStatus,
    InsightCandidate,
    MatchSnapshot,
    NarrativeDraft,
    OverlayMessage,
    VerificationStatus,
    ViewerMode,
    ViewerPreferences,
)

CASUAL_MIN_PRIORITY = 50
PLAYER_QUIET_GAP_MS = 10_000
END_PADDING_MS = 8_000
ALWAYS_SHOWN_KINDS = {"goal"}


class SessionError(Exception):
    """Error de negocio que la API traduce a un código HTTP."""

    status_code = 400


class NotFoundError(SessionError):
    status_code = 404


class ConflictError(SessionError):
    status_code = 409


class ReviewDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


@dataclass
class EditorialRecord:
    draft: NarrativeDraft
    status: EditorialStatus = EditorialStatus.PENDING
    reviewer: str | None = None
    note: str | None = None
    decided_at: datetime | None = None


@dataclass
class ErrorReport:
    report_id: str
    draft_id: str
    message_id: str | None
    reason: str
    outcome: VerificationOutcome
    issues: list[str]
    corrected_draft: NarrativeDraft | None
    created_at: datetime


@dataclass
class OverlayBatch:
    overlays: list[OverlayMessage]
    pipeline_ms: float


def _video_time(event: MatchEvent) -> int:
    return event.video_time_ms if event.video_time_ms is not None else event.clock_ms


@dataclass
class MatchSession:
    metadata: MatchMetadata
    events: tuple[MatchEvent, ...]
    analytics: AnalyticsPort
    narrative: NarrativePort
    correction_narrative: NarrativePort
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    _drafts: dict[str, NarrativeDraft] = field(default_factory=dict)
    _withdrawn_candidates: set[str] = field(default_factory=set)
    _editorial: dict[str, EditorialRecord] = field(default_factory=dict)
    _reports: list[ErrorReport] = field(default_factory=list)
    _clock: Callable[[], datetime] = field(default=lambda: datetime.now(UTC))
    _replay: VideoSynchronizedReplay | None = None

    def __post_init__(self) -> None:
        missing = [e.event_id for e in self.events if e.video_time_ms is None]
        if missing:
            raise SessionError(
                "Todos los eventos necesitan video_time_ms para sincronizar: " + ", ".join(missing)
            )
        self.events = tuple(sorted(self.events, key=_video_time))

    # ----- consultas básicas ----------------------------------------------
    @property
    def match_id(self) -> str:
        return self.metadata.match_id

    @property
    def duration_ms(self) -> int:
        if not self.events:
            return END_PADDING_MS
        return _video_time(self.events[-1]) + END_PADDING_MS

    def events_until(self, video_time_ms: int) -> list[MatchEvent]:
        return [e for e in self.events if _video_time(e) <= video_time_ms]

    def snapshot(self, video_time_ms: int) -> MatchSnapshot:
        self._check_time(video_time_ms)
        return self.analytics.snapshot(
            self.metadata, self.events_until(video_time_ms), video_time_ms=video_time_ms
        )

    # ----- mensajes para pantalla -------------------------------------------
    def overlays(
        self, preferences: ViewerPreferences, *, until_video_ms: int | None = None
    ) -> OverlayBatch:
        """Planifica los mensajes visibles hasta ``until_video_ms``.

        Solo usa eventos ya ocurridos, de modo que la misma función sirve para
        el canal en directo y para reconstruir la pantalla tras adelantar.
        """
        self._validate_preferences(preferences)
        limit = self.duration_ms if until_video_ms is None else until_video_ms
        self._check_time(limit)
        started = time.perf_counter()
        events = self.events_until(limit)
        candidates = self.analytics.candidates(self.metadata, events, preferences)
        by_id = {e.event_id: e for e in events}

        messages: list[OverlayMessage] = []
        for candidate in candidates:
            if not self._selected(candidate, preferences):
                continue
            draft, corrected = self._live_draft(candidate, preferences)
            if draft.verification_status is not VerificationStatus.APPROVED:
                continue
            video_time = max(_video_time(by_id[eid]) for eid in candidate.source_event_ids if eid in by_id)
            messages.append(
                self._overlay(draft, candidate.kind, candidate.priority, candidate.period, candidate.clock_ms, video_time, preferences, corrected)
            )

        if preferences.mode is ViewerMode.PLAYER and preferences.favorite_player_id:
            messages.extend(self._quiet_messages(events, candidates, preferences, limit))

        scheduled = schedule_overlays(messages)
        elapsed = (time.perf_counter() - started) * 1000
        return OverlayBatch(scheduled, elapsed)

    def _selected(self, candidate: InsightCandidate, preferences: ViewerPreferences) -> bool:
        if candidate.kind in ALWAYS_SHOWN_KINDS:
            return True  # Nunca se ocultan hechos decisivos del rival (RF-24).
        if preferences.mode is ViewerMode.PLAYER and preferences.favorite_player_id:
            return preferences.favorite_player_id in candidate.player_ids
        if preferences.mode is ViewerMode.CASUAL:
            return candidate.priority >= CASUAL_MIN_PRIORITY
        return True

    def _live_draft(
        self, candidate: InsightCandidate, preferences: ViewerPreferences
    ) -> tuple[NarrativeDraft, bool]:
        if candidate.candidate_id in self._withdrawn_candidates:
            draft = self.correction_narrative.live(self.metadata, candidate, preferences)
            draft = draft.model_copy(update={"draft_id": draft.draft_id + "-v2"})
            corrected = True
        else:
            draft = self.narrative.live(self.metadata, candidate, preferences)
            corrected = False
        self._drafts[draft.draft_id] = draft
        return draft, corrected

    def _quiet_messages(
        self,
        events: Sequence[MatchEvent],
        candidates: Sequence[InsightCandidate],
        preferences: ViewerPreferences,
        limit: int,
    ) -> list[OverlayMessage]:
        player_id = preferences.favorite_player_id
        assert player_id
        involvement = sorted(
            {_video_time(e) for e in events if e.player_id == player_id}
        )
        start = _video_time(self.events[0]) if self.events else 0
        messages: list[OverlayMessage] = []
        last = start
        checkpoints = [*involvement, min(limit, self.duration_ms)]
        for moment in checkpoints:
            quiet_at = last + PLAYER_QUIET_GAP_MS
            while quiet_at < moment and quiet_at <= limit:
                clock = self._clock_for_video(quiet_at)
                draft = self.narrative.player_quiet(
                    self.metadata,
                    player_id,
                    since_clock_ms=self._clock_for_video(last),
                    until_clock_ms=clock,
                    preferences=preferences,
                )
                self._drafts[draft.draft_id] = draft
                messages.append(
                    self._overlay(draft, "player_quiet", 30, 1, clock, quiet_at, preferences, False)
                )
                quiet_at += PLAYER_QUIET_GAP_MS
            last = max(last, moment)
        return messages

    def _clock_for_video(self, video_time_ms: int) -> int:
        previous = [e for e in self.events if _video_time(e) <= video_time_ms]
        if not previous:
            first = self.events[0] if self.events else None
            return max(0, (first.clock_ms - (_video_time(first) - video_time_ms)) if first else video_time_ms)
        last = previous[-1]
        return last.clock_ms + (video_time_ms - _video_time(last))

    @staticmethod
    def _overlay(
        draft: NarrativeDraft,
        kind: str,
        priority: int,
        period: int,
        clock_ms: int,
        video_time_ms: int,
        preferences: ViewerPreferences,
        corrected: bool,
    ) -> OverlayMessage:
        show_for = 4_000 + priority * 40
        if preferences.mode is ViewerMode.ANALYST or preferences.level is DetailLevel.ADVANCED:
            show_for += 1_500
        if preferences.level is DetailLevel.SIMPLE:
            show_for -= 1_000
        return OverlayMessage(
            message_id=draft.draft_id.replace("draft-", "overlay-", 1),
            draft_id=draft.draft_id,
            candidate_id=draft.candidate_id,
            match_id=draft.match_id,
            period=period,
            clock_ms=clock_ms,
            video_time_ms=video_time_ms,
            show_for_ms=show_for,
            priority=priority,
            kind=kind,
            language=draft.language,
            mode=draft.mode,
            level=draft.level,
            headline=draft.headline,
            explanation=draft.explanation,
            source_event_ids=draft.source_event_ids,
            display_until_ms=video_time_ms + show_for,
            corrected=corrected,
        )

    # ----- fuentes de un mensaje ------------------------------------------
    def sources(self, draft_id: str) -> tuple[NarrativeDraft, list[MatchEvent]]:
        draft = self._find_draft(draft_id)
        by_id = {e.event_id: e for e in self.events}
        return draft, [by_id[eid] for eid in draft.source_event_ids if eid in by_id]

    def _find_draft(self, draft_id: str) -> NarrativeDraft:
        if draft_id in self._drafts:
            return self._drafts[draft_id]
        if draft_id in self._editorial:
            return self._editorial[draft_id].draft
        raise NotFoundError(f"No existe la narración {draft_id}")

    # ----- preguntas -------------------------------------------------------
    def ask(self, question: str, video_time_ms: int, preferences: ViewerPreferences) -> NarrativeDraft:
        if not question.strip():
            raise SessionError("La pregunta está vacía")
        snapshot = self.snapshot(video_time_ms)
        draft = self.narrative.answer(
            self.metadata, self.events_until(video_time_ms), snapshot, question, preferences
        )
        self._drafts[draft.draft_id] = draft
        return draft

    # ----- resumen y revisión editorial -------------------------------------
    def summary(self, preferences: ViewerPreferences) -> EditorialRecord:
        """Genera el resumen final; queda pendiente hasta su revisión (RF-38)."""
        self._validate_preferences(preferences)
        snapshot = self.snapshot(self.duration_ms)
        candidates = self.analytics.candidates(self.metadata, self.events, preferences)
        draft = self.narrative.summary(self.metadata, snapshot, candidates, preferences)
        record = self._editorial.get(draft.draft_id)
        if record is None:
            record = EditorialRecord(draft=draft)
            self._editorial[draft.draft_id] = record
        return record

    def editorial_queue(self) -> list[EditorialRecord]:
        return list(self._editorial.values())

    def review(
        self, draft_id: str, decision: ReviewDecision, reviewer: str, note: str | None
    ) -> EditorialRecord:
        record = self._editorial.get(draft_id)
        if record is None:
            raise NotFoundError(f"No existe el análisis final {draft_id}")
        if not reviewer.strip():
            raise SessionError("La revisión necesita el nombre de quien revisa")
        if record.status is not EditorialStatus.PENDING:
            raise ConflictError(f"El análisis {draft_id} ya fue revisado: {record.status.value}")
        record.status = (
            EditorialStatus.APPROVED if decision is ReviewDecision.APPROVE else EditorialStatus.REJECTED
        )
        record.reviewer = reviewer
        record.note = note
        record.decided_at = self._clock()
        record.draft = record.draft.model_copy(update={"editorial_status": record.status})
        return record

    def published(self, draft_id: str) -> NarrativeDraft:
        """Devuelve el análisis final solo si fue aprobado."""
        record = self._editorial.get(draft_id)
        if record is None:
            raise NotFoundError(f"No existe el análisis final {draft_id}")
        if record.status is not EditorialStatus.APPROVED:
            raise ConflictError(
                f"El análisis {draft_id} no se publica: estado editorial {record.status.value}"
            )
        return record.draft

    # ----- reportes de error ------------------------------------------------
    def report(self, draft_id: str, reason: str, message_id: str | None = None) -> ErrorReport:
        if not reason.strip():
            raise SessionError("El reporte necesita un motivo")
        draft = self._find_draft(draft_id)
        result = self.narrative.verify(self.metadata, self.events, draft)
        corrected = None
        if result.outcome is VerificationOutcome.WITHDRAWN:
            if draft.content_kind is ContentKind.LIVE and draft.candidate_id:
                self._withdrawn_candidates.add(draft.candidate_id)
                candidate = next(
                    (
                        c for c in self.analytics.candidates(self.metadata, self.events, _prefs_of(draft))
                        if c.candidate_id == draft.candidate_id
                    ),
                    None,
                )
                if candidate:
                    corrected, _ = self._live_draft(candidate, _prefs_of(draft))
            elif draft.draft_id in self._editorial:
                record = self._editorial[draft.draft_id]
                record.status = EditorialStatus.REJECTED
                record.note = "Retirado por verificación: " + "; ".join(result.issues)
                record.draft = record.draft.model_copy(update={"editorial_status": record.status})
        report = ErrorReport(
            report_id=f"report-{len(self._reports) + 1:03d}",
            draft_id=draft_id,
            message_id=message_id,
            reason=reason,
            outcome=result.outcome,
            issues=result.issues,
            corrected_draft=corrected,
            created_at=self._clock(),
        )
        self._reports.append(report)
        return report

    def reports(self) -> list[ErrorReport]:
        return list(self._reports)

    # ----- control de reproducción -------------------------------------------
    @property
    def replay(self) -> VideoSynchronizedReplay:
        if self._replay is None:
            self._replay = VideoSynchronizedReplay(
                self.events, _DiscardPublisher(), _OnDemandStateRebuilder()
            )
        return self._replay

    async def control(self, action: str, video_time_ms: int | None) -> VideoSynchronizedReplay:
        """Registra el control del reproductor con el sincronizador de Persona 1."""
        replay = self.replay
        try:
            if action == "restart":
                await replay.restart()
            elif action == "seek":
                if video_time_ms is None:
                    raise SessionError("seek necesita video_time_ms")
                await replay.seek(min(video_time_ms, self.duration_ms))
            elif action == "play":
                replay.play()
                if video_time_ms is not None:
                    await self._move(replay, video_time_ms)
            elif action == "pause":
                if video_time_ms is not None:
                    await self._move(replay, video_time_ms)
                replay.pause()
            else:
                raise SessionError(f"Acción desconocida: {action}")
        except VideoSyncError as error:
            raise SessionError(str(error)) from error
        return replay

    async def _move(self, replay: VideoSynchronizedReplay, video_time_ms: int) -> None:
        target = min(video_time_ms, self.duration_ms)
        if target >= replay.video_time_ms:
            await replay.advance_to(target)
        else:
            await replay.seek(target)

    # ----- validaciones --------------------------------------------------
    def _validate_preferences(self, preferences: ViewerPreferences) -> None:
        team_ids = {self.metadata.home_team.team_id, self.metadata.away_team.team_id}
        if preferences.favorite_team_id and preferences.favorite_team_id not in team_ids:
            raise SessionError(f"El club {preferences.favorite_team_id} no juega este partido")
        player_ids = {p.player_id for p in self.metadata.players}
        if preferences.favorite_player_id and preferences.favorite_player_id not in player_ids:
            raise SessionError(f"El jugador {preferences.favorite_player_id} no juega este partido")
        if preferences.mode is ViewerMode.PLAYER and not preferences.favorite_player_id:
            raise SessionError("El modo jugador necesita un jugador favorito")

    @staticmethod
    def _check_time(video_time_ms: int) -> None:
        if video_time_ms < 0:
            raise SessionError("video_time_ms no puede ser negativo")


class _DiscardPublisher:
    """La pantalla se calcula con ``overlays``; el sincronizador solo guarda la posición."""

    async def publish(self, event: SynchronizedEvent) -> None:
        return None


class _OnDemandStateRebuilder:
    """El estado se recalcula en cada consulta, así que no hay caché que reconstruir."""

    async def rebuild(self, events: tuple[MatchEvent, ...], *, video_time_ms: int) -> None:
        return None


def _prefs_of(draft: NarrativeDraft) -> ViewerPreferences:
    prefs: dict[str, str] = {}
    for item in draft.applied_preferences:
        key, _, value = item.partition(":")
        prefs[key] = value
    return ViewerPreferences(
        language=draft.language,
        mode=draft.mode,
        level=draft.level,
        favorite_team_id=prefs.get("favorite_team"),
        favorite_player_id=prefs.get("favorite_player"),
    )


def schedule_overlays(messages: Sequence[OverlayMessage]) -> list[OverlayMessage]:
    """Asigna una sola zona principal de pantalla (RNF-05).

    Un mensaje nuevo reemplaza al visible si su prioridad es igual o mayor. Si
    es menor, queda en el historial marcado como ``suppressed``. El resultado
    depende solo de los mensajes, así que adelantar o retroceder el vídeo
    produce siempre la misma pantalla.
    """
    ordered = sorted(messages, key=lambda m: (m.video_time_ms, -m.priority, m.message_id))
    result: list[OverlayMessage] = []
    current: int | None = None
    for message in ordered:
        start = message.video_time_ms
        visible = result[current] if current is not None else None
        if visible is not None and visible.display_until_ms > start:
            if message.priority < visible.priority:
                result.append(message.model_copy(update={"suppressed": True, "display_until_ms": start}))
                continue
            result[current] = visible.model_copy(update={"display_until_ms": start})
            message = message.model_copy(update={"replaces_message_id": visible.message_id})
        result.append(message)
        current = len(result) - 1
    return result
