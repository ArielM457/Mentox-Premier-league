"""Seguimiento simulado (mock) a partir de eventos sintéticos.

Sirve para probar la analítica de seguimiento mientras Persona 1 no entregue
observaciones reales de vídeo (DV-US-19). Produce lo mismo que entregará
Persona 1: ``VisualTrackObservation`` por pista e instante, e identidades
resueltas con su ``PlayerIdentityResolver``. No es una medición: el origen es
``PredictionOrigin.SIMULATED_FIXTURE`` y las posiciones salen de una
cinemática simple.

Modelo:

* El balón pasa por el inicio de cada evento y, en pases y tiros, viaja hasta
  su final a 16 m/s (pase) o 27 m/s (tiro), sin llegar después del evento
  siguiente.
* Cada jugador tiene una zona en el marco de ataque de su equipo. La zona se
  desplaza con el balón y avanza si su equipo tiene la posesión.
* Si entre dos eventos el balón tendría que ir a más de 32 m/s, se omite en esos
  cuadros, como cuando un seguimiento real lo pierde.
* El jugador de un evento va hacia el lugar del evento desde 4 s antes.
* Velocidad máxima de 8,5 m/s para quien va a la acción, 5,5 m/s para el resto y
  5 m/s para porteros y árbitro; aceleración máxima de 3,5 m/s².
"""

from bisect import bisect_left, bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from math import hypot
from random import Random

from match_intelligence.application.analytics.tracking_input import (
    DEFAULT_BALL_TRACK_IDS,
    TrackingInput,
)
from match_intelligence.application.vision_evaluation import PredictionOrigin
from match_intelligence.application.visual_identity import (
    ConfirmedPlayerIdentity,
    IdentityEvidenceKind,
    PlayerIdentityResolver,
    ResolvedVisualIdentity,
    VisualTrackObservation,
)
from match_intelligence.domain.analytics.pitch import PitchFrame
from match_intelligence.domain.analytics.state import MatchState, chronological
from match_intelligence.domain.analytics.tracking import TrackedKind
from match_intelligence.domain.contracts import EventType, MatchEvent, MatchMetadata, Position

BALL_TRACK_ID = next(iter(DEFAULT_BALL_TRACK_IDS))
MOCK_EVIDENCE = "mock de Persona 2: identidad asignada al generar el seguimiento simulado"

PASS_SPEED_MS = 16.0
SHOT_SPEED_MS = 27.0
ACTION_LEAD_MS = 4_000
ACTION_TAIL_MS = 400
ACTOR_MAX_MS = 8.5
PLAYER_MAX_MS = 5.5
KEEPER_MAX_MS = 5.0
MAX_ACCEL = 3.5
GAIN = 0.5
BALL_VISIBLE_MAX_MS = 32.0

# Zonas en el marco de ataque (x' hacia la portería rival, y a lo ancho).
SCENARIO_ANCHORS: dict[str, tuple[float, float]] = {
    "aurora-4": (24, 30), "aurora-5": (24, 70), "aurora-8": (42, 42), "aurora-10": (48, 64),
    "aurora-11": (62, 24), "aurora-9": (66, 50),
    "rio-5": (24, 34), "rio-6": (26, 66), "rio-8": (44, 46), "rio-10": (50, 58),
    "rio-7": (62, 72), "rio-9": (66, 46),
}
DEFAULT_ANCHORS = ((24, 32), (24, 68), (44, 44), (50, 62), (64, 28), (68, 52), (36, 50), (56, 40))


@dataclass(slots=True)
class _Body:
    track_id: str
    kind: TrackedKind
    team_id: str | None
    player_id: str | None
    anchor: tuple[float, float]
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0


def _bodies(metadata: MatchMetadata) -> list[_Body]:
    bodies: list[_Body] = []
    for team in (metadata.home_team, metadata.away_team):
        outfield = 0
        for player in [p for p in metadata.players if p.team_id == team.team_id]:
            keeper = player.shirt_number == 1
            if keeper:
                anchor = (5.0, 50.0)
            else:
                anchor = SCENARIO_ANCHORS.get(player.player_id, DEFAULT_ANCHORS[outfield % len(DEFAULT_ANCHORS)])
                outfield += 1
            bodies.append(_Body(
                track_id=f"trk-{player.player_id}",
                kind=TrackedKind.GOALKEEPER if keeper else TrackedKind.PLAYER,
                team_id=team.team_id, player_id=player.player_id, anchor=anchor,
            ))
    bodies.append(_Body("trk-ref-1", TrackedKind.UNASSIGNED, None, None, (50.0, 40.0)))
    return bodies


