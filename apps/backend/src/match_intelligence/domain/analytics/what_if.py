"""Lecturas «¿qué habría pasado si…?» medidas con posiciones (``what_if@1``).

Cada lectura compara el instante real de un momento con una alternativa
concreta y medible, sin predecir el resultado de la jugada:

* ``earlier_pass``: el pase un segundo antes. Espacio del pasador y del
  receptor (distancia al rival más cercano) en los dos instantes.
* ``early_shot``: el remate un segundo antes. Distancia y ángulo a la portería
  desde donde estaba el rematador y su espacio.
* ``supporting_run``: el apoyo hacia el compañero más libre. Espacio del
  compañero más cercano al poseedor frente al del más libre a menos de 25 m.
* ``keeper_steps``: el arquero 3 m más cerca del balón. Distancia al balón y a
  su línea de gol.

Las posiciones salen de un ``TrackSet`` (Persona 1 o su simulación). Las cifras
llevan su origen; con datos simulados solo muestran el método.
"""

from bisect import bisect_left
from collections.abc import Sequence
from enum import StrEnum
from math import hypot

from pydantic import BaseModel, ConfigDict, Field

from match_intelligence.domain.contracts import EventType, MatchEvent

from .models import TrackingEvidence
from .pitch import PitchFrame
from .tracking import (
    TrackedKind,
    TrackedObject,
    Track,
    TrackingFrame,
    TrackSet,
    tracking_source,
)

WHAT_IF_RULE = "what_if@1"
EARLIER_MS = 1_000
KEEPER_STEP_M = 3.0
SUPPORT_RADIUS_M = 25.0
SAMPLE_TOLERANCE_MS = 300

LIMIT_NO_PREDICTION = (
    "Compara el espacio en la alternativa; no predice cómo habría terminado la jugada."
)
LIMIT_SIMULATED = (
    "Posiciones simuladas (simulated_fixture): muestran el método, no son mediciones."
)


class WhatIfScenario(StrEnum):
    EARLIER_PASS = "earlier_pass"
    KEEPER_STEPS = "keeper_steps"
    SUPPORTING_RUN = "supporting_run"
    EARLY_SHOT = "early_shot"


class WhatIfComparison(BaseModel):
    """Una cifra en el instante real y en la alternativa."""

    model_config = ConfigDict(extra="forbid")

    key: str
    unit: str
    actual: float | None
    alternative: float | None
    player_id: str | None = None
    alternative_player_id: str | None = None


