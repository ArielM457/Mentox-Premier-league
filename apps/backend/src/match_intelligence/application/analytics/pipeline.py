"""Análisis reproducible de un partido: estado, jugadas, señales y momentos.

``MatchAnalyzer`` recorre los eventos en orden deportivo y ejecuta detectores
causales. ``build_snapshot`` calcula ``MatchSnapshot v1`` desde los eventos
de un prefijo. ``MatchAnalytics`` implementa el ``AnalyticsPort`` de Persona 4
(``snapshot`` y ``candidates``) y reutiliza el análisis cuando la lista de
eventos crece o retrocede, porque los momentos de un prefijo son exactamente
los anclados en eventos de ese prefijo.
"""

from collections import OrderedDict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from threading import Lock

from match_intelligence.domain.analytics.attention import (
    AttentionReport,
    MomentDraft,
    merge_signals,
    select_moments,
)
from match_intelligence.domain.analytics.indicators import (
    CHAOS_WINDOW_MS,
    CONTROL_WINDOW_MS,
    ChaosPhaseDetector,
    ControlShiftDetector,
    chaos_index,
    control_index,
    momentum_index,
)
from match_intelligence.domain.analytics.milestones import MilestoneDetector
from match_intelligence.domain.analytics.situations import SituationDetector
from match_intelligence.domain.analytics.models import (
    InsightCandidate,
    MatchSnapshot,
    MetricValue,
)
from match_intelligence.domain.analytics.patterns import (
    FastProgressionDetector,
    HighRecoveryDetector,
    ProgressivePassDetector,
    RecoveryToShotDetector,
    ShotDetector,
    SustainedPressureDetector,
)
from match_intelligence.domain.analytics.pitch import PitchFrame
from match_intelligence.domain.analytics.sequences import PlaySequence, SequenceBuilder
from match_intelligence.domain.analytics.signals import (
    DetectionContext,
    DetectionNote,
    Detector,
    EventHistory,
    Signal,
)
from match_intelligence.domain.analytics.state import MatchState, chronological
from match_intelligence.domain.analytics.tracking import TrackSet, tracking_metrics
from match_intelligence.domain.analytics.statistics import (
    EventWindow,
    player_statistics,
    possession_statistics,
    team_statistics,
    unavailable_speed_metrics,
)
from match_intelligence.domain.contracts import EventType, MatchEvent, MatchMetadata

from .value_models import ValueModelName, ValueModelRegistry

RECENT_EVENTS = 5
TRACKING_REPLACES = frozenset({"ball_speed_kmh", "shot_speed_kmh", "distance_covered_m"})
TrackingProvider = Callable[[MatchMetadata], TrackSet | None]


def default_detectors() -> list[Detector]:
    return [
        ShotDetector(),
        RecoveryToShotDetector(),
        FastProgressionDetector(),
        SustainedPressureDetector(),
        MilestoneDetector(),
        ControlShiftDetector(),
        ChaosPhaseDetector(),
        HighRecoveryDetector(),
        ProgressivePassDetector(),
        SituationDetector(),
    ]


class AnalyzerOrderError(ValueError):
    """El analizador incremental recibió un evento anterior al último aplicado."""


@dataclass(frozen=True, slots=True)
class ExcludedEvent:
    event_id: str
    reason: str


def exclusion_reason(frame: PitchFrame, event: MatchEvent) -> str | None:
    """Eventos que no pueden contarse sin inventar una relación con el partido."""
    if event.match_id != frame.match_id:
        return f"Pertenece al partido {event.match_id}"
    if event.team_id not in frame.team_ids:
        return f"El equipo {event.team_id} no figura en los metadatos"
    known_team = frame.player_teams.get(event.player_id) if event.player_id else None
    if known_team is not None and known_team != event.team_id:
        return f"El jugador {event.player_id} pertenece a {known_team} según los metadatos"
    return None


