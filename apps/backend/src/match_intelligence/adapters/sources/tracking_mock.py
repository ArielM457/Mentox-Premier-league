"""Seguimiento simulado (mock) a partir de eventos sintéticos.

Sirve para desarrollar y probar la analítica de seguimiento mientras no haya un
vídeo permitido procesado con Roboflow Sports. No es una medición: las
posiciones salen de una cinemática simple y todos los cuadros se marcan con
``source = synthetic_mock``.

Modelo:

* El balón pasa por el inicio de cada evento y, en pases y tiros, viaja hasta
  su final a 16 m/s (pase) o 27 m/s (tiro), sin llegar después del evento
  siguiente.
* Cada jugador tiene una zona en el marco de ataque de su equipo. La zona se
  desplaza con el balón y avanza si su equipo tiene la posesión.
* Si entre dos eventos el balón tendría que ir a más de 32 m/s, se omite en esos
  cuadros, como cuando un seguimiento real lo pierde.
* El jugador de un evento va hacia el lugar del evento desde 4 s antes y el
  receptor de un pase ataca su punto de recepción.
* Faltas y lesiones conservan el balón detenido y reducen el movimiento hasta
  el reinicio indicado por los eventos.
* Velocidad máxima de 8,5 m/s para quien va a la acción, 5,5 m/s para el resto y
  5 m/s para porteros y árbitro; aceleración máxima de 3,5 m/s².
"""

from bisect import bisect_left, bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from math import hypot
from random import Random

from match_intelligence.domain.analytics.pitch import PitchFrame
from match_intelligence.domain.analytics.state import MatchState, chronological
from match_intelligence.domain.analytics.tracking import (
    TrackedKind,
    TrackedObject,
    TrackingFrame,
    TrackingSource,
)
from match_intelligence.domain.contracts import EventType, MatchEvent, MatchMetadata

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
    "aurora-2": (23, 16), "aurora-3": (18, 38), "aurora-4": (18, 62),
    "aurora-5": (23, 84), "aurora-6": (39, 50), "aurora-8": (49, 34),
    "aurora-10": (49, 66), "aurora-7": (68, 18), "aurora-9": (73, 50),
    "aurora-11": (68, 82),
    "rio-2": (23, 16), "rio-3": (18, 38), "rio-4": (18, 62),
    "rio-5": (23, 84), "rio-6": (39, 50), "rio-8": (49, 34),
    "rio-10": (49, 66), "rio-7": (68, 18), "rio-9": (73, 50),
    "rio-11": (68, 82),
}
DEFAULT_ANCHORS = (
    (23, 16), (18, 38), (18, 62), (23, 84),
    (39, 50), (49, 34), (49, 66), (68, 18), (73, 50), (68, 82),
)


@dataclass(slots=True)
class _Body:
    track_id: str
    kind: TrackedKind
    team_id: str | None
    player_id: str | None
    anchor: tuple[float, float]
    slot: int = 0
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0


def _bodies(metadata: MatchMetadata) -> list[_Body]:
    bodies: list[_Body] = []
    for team in (metadata.home_team, metadata.away_team):
        outfield = 0
        for slot, player in enumerate([p for p in metadata.players if p.team_id == team.team_id]):
            keeper = player.shirt_number == 1
            if keeper:
                anchor = (5.0, 50.0)
            else:
                anchor = SCENARIO_ANCHORS.get(player.player_id, DEFAULT_ANCHORS[outfield % len(DEFAULT_ANCHORS)])
                outfield += 1
            bodies.append(_Body(
                track_id=f"trk-{player.player_id}",
                kind=TrackedKind.GOALKEEPER if keeper else TrackedKind.PLAYER,
                team_id=team.team_id, player_id=player.player_id, anchor=anchor, slot=slot,
            ))
    bodies.append(_Body("trk-ref-1", TrackedKind.REFEREE, None, None, (50.0, 40.0)))
    return bodies


