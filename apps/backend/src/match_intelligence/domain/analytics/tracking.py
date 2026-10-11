"""Analítica de seguimiento (``tracking@1``): posiciones por cuadro en metros.

Complementa a los eventos: con posiciones sucesivas y su tiempo ya se pueden
medir velocidad, distancia, sprints, velocidad del balón, presión por cercanía
y forma del equipo, que con ``MatchEvent 1.0`` quedan no disponibles.

Las coordenadas usan el campo fijo de los eventos: ``x_m`` va de 0 a
``pitch_length_m`` en el mismo sentido que ``x`` de ``MatchEvent`` y ``y_m`` de
0 a ``pitch_width_m``. La fuente puede ser un seguimiento simulado
(``synthetic_mock``) o un modelo de vídeo (``video_model``); las cifras siempre
dicen de cuál vienen.
"""

from bisect import bisect_left, bisect_right
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from math import hypot
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from match_intelligence.domain.contracts import EventType, MatchEvent

from . import catalog
from .models import IndicatorComponent, MetricOrigin, MetricValue, TrackingEvidence

TRACKING_RULE = "tracking@1"
ALERT_RULE = "tracking_alert@1"

PLAYER_MAX_SPEED_MS = 12.0
BALL_MAX_SPEED_MS = 40.0  # 144 km/h
SPEED_WINDOW_MS = 1_000
MAX_SAMPLE_GAP_MS = 300  # pensado para 5 cuadros por segundo o más
BALL_WINDOW_MS = 200
HIGH_INTENSITY_MS = 5.5   # 19,8 km/h
SPRINT_MS = 7.0           # 25,2 km/h, sostenida al menos 1 s
SHOT_WINDOW_MS = 1_000
CONTROL_RADIUS_M = 2.0
PRESSURE_RADIUS_M = 5.0
SPEED_RECORD_KMH = 30.0
SPEED_RECORD_STEP_KMH = 1.0
DISTANCE_STEP_M = 1_000.0

LIMIT_MOCK = (
    "Seguimiento simulado a partir de los eventos sintéticos: las velocidades y distancias "
    "son de ejemplo y no se midieron en un vídeo."
)
LIMIT_VIDEO = (
    "Posiciones estimadas por un modelo de vídeo; dependen de la calidad del seguimiento y "
    "de la homografía del campo."
)
LIMIT_IDENTITY = "La pista no está asociada a un jugador confirmado; se informa por track_id."


class TrackedKind(StrEnum):
    PLAYER = "player"
    GOALKEEPER = "goalkeeper"
    REFEREE = "referee"
    BALL = "ball"


class TrackingSource(StrEnum):
    SYNTHETIC_MOCK = "synthetic_mock"
    VIDEO_MODEL = "video_model"


class TrackedObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    track_id: str = Field(min_length=1)
    kind: TrackedKind
    team_id: str | None = None
    player_id: str | None = None
    x_m: float
    y_m: float
    confidence: float | None = Field(default=None, ge=0, le=1)


class TrackingFrame(BaseModel):
    """``TrackingFrame v1``: todas las posiciones conocidas en un instante."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    match_id: str = Field(min_length=1)
    period: int = Field(ge=1, le=4)
    clock_ms: int = Field(ge=0)
    video_time_ms: int | None = Field(default=None, ge=0)
    source: TrackingSource
    objects: list[TrackedObject] = Field(default_factory=list)


class TrackingAlert(BaseModel):
    """Aviso por umbral de velocidad o distancia, con su evidencia de seguimiento."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["1"] = "1"
    alert_id: str
    match_id: str
    kind: Literal["speed_record", "distance_milestone"]
    rule_version: str = ALERT_RULE
    period: int
    clock_ms: int
    video_time_ms: int | None = None
    team_id: str | None = None
    player_id: str | None = None
    track_id: str
    source: TrackingSource
    facts: list[MetricValue]
    evidence_limits: list[str] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Sample:
    period: int
    clock_ms: int
    x: float
    y: float