def _ball_keypoints(frame: PitchFrame, events: Sequence[MatchEvent]) -> list[tuple[int, float, float]]:
    keys: dict[int, tuple[float, float]] = {}
    for index, event in enumerate(events):
        if event.start is None:
            continue
        start = (event.start.x * frame.length_m / 100, event.start.y * frame.width_m / 100)
        keys[event.clock_ms] = start
        if event.end is None or event.type not in {EventType.PASS, EventType.SHOT}:
            continue
        end = (event.end.x * frame.length_m / 100, event.end.y * frame.width_m / 100)
        speed = SHOT_SPEED_MS if event.type is EventType.SHOT else PASS_SPEED_MS
        arrival = event.clock_ms + max(300, int(hypot(end[0] - start[0], end[1] - start[1]) / speed * 1000))
        if index + 1 < len(events):
            arrival = max(event.clock_ms + 100, min(arrival, events[index + 1].clock_ms - 100))
        keys[arrival] = end
    return sorted((t, x, y) for t, (x, y) in keys.items())


def _ball_at(keys: list[tuple[int, float, float]], t: int) -> tuple[float, float] | None:
    if not keys:
        return None
    if t <= keys[0][0]:
        return keys[0][1], keys[0][2]
    for (t0, x0, y0), (t1, x1, y1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            if t1 > t0 and hypot(x1 - x0, y1 - y0) / ((t1 - t0) / 1000) > BALL_VISIBLE_MAX_MS:
                return None if t0 < t < t1 else ((x0, y0) if t == t0 else (x1, y1))
            ratio = (t - t0) / (t1 - t0) if t1 > t0 else 1.0
            return x0 + (x1 - x0) * ratio, y0 + (y1 - y0) * ratio
    return keys[-1][1], keys[-1][2]


def generate_mock_tracking(
    metadata: MatchMetadata,
    events: Sequence[MatchEvent],
    *,
    hz: int = 5,
    seed: int = 11,
    tail_ms: int = 5_000,
) -> TrackingInput:
    """Observaciones deterministas a ``hz`` muestras por segundo, con el formato de Persona 1."""
    rng = Random(seed)
    pitch = PitchFrame.from_metadata(metadata)
    length, width = pitch.length_m, pitch.width_m
    step_ms = 1000 // hz
    dt = step_ms / 1000
    ordered = chronological(events)
    observations: list[VisualTrackObservation] = []
    first_seen: dict[str, VisualTrackObservation] = {}

    def observe(track_id: str, team_id: str | None, video_time_ms: int, x: float, y: float) -> None:
        observation = VisualTrackObservation(
            observation_id=f"mock-{track_id}-{video_time_ms}",
            match_id=metadata.match_id,
            video_time_ms=video_time_ms,
            track_id=track_id,
            detector_confidence=1.0,
            team_id=team_id,
            position=Position(
                x=round(min(100.0, max(0.0, x / length * 100)), 2),
                y=round(min(100.0, max(0.0, y / width * 100)), 2),
            ),
        )
        observations.append(observation)
        first_seen.setdefault(track_id, observation)

    for period in sorted({e.period for e in ordered}):
        period_events = [e for e in ordered if e.period == period]
        keys = _ball_keypoints(pitch, period_events)
        offset = next(
            (e.video_time_ms - e.clock_ms for e in period_events if e.video_time_ms is not None), None
        )
        if offset is None:
            raise ValueError(f"Los eventos del período {period} necesitan video_time_ms")
        state = MatchState(match_id=metadata.match_id, team_ids=pitch.team_ids)
        cursor = 0
        bodies = _bodies(metadata)
        actions: dict[str, tuple[list[int], list[tuple[float, float]]]] = {}
        for e in period_events:
            if e.player_id and e.start is not None:
                clocks, points = actions.setdefault(e.player_id, ([], []))
                clocks.append(e.clock_ms)
                points.append((e.start.x * length / 100, e.start.y * width / 100))
        first = True

        for t in range(0, period_events[-1].clock_ms + tail_ms + 1, step_ms):
            while cursor < len(period_events) and period_events[cursor].clock_ms <= t:
                state.apply(period_events[cursor])
                cursor += 1
            ball = _ball_at(keys, t)
            for body in bodies:
                target, limit = _target(body, pitch, period, ball, state.possession_team_id, actions, t)
                if first:
                    body.x, body.y = target
                _move(body, target, limit, dt, rng, length, width)
                observe(body.track_id, body.team_id, t + offset, body.x, body.y)
            if ball is not None:
                observe(BALL_TRACK_ID, None, t + offset, ball[0], ball[1])
            first = False

    # La identidad se resuelve con el mismo componente que usará el vídeo real (DV-US-12).
    resolver = PlayerIdentityResolver({p.player_id for p in metadata.players})
    identities: list[ResolvedVisualIdentity] = []
    for body in _bodies(metadata):
        if body.player_id is None or body.track_id not in first_seen:
            continue
        identities.append(resolver.resolve(
            first_seen[body.track_id],
            ConfirmedPlayerIdentity(
                match_id=metadata.match_id, track_id=body.track_id, player_id=body.player_id,
                evidence_kind=IdentityEvidenceKind.VERIFIED_ROSTER_MAPPING,
                evidence_reference=MOCK_EVIDENCE, verified_by="persona-2-mock",
            ),
        ))
    return TrackingInput(
        observations=tuple(observations),
        identities=tuple(identities),
        origin=PredictionOrigin.SIMULATED_FIXTURE,
        goalkeeper_player_ids=frozenset(p.player_id for p in metadata.players if p.shirt_number == 1),
    )


def _target(
    body: _Body, pitch: PitchFrame, period: int, ball: tuple[float, float] | None,
    possession: str | None, actions: dict[str, tuple[list[int], list[tuple[float, float]]]], t: int,
) -> tuple[tuple[float, float], float]:
    length, width = pitch.length_m, pitch.width_m
    if body.kind is TrackedKind.UNASSIGNED:
        if ball is None:
            return (length / 2, width / 2), KEEPER_MAX_MS
        return (min(length, max(0.0, ball[0] - 8)), min(width, max(0.0, ball[1] + 10))), KEEPER_MAX_MS

    clocks, points = actions.get(body.player_id or "", ([], []))
    left = bisect_left(clocks, t - ACTION_TAIL_MS)
    right = bisect_right(clocks, t + ACTION_LEAD_MS)
    if left < right:
        nearest = min(range(left, right), key=lambda i: abs(clocks[i] - t))
        return points[nearest], ACTOR_MAX_MS

    team = body.team_id or ""
    ball_attack_x, ball_y = 50.0, 50.0
    if ball is not None:
        ball_attack_x = pitch.attack_x(team, period, ball[0] / length * 100) or 50.0
        ball_y = ball[1] / width * 100
    anchor_x, anchor_y = body.anchor
    if body.kind is TrackedKind.GOALKEEPER:
        x_attack = min(18.0, max(1.0, anchor_x + 0.06 * (ball_attack_x - 50)))
        y = 50 + 0.2 * (ball_y - 50)
        limit = KEEPER_MAX_MS
    else:
        shift = 6.0 if possession == team else -3.0
        x_attack = min(97.0, max(3.0, anchor_x + 0.3 * (ball_attack_x - 50) + shift))
        y = min(97.0, max(3.0, anchor_y + 0.2 * (ball_y - 50)))
        limit = PLAYER_MAX_MS
    # Sin dirección conocida se supone izquierda a derecha.
    fixed_x = 100 - x_attack if pitch.attack_x(team, period, 0.0) == 100.0 else x_attack
    return (fixed_x * length / 100, y * width / 100), limit


def _move(
    body: _Body, target: tuple[float, float], limit: float, dt: float, rng: Random,
    length: float, width: float,
) -> None:
    dx, dy = target[0] - body.x, target[1] - body.y
    distance = hypot(dx, dy)
    desired = min(limit, distance * GAIN)
    want_vx, want_vy = (dx / distance * desired, dy / distance * desired) if distance > 1e-6 else (0.0, 0.0)
    change_x, change_y = want_vx - body.vx, want_vy - body.vy
    change = hypot(change_x, change_y)
    max_change = MAX_ACCEL * dt
    if change > max_change:
        change_x, change_y = change_x / change * max_change, change_y / change * max_change
    body.vx += change_x
    body.vy += change_y
    body.x = min(length, max(0.0, body.x + body.vx * dt + rng.gauss(0, 0.02)))
    body.y = min(width, max(0.0, body.y + body.vy * dt + rng.gauss(0, 0.02)))