def _ball_keypoints(frame: PitchFrame, events: Sequence[MatchEvent]) -> list[tuple[int, float, float]]:
    keys: dict[int, tuple[float, float]] = {}
    for index, event in enumerate(events):
        if event.start is None:
            continue
        start = (event.start.x * frame.length_m / 100, event.start.y * frame.width_m / 100)
        keys[event.clock_ms] = start
        if event.stoppage_ms:
            keys[event.clock_ms + event.stoppage_ms] = start
        if event.end is None or event.type not in {EventType.PASS, EventType.RESTART, EventType.SHOT}:
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
) -> list[TrackingFrame]:
    """Cuadros deterministas a ``hz`` cuadros por segundo para cada período con eventos."""
    rng = Random(seed)
    pitch = PitchFrame.from_metadata(metadata)
    length, width = pitch.length_m, pitch.width_m
    step_ms = 1000 // hz
    dt = step_ms / 1000
    ordered = chronological(events)
    frames: list[TrackingFrame] = []

    for period in sorted({e.period for e in ordered}):
        period_events = [e for e in ordered if e.period == period]
        keys = _ball_keypoints(pitch, period_events)
        offset = next(
            (e.video_time_ms - e.clock_ms for e in period_events if e.video_time_ms is not None), None
        )
        state = MatchState(match_id=metadata.match_id, team_ids=pitch.team_ids)
        cursor = 0
        bodies = _bodies(metadata)
        actions: dict[str, tuple[list[int], list[tuple[float, float]]]] = {}
        receptions: dict[str, tuple[list[int], list[tuple[float, float]]]] = {}
        for e in period_events:
            if e.player_id and e.start is not None:
                clocks, points = actions.setdefault(e.player_id, ([], []))
                clocks.append(e.clock_ms)
                points.append((e.start.x * length / 100, e.start.y * width / 100))
            if e.receiver_player_id and e.end is not None:
                clocks, points = receptions.setdefault(e.receiver_player_id, ([], []))
                clocks.append(e.clock_ms + 1_000)
                points.append((e.end.x * length / 100, e.end.y * width / 100))
        first = True

        for t in range(0, period_events[-1].clock_ms + tail_ms + 1, step_ms):
            while cursor < len(period_events) and period_events[cursor].clock_ms <= t:
                state.apply(period_events[cursor])
                cursor += 1
            ball = _ball_at(keys, t)
            stoppage = next(
                (
                    e for e in reversed(period_events[:cursor])
                    if e.stoppage_ms and e.clock_ms <= t <= e.clock_ms + e.stoppage_ms
                ),
                None,
            )
            objects: list[TrackedObject] = []
            for body in bodies:
                target, limit = _target(
                    body, bodies, pitch, period, ball, state.possession_team_id,
                    actions, receptions, t
                )
                if stoppage is not None:
                    if body.player_id == stoppage.player_id:
                        target, limit = (body.x, body.y), 0.0
                    elif body.kind is not TrackedKind.REFEREE:
                        limit = min(limit, 1.2)
                if first:
                    body.x, body.y = target
                _move(body, target, limit, dt, rng, length, width)
                objects.append(TrackedObject(
                    track_id=body.track_id, kind=body.kind, team_id=body.team_id,
                    player_id=body.player_id, x_m=round(body.x, 2), y_m=round(body.y, 2),
                ))
            if ball is not None:
                objects.append(TrackedObject(
                    track_id="trk-ball", kind=TrackedKind.BALL, x_m=round(ball[0], 2), y_m=round(ball[1], 2),
                ))
            first = False
            frames.append(TrackingFrame(
                match_id=metadata.match_id, period=period, clock_ms=t,
                video_time_ms=t + offset if offset is not None else None,
                source=TrackingSource.SYNTHETIC_MOCK, objects=objects,
            ))
    return frames


def _target(
    body: _Body, bodies: Sequence[_Body], pitch: PitchFrame, period: int,
    ball: tuple[float, float] | None,
    possession: str | None,
    actions: dict[str, tuple[list[int], list[tuple[float, float]]]],
    receptions: dict[str, tuple[list[int], list[tuple[float, float]]]],
    t: int,
) -> tuple[tuple[float, float], float]:
    length, width = pitch.length_m, pitch.width_m
    if body.kind is TrackedKind.REFEREE:
        if ball is None:
            return (length / 2, width / 2), KEEPER_MAX_MS
        return (min(length, max(0.0, ball[0] - 8)), min(width, max(0.0, ball[1] + 10))), KEEPER_MAX_MS

    clocks, points = actions.get(body.player_id or "", ([], []))
    left = bisect_left(clocks, t - ACTION_TAIL_MS)
    right = bisect_right(clocks, t + ACTION_LEAD_MS)
    if left < right:
        nearest = min(range(left, right), key=lambda i: abs(clocks[i] - t))
        return points[nearest], ACTOR_MAX_MS

    receive_clocks, receive_points = receptions.get(body.player_id or "", ([], []))
    left = bisect_left(receive_clocks, t - ACTION_TAIL_MS)
    right = bisect_right(receive_clocks, t + ACTION_LEAD_MS)
    if left < right:
        nearest = min(range(left, right), key=lambda i: abs(receive_clocks[i] - t))
        return receive_points[nearest], ACTOR_MAX_MS

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
    attacks_right_to_left = pitch.attack_x(team, period, 0.0) == 100.0
    fixed_x = 100 - x_attack if attacks_right_to_left else x_attack
    base = (fixed_x * length / 100, y * width / 100)

    if ball is None or possession in {None, team}:
        return base, limit

    teammates = [
        item for item in bodies
        if item.team_id == team and item.kind is TrackedKind.PLAYER
    ]
    presser = min(teammates, key=lambda item: hypot(item.x - ball[0], item.y - ball[1]))
    if body.player_id == presser.player_id:
        own_goal_x = length if attacks_right_to_left else 0.0
        direction = 1.0 if own_goal_x > ball[0] else -1.0
        return (
            min(length, max(0.0, ball[0] + direction * 1.2)),
            min(width, max(0.0, ball[1])),
        ), PLAYER_MAX_MS

    # La línea defensiva protege su portería y toma una marca de su carril.
    # La mezcla con la posición base evita que todos persigan al mismo rival.
    if body.anchor[0] <= 49:
        opponents = [
            item for item in bodies
            if item.team_id not in {None, team}
            and item.kind is TrackedKind.PLAYER
            and (item.x != 0.0 or item.y != 0.0)
        ]
        if opponents:
            opponent = min(
                opponents,
                key=lambda item: abs(item.y - body.y) + 0.35 * hypot(item.x - body.x, item.y - body.y),
            )
            own_goal_x = length if attacks_right_to_left else 0.0
            cover_x = opponent.x + (1.8 if own_goal_x > opponent.x else -1.8)
            marked = (
                min(length, max(0.0, cover_x)),
                min(width, max(0.0, opponent.y)),
            )
            return (
                base[0] * 0.45 + marked[0] * 0.55,
                base[1] * 0.45 + marked[1] * 0.55,
            ), limit
    return base, limit


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