@dataclass(slots=True)
class Track:
    track_id: str
    kind: TrackedKind
    team_id: str | None
    player_id: str | None
    samples: list[Sample] = field(default_factory=list)

    @property
    def is_outfield(self) -> bool:
        return self.kind is TrackedKind.PLAYER

    @property
    def is_person(self) -> bool:
        return self.kind in {TrackedKind.PLAYER, TrackedKind.GOALKEEPER}


@dataclass(frozen=True, slots=True)
class Movement:
    """Resumen de movimiento de una pista hasta un instante."""

    track: Track
    distance_m: float
    high_intensity_m: float
    top_speed_ms: float | None
    top_speed_clock: tuple[int, int] | None
    sprints: int
    discarded_segments: int
    frames: int
    start: tuple[int, int] | None
    end: tuple[int, int] | None


def build_tracks(frames: Iterable[TrackingFrame]) -> dict[str, Track]:
    tracks: dict[str, Track] = {}
    for frame in sorted(frames, key=lambda f: (f.period, f.clock_ms)):
        for item in frame.objects:
            track = tracks.get(item.track_id)
            if track is None:
                track = Track(item.track_id, item.kind, item.team_id, item.player_id)
                tracks[item.track_id] = track
            track.samples.append(Sample(frame.period, frame.clock_ms, item.x_m, item.y_m))
    return tracks


def _segments(samples: Sequence[Sample], max_speed: float):
    """Tramos consecutivos del mismo período; los saltos imposibles se marcan como no válidos.

    Un hueco de más de 0,3 s sin cuadros (la pista se perdió) no es un tramo.
    """
    for previous, current in zip(samples, samples[1:]):
        if current.period != previous.period:
            continue
        gap_ms = current.clock_ms - previous.clock_ms
        if gap_ms <= 0 or gap_ms > MAX_SAMPLE_GAP_MS:
            continue
        dt = gap_ms / 1000
        distance = hypot(current.x - previous.x, current.y - previous.y)
        yield previous, current, distance, distance / dt, distance / dt <= max_speed


def window_speeds(
    samples: Sequence[Sample], *, window_ms: int, max_speed: float
) -> list[tuple[Sample, Sample, float]]:
    """Velocidad media (recorrido / tiempo) en ventanas de al menos ``window_ms``.

    Las ventanas no cruzan períodos y no incluyen tramos descartados por imposibles.
    """
    valid = [(a, b, d) for a, b, d, _, ok in _segments(samples, max_speed) if ok]
    result: list[tuple[Sample, Sample, float]] = []
    first = 0
    path = 0.0
    for last, (_, end, length) in enumerate(valid):
        if valid[first][0].period != end.period:
            first, path = last, 0.0
        path += length
        while first < last and end.clock_ms - valid[first][1].clock_ms >= window_ms:
            path -= valid[first][2]
            first += 1
        elapsed = end.clock_ms - valid[first][0].clock_ms
        if elapsed >= window_ms:
            result.append((valid[first][0], end, path / (elapsed / 1000)))
    return result


def episodes(
    speeds: Sequence[tuple[Sample, Sample, float]], threshold: float
) -> list[list[tuple[Sample, Sample, float]]]:
    """Ventanas consecutivas por encima de un umbral, agrupadas por episodio."""
    grouped: list[list[tuple[Sample, Sample, float]]] = []
    current: list[tuple[Sample, Sample, float]] = []
    for item in speeds:
        if item[2] >= threshold:
            if current and current[-1][1].period != item[1].period:
                grouped.append(current)
                current = []
            current.append(item)
        elif current:
            grouped.append(current)
            current = []
    if current:
        grouped.append(current)
    return grouped


