"""Analítica provisional para desarrollar la API sin esperar a Persona 2.

Calcula solo conteos directos sobre los eventos y reglas de momentos muy
simples. No implementa xT, VAEP ni xG. Se reemplaza por el módulo real de
Persona 2 a través de ``AnalyticsPort``.
"""

from collections.abc import Sequence

from match_intelligence.domain.contracts import (
    AttackDirection,
    EventOutcome,
    EventType,
    MatchEvent,
    MatchMetadata,
)
from match_intelligence.domain.presentation import (
    InsightCandidate,
    MatchSnapshot,
    MetricValue,
    ViewerMode,
    ViewerPreferences,
)

PROGRESSIVE_PASS_MIN_X = 15.0
FAVORITE_TEAM_BONUS = 10
FAVORITE_PLAYER_BONUS = 15

_POSSESSION_EVENTS = {
    EventType.PASS,
    EventType.RECOVERY,
    EventType.POSSESSION_CHANGE,
    EventType.RESTART,
}


class ProvisionalAnalytics:
    def snapshot(
        self,
        metadata: MatchMetadata,
        events: Sequence[MatchEvent],
        *,
        video_time_ms: int,
    ) -> MatchSnapshot:
        seen = [e for e in events if _video_time(e) <= video_time_ms]
        team_ids = [metadata.home_team.team_id, metadata.away_team.team_id]
        score = {team_id: 0 for team_id in team_ids}
        for event in seen:
            if event.type is EventType.SHOT and event.outcome is EventOutcome.GOAL:
                score[event.team_id] = score.get(event.team_id, 0) + 1

        possession = None
        for event in seen:
            if event.type in _POSSESSION_EVENTS and event.outcome is EventOutcome.SUCCESS:
                possession = event.team_id

        metrics: list[MetricValue] = []
        for team_id in team_ids:
            team_events = [e for e in seen if e.team_id == team_id]
            metrics.extend(_team_metrics(team_id, team_events))

        last = seen[-1] if seen else None
        return MatchSnapshot(
            match_id=metadata.match_id,
            period=last.period if last else 1,
            clock_ms=_clock_at(seen, video_time_ms),
            video_time_ms=video_time_ms,
            score=score,
            possession_team_id=possession,
            metrics=metrics,
            recent_event_ids=[e.event_id for e in seen[-5:]],
        )

    def candidates(
        self,
        metadata: MatchMetadata,
        events: Sequence[MatchEvent],
        preferences: ViewerPreferences,
    ) -> list[InsightCandidate]:
        candidates: list[InsightCandidate] = []
        by_id = {e.event_id: e for e in events}
        for event in events:
            candidate = _candidate_for(metadata, event, by_id)
            if candidate is None:
                continue
            candidates.append(_apply_preferences(candidate, preferences))
        return candidates


def _video_time(event: MatchEvent) -> int:
    return event.video_time_ms if event.video_time_ms is not None else event.clock_ms


def _clock_at(seen: list[MatchEvent], video_time_ms: int) -> int:
    """Reloj del partido estimado desde el último evento conocido."""
    if not seen:
        return 0
    last = seen[-1]
    return max(0, last.clock_ms + (video_time_ms - _video_time(last)))


def _team_metrics(team_id: str, events: list[MatchEvent]) -> list[MetricValue]:
    def ids(predicate) -> list[str]:
        return [e.event_id for e in events if predicate(e)]

    shots = ids(lambda e: e.type is EventType.SHOT)
    goals = ids(lambda e: e.type is EventType.SHOT and e.outcome is EventOutcome.GOAL)
    passes = ids(lambda e: e.type is EventType.PASS)
    completed = ids(
        lambda e: e.type is EventType.PASS and e.outcome is EventOutcome.SUCCESS
    )
    recoveries = ids(lambda e: e.type is EventType.RECOVERY)
    pressures = ids(lambda e: e.type is EventType.PRESSURE)

    metrics = [
        MetricValue(key="goals", team_id=team_id, value=len(goals), unit="count", source_event_ids=goals),
        MetricValue(key="shots", team_id=team_id, value=len(shots), unit="count", source_event_ids=shots),
        MetricValue(key="passes_attempted", team_id=team_id, value=len(passes), unit="count", source_event_ids=passes),
        MetricValue(key="passes_completed", team_id=team_id, value=len(completed), unit="count", source_event_ids=completed),
        MetricValue(key="recoveries", team_id=team_id, value=len(recoveries), unit="count", source_event_ids=recoveries),
        MetricValue(key="pressures", team_id=team_id, value=len(pressures), unit="count", source_event_ids=pressures),
    ]
    if passes:
        metrics.append(
            MetricValue(
                key="pass_accuracy",
                team_id=team_id,
                value=round(100 * len(completed) / len(passes)),
                unit="percent",
                source_event_ids=passes,
            )
        )
    else:
        metrics.append(
            MetricValue(key="pass_accuracy", team_id=team_id, value=None, available=False, unit="percent")
        )
    return metrics


def _attacks_left_to_right(metadata: MatchMetadata, event: MatchEvent) -> bool:
    for direction in metadata.attacking_directions:
        if direction.period == event.period and direction.team_id == event.team_id:
            return direction.direction is AttackDirection.LEFT_TO_RIGHT
    return True


def _chain(event: MatchEvent, by_id: dict[str, MatchEvent]) -> list[str]:
    related = [rid for rid in event.related_event_ids if rid in by_id]
    return sorted({*related, event.event_id})


