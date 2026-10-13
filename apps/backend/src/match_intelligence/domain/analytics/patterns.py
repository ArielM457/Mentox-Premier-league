"""Detectores de jugadas y patrones con reglas comprobables.

Cada regla tiene versión, umbrales visibles y ejemplos positivos y negativos
en las pruebas. Un patrón solo se afirma cuando los eventos traen las
posiciones y tiempos que la regla necesita; si faltan, se registra una nota y
no se emite nada.
"""

from match_intelligence.domain.contracts import EventOutcome, EventType, MatchEvent

from .models import IndicatorComponent, MetricValue
from .pitch import FINAL_THIRD_X, PitchFrame, in_opponent_half
from .sequences import PlaySequence
from .signals import (
    NO_DETECTION,
    Detection,
    DetectionContext,
    DetectionNote,
    signal_from,
)
from .state import SHOT_ON_TARGET_OUTCOMES, is_goal, wins_ball
from .statistics import (
    EventWindow,
    is_high_recovery,
    is_progressive_pass,
    metric,
    pass_distance_m,
    team_statistics,
)

SHOT_RULE = "shot@1"
PROGRESSIVE_PASS_RULE = "progressive_pass@1"
HIGH_RECOVERY_RULE = "high_recovery@1"
FAST_PROGRESSION_RULE = "fast_progression@1"
RECOVERY_TO_SHOT_RULE = "recovery_to_shot@1"
SUSTAINED_PRESSURE_RULE = "sustained_pressure@1"

FAST_PROGRESSION_MIN_PROGRESS = 30.0
FAST_PROGRESSION_MAX_MS = 15_000
RECOVERY_TO_SHOT_MAX_MS = 15_000
PRESSURE_WINDOW_MS = 90_000
PRESSURE_MIN_ACTIONS = 5
PRESSURE_MIN_WINS = 2
INSIDE_BOX_DISTANCE_M = 16.5

DEFENSIVE_TYPES = frozenset(
    {EventType.PRESSURE, EventType.TACKLE, EventType.RECOVERY, EventType.POSSESSION_CHANGE}
)

LIMIT_ENDPOINTS = (
    "El avance se mide con los puntos de inicio y fin de cada evento; no hay seguimiento "
    "continuo del balón."
)
LIMIT_TEMPORAL = (
    "Relación temporal entre ganar el balón y el tiro; los eventos no demuestran que una "
    "acción causara la otra."
)
LIMIT_PRESSURE = (
    "Cuenta acciones defensivas registradas como eventos; no mide la distancia real entre "
    "jugadores ni la intensidad de cada presión."
)


def sequence_facts(frame: PitchFrame, sequence: PlaySequence) -> list[MetricValue]:
    """Hechos de una jugada que cualquier momento puede citar (RF-29)."""
    owner = {"team_id": sequence.team_id}
    facts = [
        metric("sequence_passes", sequence.pass_count, sequence.pass_event_ids, **owner),
        metric(
            "sequence_duration_s",
            round(sequence.duration_ms / 1000, 1),
            [sequence.event_ids[0], sequence.event_ids[-1]],
            **owner,
        ),
    ]
    if sequence.points:
        start = sequence.points[0]
        furthest = max(sequence.points, key=lambda point: point.x)
        progress = furthest.x - start.x
        sources = [start.event_id, furthest.event_id]
        facts.append(metric("forward_progress", round(progress, 1), sources, **owner))
        facts.append(
            metric("forward_progress_m", round(progress * frame.length_m / 100, 1), sources, **owner)
        )
    return facts


def _shot_geometry(frame: PitchFrame, event: MatchEvent) -> list[MetricValue]:
    point = frame.event_start(event)
    if point is None:
        return []
    owner = {"team_id": event.team_id, "player_id": event.player_id}
    return [
        metric("shot_distance_m", round(frame.goal_distance_m(point), 1), [event.event_id], **owner),
        metric("shot_angle_deg", round(frame.goal_angle_deg(point), 1), [event.event_id], **owner),
    ]