def movement(track: Track) -> Movement:
    max_speed = BALL_MAX_SPEED_MS if track.kind is TrackedKind.BALL else PLAYER_MAX_SPEED_MS
    distance = 0.0
    high = 0.0
    discarded = 0
    for _, _, length, speed, ok in _segments(track.samples, max_speed):
        if not ok:
            discarded += 1
            continue
        distance += length
        if speed >= HIGH_INTENSITY_MS:
            high += length
    window = BALL_WINDOW_MS if track.kind is TrackedKind.BALL else SPEED_WINDOW_MS
    speeds = window_speeds(track.samples, window_ms=window, max_speed=max_speed)
    top = max(speeds, key=lambda item: item[2]) if speeds else None
    # Cada ventana dura al menos 1 s: un episodio sobre el umbral es un sprint sostenido.
    sprints = len(episodes(speeds, SPRINT_MS)) if track.kind is not TrackedKind.BALL else 0
    samples = track.samples
    return Movement(
        track=track,
        distance_m=distance,
        high_intensity_m=high,
        top_speed_ms=top[2] if top else None,
        top_speed_clock=(top[1].period, top[1].clock_ms) if top else None,
        sprints=sprints,
        discarded_segments=discarded,
        frames=len(samples),
        start=(samples[0].period, samples[0].clock_ms) if samples else None,
        end=(samples[-1].period, samples[-1].clock_ms) if samples else None,
    )


def _evidence(
    track_ids: Sequence[str], source: TrackingSource, start: tuple[int, int] | None,
    end: tuple[int, int] | None, frames: int,
) -> TrackingEvidence:
    return TrackingEvidence(
        source=source.value,
        track_ids=list(track_ids),
        start_period=start[0] if start else None,
        start_clock_ms=start[1] if start else None,
        end_period=end[0] if end else None,
        end_clock_ms=end[1] if end else None,
        frames=frames,
    )


def tracking_metric(
    key: str, value: float | int | None, *, evidence: TrackingEvidence,
    team_id: str | None = None, player_id: str | None = None,
    source_event_ids: Sequence[str] = (), components: Sequence[IndicatorComponent] = (),
    reason: str | None = None,
) -> MetricValue:
    item = catalog.definition(key)
    return MetricValue(
        key=key, team_id=team_id, player_id=player_id, value=value,
        available=value is not None, unit=item.unit, formula_version=item.formula_version,
        source_event_ids=list(source_event_ids), origin=MetricOrigin.DERIVED,
        unavailable_reason=None if value is not None else (reason or item.when_unavailable),
        components=list(components), tracking_evidence=evidence,
    )


def frame_source(frames: Sequence[TrackingFrame]) -> TrackingSource:
    sources = {frame.source for frame in frames}
    return TrackingSource.VIDEO_MODEL if TrackingSource.VIDEO_MODEL in sources else TrackingSource.SYNTHETIC_MOCK


def player_tracking_metrics(frames: Sequence[TrackingFrame]) -> list[MetricValue]:
    """Distancia, distancia a alta intensidad, velocidad máxima y sprints por jugador."""
    source = frame_source(frames)
    results: list[MetricValue] = []
    for track in build_tracks(frames).values():
        if not track.is_person:
            continue
        summary = movement(track)
        evidence = _evidence([track.track_id], source, summary.start, summary.end, summary.frames)
        owner = {"team_id": track.team_id, "player_id": track.player_id or None}
        discarded = [IndicatorComponent(key="discarded_segments", value=summary.discarded_segments, unit="count")]
        results.extend([
            tracking_metric("distance_covered_m", round(summary.distance_m, 1), evidence=evidence,
                            components=discarded, **owner),
            tracking_metric("high_intensity_distance_m", round(summary.high_intensity_m, 1),
                            evidence=evidence, **owner),
            tracking_metric("top_speed_kmh",
                            round(summary.top_speed_ms * 3.6, 1) if summary.top_speed_ms is not None else None,
                            evidence=evidence, **owner),
            tracking_metric("sprints", summary.sprints, evidence=evidence, **owner),
        ])
    return results


