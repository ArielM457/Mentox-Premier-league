"""Motor de atención (``attention@1``).

Decide qué momentos merecen aparecer y deja escrito por qué. La prioridad es
una suma de puntos visibles, recortada entre 0 y 100:

* ``base_kind``: importancia del tipo de momento.
* ``measured_fact``: fuerza del hecho medido por la regla que lo detectó.
* ``combined_signals``: otras reglas que se cumplen en el mismo instante.
* ``novelty``: primer momento de ese tipo para ese equipo.
* ``repetition``: el mismo tipo para el mismo equipo se emitió hace menos de 2 min.
* Preferencias: club, jugador y modo del espectador.

Las preferencias cambian prioridad y selección, nunca los hechos ni sus
fuentes. Los goles se emiten siempre, también los del rival (RF-24).
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from .models import (
    AttentionDecision,
    AttentionOutcome,
    InsightCandidate,
    MetricValue,
    RelevanceMode,
    RelevancePreferences,
    SelectionReason,
)
from .signals import Signal

BASE_PRIORITY: dict[str, int] = {
    "goal": 80,
    "shot": 45,
    "recovery_to_shot": 50,
    "fast_progression": 50,
    "sustained_pressure": 50,
    "control_shift": 50,
    "chaos_phase": 45,
    "player_milestone": 40,
    "high_recovery": 35,
    "progressive_pass": 25,
}
KIND_RANK = tuple(BASE_PRIORITY)
ALWAYS_EMITTED = frozenset({"goal"})
ANALYTIC_KINDS = frozenset(
    {"recovery_to_shot", "fast_progression", "sustained_pressure", "control_shift",
     "chaos_phase", "player_milestone", "high_recovery", "progressive_pass"}
)
INDICATOR_KINDS = frozenset({"control_shift", "chaos_phase"})

THRESHOLDS: dict[RelevanceMode | None, int] = {
    None: 40,
    RelevanceMode.CASUAL: 50,
    RelevanceMode.ANALYST: 35,
    RelevanceMode.PLAYER: 45,
}
COOLDOWN_MS = 120_000
NOVELTY_POINTS = 10
REPETITION_POINTS = -20
COMBINED_SIGNAL_POINTS = 5
COMBINED_SIGNAL_MAX = 10
FAVORITE_TEAM_POINTS = 10
FAVORITE_PLAYER_POINTS = 15
ANALYST_POINTS = 10
CASUAL_INDICATOR_POINTS = -10
PLAYER_INVOLVED_POINTS = 20
PLAYER_NOT_INVOLVED_POINTS = -30


@dataclass(frozen=True, slots=True)
class MomentDraft:
    """Señales de un mismo evento fusionadas antes de puntuar."""

    candidate_id: str
    match_id: str
    anchor_event_id: str
    period: int
    clock_ms: int
    video_time_ms: int | None
    kind: str
    team_id: str | None
    player_ids: tuple[str, ...]
    facts: tuple[MetricValue, ...]
    source_event_ids: tuple[str, ...]
    evidence_limits: tuple[str, ...]
    sequence_id: str | None
    signals: tuple[Signal, ...]

    @property
    def primary(self) -> Signal:
        return self.signals[0]

    @property
    def signal_kinds(self) -> list[str]:
        return [signal.kind for signal in self.signals]


def _fact_key(item: MetricValue) -> tuple[object, ...]:
    return (item.key, item.team_id, item.player_id, item.window_ms, item.window_end_clock_ms)


def merge_signals(
    match_id: str, signals: Sequence[Signal], position: Callable[[str], int]
) -> list[MomentDraft]:
    """Agrupa por evento ancla; el tipo principal es el de mayor rango."""
    groups: dict[str, list[Signal]] = {}
    for signal in signals:
        groups.setdefault(signal.anchor_event_id, []).append(signal)

    moments = []
    for anchor, group in groups.items():
        ordered = sorted(
            group,
            key=lambda item: KIND_RANK.index(item.kind) if item.kind in KIND_RANK else len(KIND_RANK),
        )
        primary = ordered[0]
        facts: dict[tuple[object, ...], MetricValue] = {}
        players: list[str] = []
        sources: set[str] = set()
        limits: list[str] = []
        for signal in ordered:
            for item in signal.facts:
                facts.setdefault(_fact_key(item), item)
            players.extend(player for player in signal.player_ids if player not in players)
            sources.update(signal.source_event_ids)
            limits.extend(limit for limit in signal.evidence_limits if limit not in limits)
        moments.append(
            MomentDraft(
                candidate_id=f"moment-{anchor}",
                match_id=match_id,
                anchor_event_id=anchor,
                period=primary.period,
                clock_ms=primary.clock_ms,
                video_time_ms=primary.video_time_ms,
                kind=primary.kind,
                team_id=primary.team_id,
                player_ids=tuple(players),
                facts=tuple(facts.values()),
                source_event_ids=tuple(sorted(sources, key=position)),
                evidence_limits=tuple(limits),
                sequence_id=next((s.sequence_id for s in ordered if s.sequence_id), None),
                signals=tuple(ordered),
            )
        )
    return moments


@dataclass(frozen=True, slots=True)
class AttentionReport:
    profile: str
    candidates: tuple[InsightCandidate, ...]
    decisions: tuple[AttentionDecision, ...]

    @property
    def discarded(self) -> tuple[AttentionDecision, ...]:
        return tuple(d for d in self.decisions if d.outcome is AttentionOutcome.DISCARDED)


@dataclass(slots=True)
class AttentionEngine:
    preferences: RelevancePreferences = field(default_factory=RelevancePreferences)
    _last_emitted: dict[tuple[str, str | None], tuple[int, int]] = field(default_factory=dict)
    _seen_kinds: set[tuple[str, str | None]] = field(default_factory=set)

    @property
    def threshold(self) -> int:
        return THRESHOLDS[self.preferences.mode]

    def evaluate(self, moments: Sequence[MomentDraft]) -> AttentionReport:
        candidates: list[InsightCandidate] = []
        decisions: list[AttentionDecision] = []
        for moment in moments:
            reasons = self._score(moment)
            priority = max(0, min(100, sum(reason.points for reason in reasons)))
            emitted = moment.kind in ALWAYS_EMITTED or priority >= self.threshold
            if moment.kind in ALWAYS_EMITTED:
                reasons.append(SelectionReason(
                    code="decisive_fact", detail="Los goles se emiten siempre, también los del rival",
                ))
            elif not emitted:
                reasons.append(SelectionReason(
                    code="below_threshold",
                    detail=f"Prioridad {priority} menor que el umbral {self.threshold} del perfil",
                    params={"threshold": self.threshold},
                ))
            if emitted:
                key = (moment.kind, moment.team_id)
                self._last_emitted[key] = (moment.period, moment.clock_ms)
                self._seen_kinds.add(key)
                candidates.append(self._candidate(moment, priority, reasons))
            decisions.append(
                AttentionDecision(
                    candidate_id=moment.candidate_id,
                    match_id=moment.match_id,
                    anchor_event_id=moment.anchor_event_id,
                    period=moment.period,
                    clock_ms=moment.clock_ms,
                    kind=moment.kind,
                    team_id=moment.team_id,
                    outcome=AttentionOutcome.EMITTED if emitted else AttentionOutcome.DISCARDED,
                    priority=priority,
                    threshold=self.threshold,
                    profile=self.preferences.profile,
                    reasons=reasons,
                )
            )
        return AttentionReport(self.preferences.profile, tuple(candidates), tuple(decisions))

    def _score(self, moment: MomentDraft) -> list[SelectionReason]:
        primary = moment.primary
        reasons = [
            SelectionReason(
                code="base_kind", points=BASE_PRIORITY.get(moment.kind, 30),
                detail=f"Tipo de momento {moment.kind}", params={"rule": primary.rule_version},
            )
        ]
        if primary.magnitude:
            reasons.append(SelectionReason(
                code="measured_fact", points=primary.magnitude, detail=primary.magnitude_detail,
            ))
        extra = [signal.kind for signal in moment.signals[1:]]
        if extra:
            reasons.append(SelectionReason(
                code="combined_signals",
                points=min(COMBINED_SIGNAL_MAX, COMBINED_SIGNAL_POINTS * len(extra)),
                detail="También cumple: " + ", ".join(extra),
            ))

        key = (moment.kind, moment.team_id)
        if key not in self._seen_kinds:
            reasons.append(SelectionReason(
                code="novelty", points=NOVELTY_POINTS,
                detail="Primer momento de este tipo para este equipo",
            ))
        last = self._last_emitted.get(key)
        if last is not None and last[0] == moment.period and moment.clock_ms - last[1] < COOLDOWN_MS:
            reasons.append(SelectionReason(
                code="repetition", points=REPETITION_POINTS,
                detail="El mismo tipo de momento se emitió hace menos de 2 minutos",
                params={"since_ms": moment.clock_ms - last[1]},
            ))
        reasons.extend(self._preference_reasons(moment))
        return reasons

    def _preference_reasons(self, moment: MomentDraft) -> list[SelectionReason]:
        preferences = self.preferences
        reasons = []
        if preferences.favorite_team_id and moment.team_id == preferences.favorite_team_id:
            reasons.append(SelectionReason(
                code="favorite_team", points=FAVORITE_TEAM_POINTS, detail="Momento del club favorito",
            ))
        involved = bool(
            preferences.favorite_player_id and preferences.favorite_player_id in moment.player_ids
        )
        if involved:
            reasons.append(SelectionReason(
                code="favorite_player", points=FAVORITE_PLAYER_POINTS,
                detail="Participa el jugador favorito",
            ))
        if preferences.mode is RelevanceMode.ANALYST and moment.kind in ANALYTIC_KINDS:
            reasons.append(SelectionReason(
                code="analyst_mode", points=ANALYST_POINTS, detail="Patrón o indicador útil para analistas",
            ))
        if preferences.mode is RelevanceMode.CASUAL and moment.kind in INDICATOR_KINDS:
            reasons.append(SelectionReason(
                code="casual_mode", points=CASUAL_INDICATOR_POINTS,
                detail="Indicador propio poco prioritario para el modo casual",
            ))
        if preferences.mode is RelevanceMode.PLAYER and preferences.favorite_player_id:
            if involved:
                reasons.append(SelectionReason(
                    code="player_mode_involved", points=PLAYER_INVOLVED_POINTS,
                    detail="Modo jugador: interviene el jugador seguido",
                ))
            elif moment.kind not in ALWAYS_EMITTED:
                reasons.append(SelectionReason(
                    code="player_mode_not_involved", points=PLAYER_NOT_INVOLVED_POINTS,
                    detail="Modo jugador: el jugador seguido no interviene",
                ))
        return reasons

    @staticmethod
    def _candidate(
        moment: MomentDraft, priority: int, reasons: list[SelectionReason]
    ) -> InsightCandidate:
        return InsightCandidate(
            candidate_id=moment.candidate_id,
            match_id=moment.match_id,
            period=moment.period,
            clock_ms=moment.clock_ms,
            kind=moment.kind,
            priority=priority,
            team_id=moment.team_id,
            player_ids=list(moment.player_ids),
            facts=list(moment.facts),
            source_event_ids=list(moment.source_event_ids),
            evidence_limits=list(moment.evidence_limits),
            video_time_ms=moment.video_time_ms,
            anchor_event_id=moment.anchor_event_id,
            sequence_id=moment.sequence_id,
            signals=moment.signal_kinds,
            reasons=reasons,
        )


def select_moments(
    moments: Sequence[MomentDraft], preferences: object | None = None
) -> AttentionReport:
    """Evalúa los momentos en orden con un motor nuevo; misma entrada, misma salida."""
    engine = AttentionEngine(RelevancePreferences.from_any(preferences))
    return engine.evaluate(moments)