class ShotDetector:
    """Cada tiro es un momento; el gol incluye el marcador resultante."""

    rule = SHOT_RULE

    def observe(self, context: DetectionContext) -> Detection:
        event = context.event
        if event.type is not EventType.SHOT:
            return NO_DETECTION

        sequence = context.sequence
        facts: list[MetricValue] = []
        limits: list[str] = []
        magnitude = 0
        detail: list[str] = []

        if is_goal(event):
            kind = "goal"
            magnitude += 10
            detail.append("gol +10")
            for team_id in context.frame.team_ids:
                goals = context.state.goal_event_ids.get(team_id, [])
                facts.append(metric("goals", len(goals), goals, team_id=team_id))
        else:
            kind = "shot"
            on_target = event.outcome in SHOT_ON_TARGET_OUTCOMES
            if on_target:
                magnitude += 6
                detail.append("a puerta +6")
            elif event.outcome is EventOutcome.BLOCKED:
                magnitude += 3
                detail.append("bloqueado +3")
            shooter_shots = [
                e.event_id for e in context.history
                if e.type is EventType.SHOT and e.player_id and e.player_id == event.player_id
            ]
            if event.player_id:
                facts.append(
                    metric("shots", len(shooter_shots), shooter_shots,
                           team_id=event.team_id, player_id=event.player_id)
                )

        geometry = _shot_geometry(context.frame, event)
        if geometry:
            facts.extend(geometry)
            if geometry[0].value is not None and geometry[0].value <= INSIDE_BOX_DISTANCE_M:
                magnitude += 3
                detail.append("a menos de 16,5 m +3")
        else:
            limits.append("El tiro no trae posición o dirección de ataque; no hay distancia ni ángulo.")

        sources = [event.event_id]
        players: list[str] = [event.player_id] if event.player_id else []
        sequence_id = None
        if sequence is not None:
            facts.extend(sequence_facts(context.frame, sequence))
            sources.extend(sequence.all_event_ids)
            players.extend(sequence.player_ids)
            sequence_id = sequence.sequence_id
            if sequence.points:
                limits.append(LIMIT_ENDPOINTS)

        return Detection(
            signals=(
                signal_from(
                    context, kind, SHOT_RULE,
                    facts=facts, source_event_ids=sources, team_id=event.team_id,
                    player_ids=players, evidence_limits=limits, sequence_id=sequence_id,
                    magnitude=magnitude, magnitude_detail=", ".join(detail),
                ),
            )
        )


class ProgressivePassDetector:
    """Cada pase progresivo (``progressive_pass@1``) es un momento menor, útil para analistas."""

    rule = PROGRESSIVE_PASS_RULE

    def observe(self, context: DetectionContext) -> Detection:
        event = context.event
        if not is_progressive_pass(context.frame, event):
            return NO_DETECTION
        gain = context.frame.forward_gain_m(event)
        distance = pass_distance_m(context.frame, event)
        owner = {"team_id": event.team_id, "player_id": event.player_id}
        facts = [metric("pass_forward_gain_m", round(gain, 1), [event.event_id], **owner)]  # type: ignore[arg-type]
        if distance is not None:
            facts.append(metric("pass_distance_m", round(distance, 1), [event.event_id], **owner))
        players = [event.player_id] if event.player_id else []
        return Detection(
            signals=(
                signal_from(
                    context, "progressive_pass", self.rule,
                    facts=facts, source_event_ids=[event.event_id], team_id=event.team_id,
                    player_ids=players, evidence_limits=[LIMIT_ENDPOINTS],
                    sequence_id=context.sequence.sequence_id if context.sequence else None,
                    magnitude=int((gain - 10) / 5),  # type: ignore[operator]
                    magnitude_detail=f"avance de {gain:.1f} m hacia la portería rival",
                ),
            )
        )


class HighRecoveryDetector:
    """Balón ganado en campo rival (``high_recovery@1``, x' ≥ 60)."""

    rule = HIGH_RECOVERY_RULE

    def observe(self, context: DetectionContext) -> Detection:
        event = context.event
        if not is_high_recovery(context.frame, event):
            return NO_DETECTION
        point = context.frame.event_start(event)
        team_wins = [
            e.event_id for e in context.history
            if e.team_id == event.team_id and is_high_recovery(context.frame, e)
        ]
        players = [event.player_id] if event.player_id else []
        return Detection(
            signals=(
                signal_from(
                    context, "high_recovery", self.rule,
                    facts=[metric("high_recoveries", len(team_wins), team_wins, team_id=event.team_id)],
                    source_event_ids=[event.event_id], team_id=event.team_id, player_ids=players,
                    sequence_id=context.sequence.sequence_id if context.sequence else None,
                    magnitude=int((point[0] - 60) / 8),  # type: ignore[index]
                    magnitude_detail=f"balón ganado en x' = {point[0]:.0f}",  # type: ignore[index]
                ),
            )
        )