def ball_tracking_metrics(
    frames: Sequence[TrackingFrame], events: Sequence[MatchEvent] = ()
) -> list[MetricValue]:
    """Velocidad máxima del balón y velocidad de cada tiro (máximo en el segundo siguiente)."""
    source = frame_source(frames)
    ball = next((t for t in build_tracks(frames).values() if t.kind is TrackedKind.BALL), None)
    if ball is None:
        return [
            tracking_metric("ball_speed_kmh", None, evidence=_evidence([], source, None, None, 0),
                            reason="El seguimiento no incluye el balón"),
        ]
    summary = movement(ball)
    evidence = _evidence([ball.track_id], source, summary.start, summary.end, summary.frames)
    results = [
        tracking_metric(
            "ball_speed_kmh",
            round(summary.top_speed_ms * 3.6, 1) if summary.top_speed_ms is not None else None,
            evidence=evidence,
        )
    ]
    speeds = window_speeds(ball.samples, window_ms=BALL_WINDOW_MS, max_speed=BALL_MAX_SPEED_MS)
    for event in events:
        if event.type is not EventType.SHOT:
            continue
        in_window = [
            speed for start, end, speed in speeds
            if start.period == event.period
            and event.clock_ms <= start.clock_ms
            and end.clock_ms <= event.clock_ms + SHOT_WINDOW_MS
        ]
        shot_evidence = _evidence(
            [ball.track_id], source, (event.period, event.clock_ms),
            (event.period, event.clock_ms + SHOT_WINDOW_MS), len(in_window),
        )
        results.append(
            tracking_metric(
                "shot_speed_kmh", round(max(in_window) * 3.6, 1) if in_window else None,
                evidence=shot_evidence, team_id=event.team_id, player_id=event.player_id,
                source_event_ids=[event.event_id],
                reason="No hay posiciones del balón en el segundo posterior al tiro",
            )
        )
    return results


def _frames_in(frames: Sequence[TrackingFrame], period: int, start_ms: int, end_ms: int) -> list[TrackingFrame]:
    return [f for f in frames if f.period == period and start_ms < f.clock_ms <= end_ms]


def team_shape_metrics(
    frames: Sequence[TrackingFrame], team_ids: Sequence[str], *,
    period: int | None = None, start_ms: int = -1, end_ms: int | None = None,
) -> list[MetricValue]:
    """Ancho, profundidad y compactación media de los jugadores de campo."""
    source = frame_source(frames)
    scoped = list(frames) if period is None else _frames_in(frames, period, start_ms, end_ms or 10**12)
    results = []
    for team_id in team_ids:
        widths, depths, spreads = [], [], []
        track_ids: set[str] = set()
        for frame in scoped:
            points = [
                o for o in frame.objects if o.team_id == team_id and o.kind is TrackedKind.PLAYER
            ]
            if len(points) < 3:
                continue
            track_ids.update(o.track_id for o in points)
            xs = [o.x_m for o in points]
            ys = [o.y_m for o in points]
            cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
            widths.append(max(ys) - min(ys))
            depths.append(max(xs) - min(xs))
            spreads.append(sum(hypot(o.x_m - cx, o.y_m - cy) for o in points) / len(points))
        evidence = _evidence(
            sorted(track_ids), source,
            (scoped[0].period, scoped[0].clock_ms) if scoped else None,
            (scoped[-1].period, scoped[-1].clock_ms) if scoped else None, len(widths),
        )
        reason = "Menos de 3 jugadores de campo seguidos por cuadro"
        for key, values in (
            ("team_width_m", widths), ("team_depth_m", depths), ("team_compactness_m", spreads)
        ):
            results.append(
                tracking_metric(key, round(sum(values) / len(values), 1) if values else None,
                                evidence=evidence, team_id=team_id, reason=reason)
            )
    return results


def ball_carrier(frame: TrackingFrame) -> tuple[TrackedObject, TrackedObject] | None:
    """Jugador a menos de 2 m del balón más cercano a él, y el balón."""
    ball = next((o for o in frame.objects if o.kind is TrackedKind.BALL), None)
    if ball is None:
        return None
    people = [o for o in frame.objects if o.kind in {TrackedKind.PLAYER, TrackedKind.GOALKEEPER} and o.team_id]
    if not people:
        return None
    nearest = min(people, key=lambda o: hypot(o.x_m - ball.x_m, o.y_m - ball.y_m))
    if hypot(nearest.x_m - ball.x_m, nearest.y_m - ball.y_m) > CONTROL_RADIUS_M:
        return None
    return nearest, ball