class WhatIfReading(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: WhatIfScenario
    rule_version: str = WHAT_IF_RULE
    available: bool
    unavailable_reason: str | None = None
    period: int | None = None
    actual_clock_ms: int | None = None
    alternative_clock_ms: int | None = None
    player_id: str | None = None
    source_event_ids: list[str] = Field(default_factory=list)
    comparisons: list[WhatIfComparison] = Field(default_factory=list)
    tracking_evidence: TrackingEvidence | None = None
    evidence_limits: list[str] = Field(default_factory=list)


Point = tuple[float, float]


def position_at(track: Track, period: int, clock_ms: int) -> Point | None:
    """Muestra más cercana al instante, si está a menos de 0,3 s y en el mismo período."""
    keys = [(s.period, s.clock_ms) for s in track.samples]
    index = bisect_left(keys, (period, clock_ms))
    best: tuple[int, Point] | None = None
    for candidate in (index - 1, index):
        if 0 <= candidate < len(track.samples):
            sample = track.samples[candidate]
            gap = abs(sample.clock_ms - clock_ms)
            if sample.period == period and gap <= SAMPLE_TOLERANCE_MS and (best is None or gap < best[0]):
                best = (gap, (sample.x, sample.y))
    return best[1] if best else None


def positions_at(tracks: TrackSet, period: int, clock_ms: int) -> dict[str, tuple[Track, Point]]:
    found = {}
    for track_id, track in tracks.tracks.items():
        point = position_at(track, period, clock_ms)
        if point is not None:
            found[track_id] = (track, point)
    return found


def frame_at(tracks: TrackSet, period: int, clock_ms: int, video_time_ms: int | None) -> TrackingFrame | None:
    """Las posiciones de todas las pistas en el instante, para dibujar la cancha."""
    found = positions_at(tracks, period, clock_ms)
    if not found:
        return None
    source = tracking_source(tracks)
    return TrackingFrame(
        match_id=tracks.match_id, period=period, clock_ms=clock_ms, video_time_ms=video_time_ms,
        source=source,
        objects=[
            TrackedObject(
                track_id=track.track_id, kind=track.kind, team_id=track.team_id,
                player_id=track.player_id, x_m=round(x, 2), y_m=round(y, 2),
            )
            for track, (x, y) in found.values()
        ],
    )


def _player(found: dict[str, tuple[Track, Point]], player_id: str | None) -> tuple[Track, Point] | None:
    if player_id is None:
        return None
    return next((item for item in found.values() if item[0].player_id == player_id), None)


def _space(found: dict[str, tuple[Track, Point]], team_id: str | None, point: Point) -> float | None:
    """Distancia al rival más cercano: el espacio de quien está en ``point``."""
    rivals = [
        hypot(x - point[0], y - point[1])
        for track, (x, y) in found.values()
        if track.is_person and track.team_id and track.team_id != team_id
    ]
    return round(min(rivals), 1) if rivals else None


def _attack_point(frame: PitchFrame, team_id: str, period: int, point: Point) -> Point | None:
    x = frame.attack_x(team_id, period, point[0] / frame.length_m * 100)
    if x is None:
        return None
    return (x, point[1] / frame.width_m * 100)


def _reading(
    scenario: WhatIfScenario, tracks: TrackSet, event: MatchEvent, alternative_clock_ms: int | None,
    comparisons: list[WhatIfComparison], track_ids: Sequence[str],
) -> WhatIfReading:
    clocks = [event.clock_ms] + ([alternative_clock_ms] if alternative_clock_ms is not None else [])
    limits = [LIMIT_NO_PREDICTION] + ([LIMIT_SIMULATED] if tracks.is_simulated else [])
    return WhatIfReading(
        scenario=scenario, available=True, period=event.period, actual_clock_ms=event.clock_ms,
        alternative_clock_ms=alternative_clock_ms, player_id=event.player_id,
        source_event_ids=[event.event_id], comparisons=comparisons,
        tracking_evidence=TrackingEvidence(
            source=tracks.origin, track_ids=list(dict.fromkeys(track_ids)),
            start_period=event.period, start_clock_ms=min(clocks),
            end_period=event.period, end_clock_ms=max(clocks), frames=len(clocks),
        ),
        evidence_limits=limits,
    )


def _unavailable(scenario: WhatIfScenario, reason: str) -> WhatIfReading:
    return WhatIfReading(scenario=scenario, available=False, unavailable_reason=reason)


def _earlier(event: MatchEvent) -> int | None:
    earlier = event.clock_ms - EARLIER_MS
    return earlier if earlier >= 0 else None


def earlier_pass(tracks: TrackSet, sources: Sequence[MatchEvent]) -> WhatIfReading:
    scenario = WhatIfScenario.EARLIER_PASS
    passes = [e for e in sources if e.type in {EventType.PASS, EventType.RESTART}]
    if not passes:
        return _unavailable(scenario, "El momento no incluye un pase.")
    event = passes[-1]
    earlier = _earlier(event)
    if earlier is None:
        return _unavailable(scenario, "El pase ocurre en el primer segundo del período.")
    now = positions_at(tracks, event.period, event.clock_ms)
    before = positions_at(tracks, event.period, earlier)
    passer_now, passer_before = _player(now, event.player_id), _player(before, event.player_id)
    if passer_now is None or passer_before is None:
        return _unavailable(scenario, "No hay seguimiento confirmado del pasador en esos instantes.")
    receiver_id = event.receiver_player_id or next(
        (e.player_id for e in sources if e.clock_ms > event.clock_ms and e.team_id == event.team_id
         and e.player_id and e.player_id != event.player_id),
        None,
    )
    comparisons = [WhatIfComparison(
        key="passer_space_m", unit="meters", player_id=event.player_id,
        actual=_space(now, event.team_id, passer_now[1]),
        alternative=_space(before, event.team_id, passer_before[1]),
    )]
    track_ids = [passer_now[0].track_id]
    receiver_now, receiver_before = _player(now, receiver_id), _player(before, receiver_id)
    if receiver_now is not None and receiver_before is not None:
        comparisons.append(WhatIfComparison(
            key="receiver_space_m", unit="meters", player_id=receiver_id,
            actual=_space(now, event.team_id, receiver_now[1]),
            alternative=_space(before, event.team_id, receiver_before[1]),
        ))
        track_ids.append(receiver_now[0].track_id)
    return _reading(scenario, tracks, event, earlier, comparisons, track_ids)


def early_shot(tracks: TrackSet, frame: PitchFrame, sources: Sequence[MatchEvent]) -> WhatIfReading:
    scenario = WhatIfScenario.EARLY_SHOT
    shots = [e for e in sources if e.type is EventType.SHOT]
    if not shots:
        return _unavailable(scenario, "El momento no incluye un remate.")
    event = shots[-1]
    earlier = _earlier(event)
    if earlier is None:
        return _unavailable(scenario, "El remate ocurre en el primer segundo del período.")
    now = positions_at(tracks, event.period, event.clock_ms)
    before = positions_at(tracks, event.period, earlier)
    shooter_now, shooter_before = _player(now, event.player_id), _player(before, event.player_id)
    if shooter_now is None or shooter_before is None:
        return _unavailable(scenario, "No hay seguimiento confirmado del rematador en esos instantes.")
    point_now = _attack_point(frame, event.team_id, event.period, shooter_now[1])
    point_before = _attack_point(frame, event.team_id, event.period, shooter_before[1])
    if point_now is None or point_before is None:
        return _unavailable(scenario, "Falta la dirección de ataque del equipo en ese período.")
    comparisons = [
        WhatIfComparison(
            key="shot_distance_m", unit="meters", player_id=event.player_id,
            actual=round(frame.goal_distance_m(point_now), 1),
            alternative=round(frame.goal_distance_m(point_before), 1),
        ),
        WhatIfComparison(
            key="shot_angle_deg", unit="degrees", player_id=event.player_id,
            actual=round(frame.goal_angle_deg(point_now), 1),
            alternative=round(frame.goal_angle_deg(point_before), 1),
        ),
        WhatIfComparison(
            key="shooter_space_m", unit="meters", player_id=event.player_id,
            actual=_space(now, event.team_id, shooter_now[1]),
            alternative=_space(before, event.team_id, shooter_before[1]),
        ),
    ]
    return _reading(scenario, tracks, event, earlier, comparisons, [shooter_now[0].track_id])


def supporting_run(tracks: TrackSet, event: MatchEvent) -> WhatIfReading:
    scenario = WhatIfScenario.SUPPORTING_RUN
    now = positions_at(tracks, event.period, event.clock_ms)
    carrier = _player(now, event.player_id)
    if carrier is None:
        return _unavailable(scenario, "No hay seguimiento confirmado del protagonista en ese instante.")
    cx, cy = carrier[1]
    mates = [
        (track, point, hypot(point[0] - cx, point[1] - cy))
        for track, point in now.values()
        if track.kind is TrackedKind.PLAYER and track.team_id == event.team_id
        and track.player_id and track.player_id != event.player_id
    ]
    near = [m for m in mates if m[2] <= SUPPORT_RADIUS_M]
    if not near:
        return _unavailable(scenario, "Ningún compañero estaba a menos de 25 m.")
    nearest = min(near, key=lambda m: m[2])
    freest = max(near, key=lambda m: _space(now, event.team_id, m[1]) or 0.0)
    comparisons = [
        WhatIfComparison(
            key="support_space_m", unit="meters",
            player_id=nearest[0].player_id, alternative_player_id=freest[0].player_id,
            actual=_space(now, event.team_id, nearest[1]),
            alternative=_space(now, event.team_id, freest[1]),
        ),
        WhatIfComparison(
            key="support_distance_m", unit="meters",
            player_id=nearest[0].player_id, alternative_player_id=freest[0].player_id,
            actual=round(nearest[2], 1), alternative=round(freest[2], 1),
        ),
    ]
    reading = _reading(
        scenario, tracks, event, None, comparisons,
        [carrier[0].track_id, nearest[0].track_id, freest[0].track_id],
    )
    return reading


def keeper_steps(tracks: TrackSet, frame: PitchFrame, event: MatchEvent) -> WhatIfReading:
    scenario = WhatIfScenario.KEEPER_STEPS
    defending = frame.opponent_of(event.team_id)
    now = positions_at(tracks, event.period, event.clock_ms)
    keeper = next(
        ((t, p) for t, p in now.values() if t.kind is TrackedKind.GOALKEEPER and t.team_id == defending),
        None,
    )
    ball = next((p for t, p in now.values() if t.kind is TrackedKind.BALL), None)
    if keeper is None or ball is None:
        return _unavailable(scenario, "No hay seguimiento del arquero rival o del balón en ese instante.")
    (kx, ky), (bx, by) = keeper[1], ball
    distance = hypot(bx - kx, by - ky)
    step = min(KEEPER_STEP_M, distance)
    moved = (kx + (bx - kx) / distance * step, ky + (by - ky) / distance * step) if distance else (kx, ky)
    keeper_now = _attack_point(frame, event.team_id, event.period, keeper[1])
    keeper_moved = _attack_point(frame, event.team_id, event.period, moved)
    if keeper_now is None or keeper_moved is None:
        return _unavailable(scenario, "Falta la dirección de ataque del equipo en ese período.")
    comparisons = [
        WhatIfComparison(
            key="keeper_ball_distance_m", unit="meters", player_id=keeper[0].player_id,
            actual=round(distance, 1), alternative=round(distance - step, 1),
        ),
        WhatIfComparison(
            key="keeper_goal_line_m", unit="meters", player_id=keeper[0].player_id,
            actual=round((100 - keeper_now[0]) * frame.length_m / 100, 1),
            alternative=round((100 - keeper_moved[0]) * frame.length_m / 100, 1),
        ),
    ]
    return _reading(scenario, tracks, event, None, comparisons, [keeper[0].track_id])


def what_if_readings(
    tracks: TrackSet, frame: PitchFrame, anchor: MatchEvent, sources: Sequence[MatchEvent]
) -> list[WhatIfReading]:
    """Las cuatro lecturas del laboratorio para un momento."""
    return [
        earlier_pass(tracks, sources),
        keeper_steps(tracks, frame, anchor),
        supporting_run(tracks, anchor),
        early_shot(tracks, frame, sources),
    ]