class FastProgressionDetector:
    """``fast_progression@1``: avanza ≥ 30 de x' y llega al último tercio en ≤ 15 s."""

    rule = FAST_PROGRESSION_RULE

    def __init__(self) -> None:
        self._emitted: set[str] = set()
        self._noted: set[str] = set()

    def observe(self, context: DetectionContext) -> Detection:
        sequence = context.sequence
        if sequence is None or sequence.sequence_id in self._emitted:
            return NO_DETECTION
        if context.event.event_id not in {point.event_id for point in sequence.points}:
            if (
                len(sequence.event_ids) >= 2
                and not sequence.points
                and sequence.sequence_id not in self._noted
            ):
                self._noted.add(sequence.sequence_id)
                reason = (
                    "Falta la dirección de ataque del equipo"
                    if not context.frame.has_direction(sequence.team_id, sequence.period)
                    else "La jugada no tiene posiciones"
                )
                return Detection(notes=(DetectionNote(self.rule, context.event.event_id, reason),))
            return NO_DETECTION

        start = sequence.points[0]
        reachable = [
            point for point in sequence.points
            if point.clock_ms - start.clock_ms <= FAST_PROGRESSION_MAX_MS
        ]
        furthest = max(reachable, key=lambda point: point.x)
        progress = furthest.x - start.x
        distinct_events = {point.event_id for point in reachable}
        if (
            furthest.event_id != context.event.event_id
            or progress < FAST_PROGRESSION_MIN_PROGRESS
            or furthest.x < FINAL_THIRD_X
            or len(distinct_events) < 2
        ):
            return NO_DETECTION

        self._emitted.add(sequence.sequence_id)
        duration_ms = furthest.clock_ms - start.clock_ms
        owner = {"team_id": sequence.team_id}
        sources = [start.event_id, furthest.event_id]
        facts = [
            metric("forward_progress", round(progress, 1), sources, **owner),
            metric("forward_progress_m", round(progress * context.frame.length_m / 100, 1), sources, **owner),
            metric("sequence_duration_s", round(duration_ms / 1000, 1), sources, **owner),
            metric("sequence_passes", sequence.pass_count, sequence.pass_event_ids, **owner),
        ]
        magnitude = int((progress - FAST_PROGRESSION_MIN_PROGRESS) / 5) + int(
            (FAST_PROGRESSION_MAX_MS - duration_ms) / 3_000
        )
        return Detection(
            signals=(
                signal_from(
                    context, "fast_progression", self.rule,
                    facts=facts, source_event_ids=sequence.event_ids, team_id=sequence.team_id,
                    player_ids=sequence.player_ids, evidence_limits=[LIMIT_ENDPOINTS],
                    sequence_id=sequence.sequence_id, magnitude=magnitude,
                    magnitude_detail=f"avance {progress:.1f} en {duration_ms / 1000:.1f} s",
                ),
            )
        )


class RecoveryToShotDetector:
    """``recovery_to_shot@1``: la jugada empieza ganando el balón y acaba en tiro en ≤ 15 s."""

    rule = RECOVERY_TO_SHOT_RULE

    def observe(self, context: DetectionContext) -> Detection:
        event = context.event
        sequence = context.sequence
        if event.type is not EventType.SHOT or sequence is None:
            return NO_DETECTION
        if not sequence.started_by_winning_ball:
            return NO_DETECTION
        elapsed = event.clock_ms - sequence.start_clock_ms
        if elapsed > RECOVERY_TO_SHOT_MAX_MS:
            return NO_DETECTION

        first_id = sequence.event_ids[0]
        components: list[IndicatorComponent] = []
        magnitude = int((RECOVERY_TO_SHOT_MAX_MS - elapsed) / 1_500)
        first = context.history.get(first_id)
        point = context.frame.event_start(first) if first is not None else None
        if point is not None:
            components.append(
                IndicatorComponent(key="recovery_x", team_id=event.team_id,
                                   value=round(point[0], 1), unit="pitch_percent",
                                   source_event_ids=[first_id])
            )
            if in_opponent_half(point[0]):
                magnitude += 3
        facts = [
            metric("seconds_since_recovery", round(elapsed / 1000, 1), [first_id, event.event_id],
                   team_id=event.team_id, components=components),
        ]
        return Detection(
            signals=(
                signal_from(
                    context, "recovery_to_shot", self.rule,
                    facts=facts, source_event_ids=sequence.event_ids, team_id=event.team_id,
                    player_ids=sequence.player_ids, evidence_limits=[LIMIT_TEMPORAL],
                    sequence_id=sequence.sequence_id, magnitude=magnitude,
                    magnitude_detail=f"tiro {elapsed / 1000:.1f} s después de ganar el balón",
                ),
            )
        )