def pressure_metrics(frames: Sequence[TrackingFrame], team_ids: Sequence[str]) -> list[MetricValue]:
    """``pressure_proximity_share``: cuadros con el rival en control y un defensor a ≤ 5 m."""
    source = frame_source(frames)
    results = []
    for team_id in team_ids:
        controlled = 0
        pressed = 0
        nearest_distances: list[float] = []
        tracks: set[str] = set()
        for frame in frames:
            carried = ball_carrier(frame)
            if carried is None or carried[0].team_id in {team_id, None}:
                continue
            carrier = carried[0]
            defenders = [
                o for o in frame.objects
                if o.team_id == team_id and o.kind in {TrackedKind.PLAYER, TrackedKind.GOALKEEPER}
            ]
            if not defenders:
                continue
            controlled += 1
            distance, closest = min(
                (hypot(o.x_m - carrier.x_m, o.y_m - carrier.y_m), o.track_id) for o in defenders
            )
            nearest_distances.append(distance)
            if distance <= PRESSURE_RADIUS_M:
                pressed += 1
                tracks.add(closest)
        evidence = _evidence(sorted(tracks), source,
                             (frames[0].period, frames[0].clock_ms) if frames else None,
                             (frames[-1].period, frames[-1].clock_ms) if frames else None, controlled)
        reason = "El rival no tuvo el balón controlado en ningún cuadro"
        share = round(100 * pressed / controlled, 1) if controlled else None
        results.append(
            tracking_metric(
                "pressure_proximity_share", share, evidence=evidence, team_id=team_id, reason=reason,
                components=[
                    IndicatorComponent(key="frames_pressed", team_id=team_id, value=pressed, unit="count"),
                    IndicatorComponent(key="frames_opponent_control", value=controlled, unit="count"),
                ] if controlled else [],
            )
        )
        results.append(
            tracking_metric(
                "nearest_defender_m",
                round(sum(nearest_distances) / len(nearest_distances), 1) if nearest_distances else None,
                evidence=evidence, team_id=team_id, reason=reason,
            )
        )
    return results


def tracking_metrics(
    frames: Sequence[TrackingFrame], team_ids: Sequence[str], events: Sequence[MatchEvent] = ()
) -> list[MetricValue]:
    ordered = sorted(frames, key=lambda f: (f.period, f.clock_ms))
    return [
        *player_tracking_metrics(ordered),
        *ball_tracking_metrics(ordered, events),
        *team_shape_metrics(ordered, team_ids),
        *pressure_metrics(ordered, team_ids),
    ]