class MatchAnalyzer:
    """Análisis incremental y causal, independiente de las preferencias."""

    def __init__(
        self,
        metadata: MatchMetadata,
        *,
        value_models: ValueModelRegistry | None = None,
        detectors: Callable[[], list[Detector]] = default_detectors,
    ) -> None:
        self.metadata = metadata
        self.frame = PitchFrame.from_metadata(metadata)
        self.state = MatchState(match_id=metadata.match_id, team_ids=self.frame.team_ids)
        self.history = EventHistory()
        self.value_models = value_models or ValueModelRegistry()
        self._builder = SequenceBuilder(self.frame)
        self._detectors = detectors()
        self._fed: list[MatchEvent] = []
        self._fed_index: dict[str, int] = {}
        self._signals: list[Signal] = []
        self._moments: list[MomentDraft] = []
        self._notes: list[DetectionNote] = []
        self._excluded: list[ExcludedEvent] = []

    @property
    def fed(self) -> Sequence[MatchEvent]:
        return self._fed

    @property
    def signals(self) -> tuple[Signal, ...]:
        return tuple(self._signals)

    @property
    def notes(self) -> tuple[DetectionNote, ...]:
        return tuple(self._notes)

    @property
    def excluded(self) -> tuple[ExcludedEvent, ...]:
        return tuple(self._excluded)

    @property
    def sequences(self) -> tuple[PlaySequence, ...]:
        current = self._builder.current
        return self._builder.closed + ((current,) if current is not None else ())

    def moments(self, *, limit: int | None = None) -> list[MomentDraft]:
        """Momentos anclados en los primeros ``limit`` eventos recibidos."""
        if limit is None:
            return list(self._moments)
        return [m for m in self._moments if self._fed_index[m.anchor_event_id] < limit]

    def add(self, event: MatchEvent) -> tuple[MomentDraft, ...]:
        index = len(self._fed)
        self._fed.append(event)
        reason = exclusion_reason(self.frame, event)
        if reason is not None:
            self._excluded.append(ExcludedEvent(event.event_id, reason))
            return ()
        last = self.history.events[-1] if len(self.history) else None
        if last is not None and (event.period, event.clock_ms) < (last.period, last.clock_ms):
            raise AnalyzerOrderError(
                f"{event.event_id} es anterior a {last.event_id}; reconstruya el análisis"
            )
        self._fed_index[event.event_id] = index
        self.state.apply(event)
        self.history.append(event)
        update = self._builder.add(event)
        context = DetectionContext(self.frame, event, self.history, self.state, update)

        signals: list[Signal] = []
        for detector in self._detectors:
            detection = detector.observe(context)
            signals.extend(detection.signals)
            self._notes.extend(detection.notes)
        signals = [self._with_model_values(signal) for signal in signals]
        moments = merge_signals(self.metadata.match_id, signals, self.history.position)
        self._signals.extend(signals)
        self._moments.extend(moments)
        return tuple(moments)

    def extend(self, events: Sequence[MatchEvent]) -> None:
        for event in events:
            self.add(event)

    def is_prefix_of(self, events: Sequence[MatchEvent]) -> bool:
        return len(self._fed) <= len(events) and _same_prefix(self._fed, events)

    def has_prefix(self, events: Sequence[MatchEvent]) -> bool:
        return len(events) <= len(self._fed) and _same_prefix(events, self._fed)

    def attention(self, preferences: object | None = None, *, limit: int | None = None) -> AttentionReport:
        return select_moments(self.moments(limit=limit), preferences)

    def _with_model_values(self, signal: Signal) -> Signal:
        extra: list[MetricValue] = []
        anchor = self.history.get(signal.anchor_event_id)
        if anchor is None:
            return signal
        if signal.kind in {"goal", "shot"}:
            xg = self.value_models.event_metric(ValueModelName.XG, self.frame, anchor)
            if xg is not None:
                extra.append(xg)
        if signal.kind == "fast_progression":
            for event_id in signal.source_event_ids:
                event = self.history.get(event_id)
                if event is not None and event.type is EventType.PASS:
                    xt = self.value_models.event_metric(ValueModelName.XT, self.frame, event)
                    if xt is not None:
                        extra.append(xt)
        return replace(signal, facts=signal.facts + tuple(extra)) if extra else signal


def _same_prefix(shorter: Sequence[MatchEvent], longer: Sequence[MatchEvent]) -> bool:
    return all(a is b or a == b for a, b in zip(shorter, longer))