def _candidate_for(
    metadata: MatchMetadata, event: MatchEvent, by_id: dict[str, MatchEvent]
) -> InsightCandidate | None:
    players = [event.player_id] if event.player_id else []

    def build(kind: str, priority: int, facts: list[MetricValue], limits: list[str] | None = None):
        source = _chain(event, by_id)
        chain_players = {by_id[eid].player_id for eid in source if by_id[eid].player_id}
        ordered_players = players + sorted(p for p in chain_players if p not in players)
        return InsightCandidate(
            candidate_id=f"moment-{event.event_id}",
            match_id=metadata.match_id,
            period=event.period,
            clock_ms=event.clock_ms,
            kind=kind,
            priority=priority,
            team_id=event.team_id,
            player_ids=ordered_players,
            facts=facts,
            source_event_ids=source,
            evidence_limits=limits or [],
        )

    if event.type is EventType.SHOT:
        if event.outcome is EventOutcome.GOAL:
            passes_before = [
                rid for rid in event.related_event_ids
                if rid in by_id and by_id[rid].type is EventType.PASS
            ]
            facts = [
                MetricValue(key="goal", team_id=event.team_id, player_id=event.player_id, value=1, unit="count", source_event_ids=[event.event_id]),
                MetricValue(key="passes_in_build_up", team_id=event.team_id, value=len(passes_before), unit="count", source_event_ids=passes_before),
            ]
            recovery = [
                rid for rid in event.related_event_ids
                if rid in by_id and by_id[rid].type is EventType.RECOVERY
            ]
            if recovery:
                seconds = (event.clock_ms - by_id[recovery[0]].clock_ms) / 1000
                facts.append(
                    MetricValue(key="seconds_since_recovery", team_id=event.team_id, value=round(seconds, 1), unit="seconds", source_event_ids=[recovery[0], event.event_id])
                )
            return build("goal", 95, facts)
        return build(
            "shot",
            70,
            [MetricValue(key="shot", team_id=event.team_id, player_id=event.player_id, value=1, unit="count", source_event_ids=[event.event_id])],
        )

    if event.type is EventType.RECOVERY:
        return build(
            "recovery",
            60,
            [MetricValue(key="recovery", team_id=event.team_id, player_id=event.player_id, value=1, unit="count", source_event_ids=[event.event_id])],
        )

    if event.type is EventType.TACKLE and event.outcome is EventOutcome.SUCCESS:
        return build(
            "turnover",
            55,
            [MetricValue(key="tackle_won", team_id=event.team_id, player_id=event.player_id, value=1, unit="count", source_event_ids=[event.event_id])],
        )

    if (
        event.type is EventType.PASS
        and event.outcome is EventOutcome.SUCCESS
        and event.start
        and event.end
    ):
        gain = event.end.x - event.start.x
        if not _attacks_left_to_right(metadata, event):
            gain = -gain
        if gain >= PROGRESSIVE_PASS_MIN_X:
            return build(
                "progressive_pass",
                45,
                [MetricValue(key="forward_progress", team_id=event.team_id, player_id=event.player_id, value=round(gain), unit="pitch_percent", source_event_ids=[event.event_id])],
                ["Progreso medido en coordenadas de campo, no en metros"],
            )

    if event.type is EventType.PRESSURE and event.outcome is EventOutcome.SUCCESS:
        return build(
            "pressure",
            40,
            [MetricValue(key="pressure", team_id=event.team_id, player_id=event.player_id, value=1, unit="count", source_event_ids=[event.event_id])],
            ["Una sola presión no demuestra un patrón sostenido"],
        )

    if event.type is EventType.FOUL:
        return build(
            "foul",
            62,
            [MetricValue(key="foul", team_id=event.team_id, player_id=event.player_id, value=1, unit="count", source_event_ids=[event.event_id])],
        )

    if event.type in {EventType.YELLOW_CARD, EventType.RED_CARD}:
        kind = "red_card" if event.type is EventType.RED_CARD else "yellow_card"
        return build(
            kind,
            92 if event.type is EventType.RED_CARD else 76,
            [MetricValue(key=kind, team_id=event.team_id, player_id=event.player_id, value=1, unit="count", source_event_ids=[event.event_id])],
        )

    if event.type is EventType.INJURY_STOPPAGE:
        return build(
            "injury_stoppage",
            68,
            [MetricValue(key="stoppage_seconds", team_id=event.team_id, player_id=event.player_id, value=event.stoppage_ms / 1_000, unit="seconds", source_event_ids=[event.event_id])],
            ["Paro sintético del escenario; no es un diagnóstico médico"],
        )
    return None


def _apply_preferences(
    candidate: InsightCandidate, preferences: ViewerPreferences
) -> InsightCandidate:
    """Ajusta la prioridad sin cambiar hechos (RF-24, RF-25)."""
    priority = candidate.priority
    if preferences.favorite_team_id and candidate.team_id == preferences.favorite_team_id:
        priority += FAVORITE_TEAM_BONUS
    if preferences.favorite_player_id and preferences.favorite_player_id in candidate.player_ids:
        priority += FAVORITE_PLAYER_BONUS
    if preferences.mode in {ViewerMode.ANALYST, ViewerMode.PROFESSIONAL_ANALYST} and candidate.kind in {"pressure", "progressive_pass"}:
        priority += 10
    return candidate.model_copy(update={"priority": min(100, priority)})