def tracking_alerts(frames: Sequence[TrackingFrame]) -> list[TrackingAlert]:
    """Avisos por umbral, causales: cada uno se emite en el cuadro que cruza el umbral.

    * ``speed_record``: al terminar un episodio sobre 30 km/h, si su pico supera en al
      menos 1 km/h el último récord avisado del partido.
    * ``distance_milestone``: un jugador alcanza cada 1 000 m recorridos.
    """
    ordered = sorted(frames, key=lambda f: (f.period, f.clock_ms))
    if not ordered:
        return []
    source = frame_source(ordered)
    limits = [LIMIT_MOCK if source is TrackingSource.SYNTHETIC_MOCK else LIMIT_VIDEO]
    match_id = ordered[0].match_id
    video_by_time = {(f.period, f.clock_ms): f.video_time_ms for f in ordered}
    candidates: list[tuple[tuple[int, int], TrackingAlert]] = []
    tracks = [t for t in build_tracks(ordered).values() if t.is_person]

    # Récords de velocidad: un aviso por episodio sobre 30 km/h, al terminar, con su pico.
    peaks = []
    for track in tracks:
        speeds = window_speeds(track.samples, window_ms=SPEED_WINDOW_MS, max_speed=PLAYER_MAX_SPEED_MS)
        for episode in episodes(speeds, SPEED_RECORD_KMH / 3.6):
            start, end, speed = max(episode, key=lambda item: item[2])
            closed = episode[-1][1]
            peaks.append(((closed.period, closed.clock_ms), track, start, end, speed))
    peaks.sort(key=lambda item: (item[0], item[1].track_id))
    record = None
    for when, track, start, end, speed in peaks:
        kmh = speed * 3.6
        if record is not None and kmh < record + SPEED_RECORD_STEP_KMH:
            continue
        components = (
            [IndicatorComponent(key="previous_record_kmh", value=round(record, 1), unit="km/h")]
            if record is not None else []
        )
        record = kmh
        evidence = _evidence([track.track_id], source, (start.period, start.clock_ms),
                             (end.period, end.clock_ms), 0)
        candidates.append((when, _alert(
            "speed_record", match_id, when, video_by_time.get(when), track, source, limits,
            [tracking_metric("top_speed_kmh", round(kmh, 1), evidence=evidence, team_id=track.team_id,
                             player_id=track.player_id, components=components)],
        )))

    # Hitos de distancia por jugador.
    for track in tracks:
        total = 0.0
        next_step = DISTANCE_STEP_M
        first = track.samples[0] if track.samples else None
        for previous, current, length, _, ok in _segments(track.samples, PLAYER_MAX_SPEED_MS):
            if not ok:
                continue
            total += length
            if total >= next_step:
                when = (current.period, current.clock_ms)
                evidence = _evidence([track.track_id], source,
                                     (first.period, first.clock_ms) if first else None, when, 0)
                candidates.append((when, _alert(
                    "distance_milestone", match_id, when, video_by_time.get(when), track, source, limits,
                    [tracking_metric("distance_covered_m", round(next_step), evidence=evidence,
                                     team_id=track.team_id, player_id=track.player_id)],
                )))
                next_step += DISTANCE_STEP_M
    candidates.sort(key=lambda item: (item[0], item[1].alert_id))
    return [alert for _, alert in candidates]


def _alert(
    kind: str, match_id: str, when: tuple[int, int], video_time_ms: int | None, track: Track,
    source: TrackingSource, limits: list[str], facts: list[MetricValue],
) -> TrackingAlert:
    period, clock = when
    extra = [] if track.player_id else [LIMIT_IDENTITY]
    return TrackingAlert(
        alert_id=f"alert-{kind}-{track.track_id}-p{period}-{clock}",
        match_id=match_id, kind=kind, period=period, clock_ms=clock, video_time_ms=video_time_ms,
        team_id=track.team_id, player_id=track.player_id, track_id=track.track_id,
        source=source, facts=facts, evidence_limits=limits + extra,
    )


def frames_until(frames: Sequence[TrackingFrame], period: int, clock_ms: int) -> list[TrackingFrame]:
    """Cuadros hasta un instante, sin futuros; los cuadros deben venir ordenados."""
    keys = [(f.period, f.clock_ms) for f in frames]
    return list(frames[: bisect_right(keys, (period, clock_ms))])


def frames_between(
    frames: Sequence[TrackingFrame], period: int, start_ms: int, end_ms: int
) -> list[TrackingFrame]:
    keys = [(f.period, f.clock_ms) for f in frames]
    return list(frames[bisect_left(keys, (period, start_ms)): bisect_right(keys, (period, end_ms))])


def cumulative_distance(track: Track) -> list[tuple[int, int, float]]:
    """Distancia acumulada en cada muestra, con las mismas reglas que ``distance_covered_m``."""
    max_speed = BALL_MAX_SPEED_MS if track.kind is TrackedKind.BALL else PLAYER_MAX_SPEED_MS
    if not track.samples:
        return []
    first = track.samples[0]
    totals = [(first.period, first.clock_ms, 0.0)]
    total = 0.0
    valid = {(id(a), id(b)): length for a, b, length, _, ok in _segments(track.samples, max_speed) if ok}
    for previous, current in zip(track.samples, track.samples[1:]):
        total += valid.get((id(previous), id(current)), 0.0)
        totals.append((current.period, current.clock_ms, total))
    return totals