def build_snapshot(
    metadata: MatchMetadata,
    events: Sequence[MatchEvent],
    *,
    video_time_ms: int | None = None,
    value_models: ValueModelRegistry | None = None,
    state_revision: int = 0,
    late_event_ids: Sequence[str] = (),
    corrected_event_ids: Sequence[str] = (),
    tracking: TrackSet | None = None,
) -> MatchSnapshot:
    """``MatchSnapshot v1`` desde eventos en orden deportivo.

    Con ``tracking`` se calculan además las métricas de seguimiento con las muestras
    hasta el instante del snapshot; sin él, velocidad y distancia quedan no disponibles.
    """
    frame = PitchFrame.from_metadata(metadata)
    registry = value_models or ValueModelRegistry()
    accepted: list[MatchEvent] = []
    excluded: list[str] = []
    for event in chronological(events):
        if exclusion_reason(frame, event):
            excluded.append(event.event_id)
        else:
            accepted.append(event)

    state = MatchState.fold(metadata.match_id, frame.team_ids, accepted)
    history = EventHistory()
    for event in accepted:
        history.append(event)

    metrics: list[MetricValue] = []
    for team_id in frame.team_ids:
        metrics.extend(team_statistics(frame, accepted, team_id))
    metrics.extend(possession_statistics(state))
    if accepted:
        period, clock = state.period, state.clock_ms
        control = control_index(
            frame, state, history.window(EventWindow.ending_at(period, clock, CONTROL_WINDOW_MS)),
            EventWindow.ending_at(period, clock, CONTROL_WINDOW_MS),
        )
        momentum = momentum_index(frame, history, period, clock)
        chaos_window = EventWindow.ending_at(period, clock, CHAOS_WINDOW_MS)
        metrics.extend(control[team_id] for team_id in frame.team_ids)
        metrics.extend(momentum[team_id] for team_id in frame.team_ids)
        metrics.append(chaos_index(frame, state, history.window(chaos_window), chaos_window))
    metrics.extend(registry.team_metrics(frame, accepted))

    known_players = [player.player_id for player in metadata.players]
    seen_players = [e.player_id for e in accepted if e.player_id]
    for player_id in dict.fromkeys(known_players + seen_players):
        metrics.extend(player_statistics(frame, accepted, player_id))
    metrics.extend(unavailable_speed_metrics())

    last = accepted[-1] if accepted else None
    clock_ms = state.clock_ms
    if last is not None and video_time_ms is not None and last.video_time_ms is not None:
        clock_ms = last.clock_ms + max(0, video_time_ms - last.video_time_ms)

    if tracking is not None:
        seen = tracking.until(state.period, clock_ms)
        if seen.tracks:
            metrics = [m for m in metrics if m.available or m.key not in TRACKING_REPLACES]
            metrics.extend(tracking_metrics(seen, frame.team_ids, accepted))

    return MatchSnapshot(
        match_id=metadata.match_id,
        period=state.period,
        clock_ms=clock_ms,
        video_time_ms=video_time_ms if video_time_ms is not None else state.video_time_ms,
        score=dict(state.score),
        possession_team_id=state.possession_team_id,
        metrics=metrics,
        recent_event_ids=[event.event_id for event in accepted[-RECENT_EVENTS:]],
        event_count=len(accepted),
        last_event_id=last.event_id if last else None,
        last_event_clock_ms=last.clock_ms if last else None,
        state_revision=state_revision,
        late_event_ids=list(late_event_ids),
        corrected_event_ids=list(corrected_event_ids),
        excluded_event_ids=excluded,
    )


class MatchAnalytics:
    """Implementación real del ``AnalyticsPort`` de Persona 4."""

    def __init__(
        self,
        *,
        value_models: ValueModelRegistry | None = None,
        cache_size: int = 16,
        tracking_provider: TrackingProvider | None = None,
    ) -> None:
        self._value_models = value_models or ValueModelRegistry()
        self._tracking_provider = tracking_provider
        self._cache: OrderedDict[str, MatchAnalyzer] = OrderedDict()
        self._cache_size = cache_size
        self._lock = Lock()

    @property
    def value_models(self) -> ValueModelRegistry:
        return self._value_models

    def snapshot(
        self,
        metadata: MatchMetadata,
        events: Sequence[MatchEvent],
        *,
        video_time_ms: int | None = None,
    ) -> MatchSnapshot:
        tracking = self._tracking_provider(metadata) if self._tracking_provider else None
        return build_snapshot(
            metadata, events, video_time_ms=video_time_ms, value_models=self._value_models,
            tracking=tracking,
        )

    def candidates(
        self,
        metadata: MatchMetadata,
        events: Sequence[MatchEvent],
        preferences: object | None = None,
    ) -> list[InsightCandidate]:
        """Momentos emitidos para el perfil, ordenados por tiempo de partido."""
        return list(self.attention_report(metadata, events, preferences).candidates)

    def attention_report(
        self,
        metadata: MatchMetadata,
        events: Sequence[MatchEvent],
        preferences: object | None = None,
    ) -> AttentionReport:
        with self._lock:
            analyzer, limit = self._analyzer(metadata, chronological(events))
            return analyzer.attention(preferences, limit=limit)

    def sequences(
        self, metadata: MatchMetadata, events: Sequence[MatchEvent]
    ) -> list[PlaySequence]:
        analyzer = MatchAnalyzer(metadata, value_models=self._value_models)
        analyzer.extend(chronological(events))
        return list(analyzer.sequences)

    def compare_segments(
        self,
        metadata: MatchMetadata,
        events: Sequence[MatchEvent],
        team_id: str,
        segments: Sequence[EventWindow],
    ) -> list[list[MetricValue]]:
        """Estadísticas del mismo equipo en varios tramos (RF-17)."""
        frame = PitchFrame.from_metadata(metadata)
        ordered = [e for e in chronological(events) if exclusion_reason(frame, e) is None]
        return [team_statistics(frame, ordered, team_id, window=segment) for segment in segments]

    def _analyzer(
        self, metadata: MatchMetadata, ordered: list[MatchEvent]
    ) -> tuple[MatchAnalyzer, int | None]:
        cached = self._cache.get(metadata.match_id)
        if cached is not None and cached.metadata == metadata:
            if cached.is_prefix_of(ordered):
                cached.extend(ordered[len(cached.fed):])
                self._cache.move_to_end(metadata.match_id)
                return cached, None
            if cached.has_prefix(ordered):
                self._cache.move_to_end(metadata.match_id)
                return cached, len(ordered)
        analyzer = MatchAnalyzer(metadata, value_models=self._value_models)
        analyzer.extend(ordered)
        self._cache[metadata.match_id] = analyzer
        self._cache.move_to_end(metadata.match_id)
        while len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
        return analyzer, None