class SustainedPressureDetector:
    """``sustained_pressure@1``: ≥ 5 acciones defensivas en campo rival y ≥ 2 balones ganados en 90 s."""

    rule = SUSTAINED_PRESSURE_RULE

    def __init__(self) -> None:
        self._active: dict[str, bool] = {}
        self._noted: set[tuple[int, str]] = set()

    def observe(self, context: DetectionContext) -> Detection:
        event = context.event
        if event.type not in DEFENSIVE_TYPES:
            return NO_DETECTION
        team_id = event.team_id
        frame = context.frame
        if not frame.has_direction(team_id, event.period):
            key = (event.period, team_id)
            if key in self._noted:
                return NO_DETECTION
            self._noted.add(key)
            return Detection(notes=(DetectionNote(self.rule, event.event_id, "Falta la dirección de ataque del equipo"),))

        window = EventWindow.ending_at(event.period, event.clock_ms, PRESSURE_WINDOW_MS)
        actions, wins, unpositioned = self._count(frame, context.history.window(window), team_id)
        satisfied = len(actions) >= PRESSURE_MIN_ACTIONS and len(wins) >= PRESSURE_MIN_WINS
        if not satisfied:
            self._active[team_id] = False
            return NO_DETECTION
        if self._active.get(team_id):
            return NO_DETECTION
        self._active[team_id] = True

        facts = [
            metric("defensive_actions_opponent_half", len(actions), actions, team_id=team_id, window=window),
            metric("ball_wins_opponent_half", len(wins), wins, team_id=team_id, window=window),
        ]
        limits = [LIMIT_PRESSURE]
        previous = EventWindow.ending_at(event.period, window.start_clock_ms, PRESSURE_WINDOW_MS)
        if window.start_clock_ms > 0:
            previous_actions, _, _ = self._count(frame, context.history.window(previous), team_id)
            facts.append(
                metric("defensive_actions_opponent_half", len(previous_actions), previous_actions,
                       team_id=team_id, window=previous)
            )
        else:
            limits.append("No hay un tramo anterior completo en este período para comparar.")
        opponent = frame.opponent_of(team_id)
        if opponent is not None:
            opponent_stats = team_statistics(frame, context.history.window(window), opponent, window=window)
            accuracy = next(item for item in opponent_stats if item.key == "pass_accuracy")
            if accuracy.available:
                facts.append(accuracy)
        if unpositioned:
            limits.append(f"{unpositioned} acciones defensivas sin posición no se contaron.")

        counted = set(actions)
        players = [
            e.player_id for e in context.history.window(window)
            if e.event_id in counted and e.player_id
        ]
        magnitude = 2 * (len(actions) - PRESSURE_MIN_ACTIONS) + 2 * (len(wins) - PRESSURE_MIN_WINS)
        return Detection(
            signals=(
                signal_from(
                    context, "sustained_pressure", self.rule,
                    facts=facts, source_event_ids=actions, team_id=team_id, player_ids=players,
                    evidence_limits=limits, magnitude=magnitude,
                    magnitude_detail=f"{len(actions)} acciones y {len(wins)} balones ganados en 90 s",
                ),
            )
        )

    @staticmethod
    def _count(
        frame: PitchFrame, events: list[MatchEvent], team_id: str
    ) -> tuple[list[str], list[str], int]:
        actions: list[str] = []
        wins: list[str] = []
        unpositioned = 0
        for event in events:
            if event.team_id != team_id or event.type not in DEFENSIVE_TYPES:
                continue
            point = frame.event_start(event)
            if point is None:
                unpositioned += 1
                continue
            if not in_opponent_half(point[0]):
                continue
            actions.append(event.event_id)
            if wins_ball(event):
                wins.append(event.event_id)
        return actions, wins, unpositioned
