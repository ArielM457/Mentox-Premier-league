"""Analítica de seguimiento (``tracking@1``): posiciones sucesivas en metros.

Complementa a los eventos: con posiciones sucesivas y su tiempo se pueden medir
velocidad, distancia, sprints, velocidad del balón, presión por cercanía y
forma del equipo, que con ``MatchEvent 1.0`` quedan no disponibles.

La entrada son las observaciones de visión de Persona 1
(``VisualTrackObservation`` con su identidad resuelta). El adaptador
``application/analytics/tracking_input.py`` las convierte en un ``TrackSet``;
este módulo solo calcula. Las coordenadas usan el campo fijo de los eventos en
metros y el origen sigue el vocabulario de Persona 1: ``simulated_fixture``
para datos de prueba y ``actual_model`` para un modelo real.
"""

from collections.abc import Sequence
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
SIMULATED_ORIGIN = "simulated_fixture"
MODEL_ORIGIN = "actual_model"
# Posiciones que el simulador MESSI genera junto a su vídeo: tampoco se miden desde vídeo.
SIMULATOR_ORIGIN = "synthetic_simulator"

PLAYER_MAX_SPEED_MS = 12.0
BALL_MAX_SPEED_MS = 40.0  # 144 km/h
SPEED_WINDOW_MS = 1_000
MAX_SAMPLE_GAP_MS = 300  # pensado para 5 muestras por segundo o más
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
LIMIT_SIMULATOR = "Posiciones del simulador MESSI; no medidas desde vídeo."
LIMIT_IDENTITY = "La pista no está asociada a un jugador confirmado; se informa por track_id."


class TrackedKind(StrEnum):
    PLAYER = "player"
    GOALKEEPER = "goalkeeper"
    # La fuente sabe que es un árbitro (por ejemplo, SoccerNet GameState).
    REFEREE = "referee"
    # Pista sin equipo de una fuente que no indica la clase (VisualTrackObservation).
    UNASSIGNED = "unassigned"
    BALL = "ball"


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
    origin: str
    facts: list[MetricValue]
    evidence_limits: list[str] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Sample:
    period: int
    clock_ms: int
    video_time_ms: int
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
    def is_person(self) -> bool:
        return self.kind in {TrackedKind.PLAYER, TrackedKind.GOALKEEPER}


@dataclass(frozen=True, slots=True)
class Instant:
    """Posiciones conocidas en un mismo instante."""

    period: int
    clock_ms: int
    video_time_ms: int
    positions: tuple[tuple[Track, float, float], ...]


@dataclass(frozen=True, slots=True)
class TrackSet:
    """Pistas de un partido en orden deportivo, listas para calcular."""

    match_id: str
    origin: str
    tracks: dict[str, Track]

    @property
    def is_simulated(self) -> bool:
        return self.origin != MODEL_ORIGIN

    @property
    def ball(self) -> Track | None:
        return next((t for t in self.tracks.values() if t.kind is TrackedKind.BALL), None)

    def until(self, period: int, clock_ms: int) -> "TrackSet":
        """Las mismas pistas sin muestras posteriores al instante (sin futuros)."""
        limit = (period, clock_ms)
        tracks = {}
        for track_id, track in self.tracks.items():
            samples = [s for s in track.samples if (s.period, s.clock_ms) <= limit]
            if samples:
                tracks[track_id] = Track(track.track_id, track.kind, track.team_id, track.player_id, samples)
        return TrackSet(self.match_id, self.origin, tracks)

    def instants(self) -> list[Instant]:
        grouped: dict[tuple[int, int], list[tuple[Track, float, float]]] = {}
        video: dict[tuple[int, int], int] = {}
        for track in self.tracks.values():
            for sample in track.samples:
                key = (sample.period, sample.clock_ms)
                grouped.setdefault(key, []).append((track, sample.x, sample.y))
                video[key] = sample.video_time_ms
        return [
            Instant(period, clock, video[(period, clock)], tuple(grouped[(period, clock)]))
            for period, clock in sorted(grouped)
        ]


class TrackingSource(StrEnum):
    """Origen de las posiciones en la vista para pantalla (vocabulario de la API)."""

    SYNTHETIC_MOCK = "synthetic_mock"
    SYNTHETIC_SIMULATOR = "synthetic_simulator"
    VIDEO_MODEL = "video_model"


_ORIGIN_BY_SOURCE = {
    TrackingSource.SYNTHETIC_MOCK: SIMULATED_ORIGIN,
    TrackingSource.SYNTHETIC_SIMULATOR: SIMULATOR_ORIGIN,
    TrackingSource.VIDEO_MODEL: MODEL_ORIGIN,
}
_SOURCE_BY_ORIGIN = {origin: source for source, origin in _ORIGIN_BY_SOURCE.items()}


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
    """``TrackingFrame v1``: posiciones de un instante para dibujar la cancha.

    Es una vista de salida de un ``TrackSet``; la entrada sigue siendo la de
    Persona 1. ``source`` traduce el origen: ``simulated_fixture`` se muestra
    como ``synthetic_mock``, ``actual_model`` como ``video_model`` y el
    simulador MESSI como ``synthetic_simulator``.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    match_id: str = Field(min_length=1)
    period: int = Field(ge=1, le=4)
    clock_ms: int = Field(ge=0)
    video_time_ms: int | None = Field(default=None, ge=0)
    source: TrackingSource
    objects: list[TrackedObject] = Field(default_factory=list)


def tracking_source(tracks: TrackSet) -> TrackingSource:
    """El origen de las pistas en el vocabulario de la API."""
    return _SOURCE_BY_ORIGIN.get(tracks.origin, TrackingSource.SYNTHETIC_MOCK)


def _limit(tracks: TrackSet) -> str:
    return {
        TrackingSource.SYNTHETIC_SIMULATOR: LIMIT_SIMULATOR,
        TrackingSource.VIDEO_MODEL: LIMIT_VIDEO,
    }.get(tracking_source(tracks), LIMIT_MOCK)


def tracking_frames(tracks: TrackSet) -> list[TrackingFrame]:
    """Un cuadro por instante, en orden deportivo, con todas las pistas visibles."""
    source = tracking_source(tracks)
    return [
        TrackingFrame(
            match_id=tracks.match_id,
            period=instant.period,
            clock_ms=instant.clock_ms,
            video_time_ms=instant.video_time_ms,
            source=source,
            objects=[
                TrackedObject(
                    track_id=track.track_id, kind=track.kind, team_id=track.team_id,
                    player_id=track.player_id, x_m=round(x, 2), y_m=round(y, 2),
                )
                for track, x, y in instant.positions
            ],
        )
        for instant in tracks.instants()
    ]


def track_set_from_frames(frames: Sequence[TrackingFrame]) -> TrackSet:
    """Inversa de ``tracking_frames``: pistas para calcular a partir de cuadros ya armados.

    Sirve a las fuentes que entregan cuadros (el simulador MESSI y SoccerNet GameState).
    Si los cuadros mezclan fuentes, prevalece el simulador y después el modelo de vídeo.
    """
    sources = {frame.source for frame in frames}
    source = next(
        (s for s in (TrackingSource.SYNTHETIC_SIMULATOR, TrackingSource.VIDEO_MODEL) if s in sources),
        TrackingSource.SYNTHETIC_MOCK,
    )
    tracks: dict[str, Track] = {}
    for frame in sorted(frames, key=lambda f: (f.period, f.clock_ms)):
        for item in frame.objects:
            track = tracks.setdefault(
                item.track_id, Track(item.track_id, item.kind, item.team_id, item.player_id or None)
            )
            track.samples.append(Sample(frame.period, frame.clock_ms, frame.video_time_ms, item.x_m, item.y_m))
    return TrackSet(frames[0].match_id if frames else "", _ORIGIN_BY_SOURCE[source], tracks)


@dataclass(frozen=True, slots=True)
class Movement:
    """Resumen de movimiento de una pista."""

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


def _segments(samples: Sequence[Sample], max_speed: float):
    """Tramos consecutivos del mismo período; los saltos imposibles se marcan como no válidos.

    Un hueco de más de 0,3 s sin muestras (la pista se perdió) no es un tramo.
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
        # No unir ventanas a través de un salto descartado o una pista perdida.
        if last and valid[last - 1][1] != valid[last][0]:
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
            if current and (
                current[-1][1].period != item[1].period
                or item[1].clock_ms - current[-1][1].clock_ms > MAX_SAMPLE_GAP_MS
            ):
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
    track_ids: Sequence[str], origin: str, start: tuple[int, int] | None,
    end: tuple[int, int] | None, frames: int,
) -> TrackingEvidence:
    return TrackingEvidence(
        source=origin,
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


def player_tracking_metrics(tracks: TrackSet) -> list[MetricValue]:
    """Distancia, distancia a alta intensidad, velocidad máxima y sprints por pista de persona."""
    results: list[MetricValue] = []
    for track in tracks.tracks.values():
        if not track.is_person:
            continue
        summary = movement(track)
        evidence = _evidence([track.track_id], tracks.origin, summary.start, summary.end, summary.frames)
        owner = {"team_id": track.team_id, "player_id": track.player_id or None}
        # Sin un tramo válido, 0 m no sería un dato sino la falta de él.
        has_segments = any(ok for _, _, _, _, ok in _segments(track.samples, PLAYER_MAX_SPEED_MS))
        missing = "No hay posiciones consecutivas válidas para medir movimiento"
        discarded = [IndicatorComponent(key="discarded_segments", value=summary.discarded_segments, unit="count")]
        results.extend([
            tracking_metric("distance_covered_m", round(summary.distance_m, 1) if has_segments else None, evidence=evidence,
                            components=discarded, reason=missing, **owner),
            tracking_metric("high_intensity_distance_m", round(summary.high_intensity_m, 1) if has_segments else None,
                            evidence=evidence, reason=missing, **owner),
            tracking_metric("top_speed_kmh",
                            round(summary.top_speed_ms * 3.6, 1) if summary.top_speed_ms is not None else None,
                            evidence=evidence, **owner),
            tracking_metric("sprints", summary.sprints if has_segments else None, evidence=evidence, reason=missing, **owner),
        ])
    return results


def ball_tracking_metrics(tracks: TrackSet, events: Sequence[MatchEvent] = ()) -> list[MetricValue]:
    """Velocidad máxima del balón y velocidad de cada tiro (máximo en el segundo siguiente)."""
    ball = tracks.ball
    if ball is None:
        return [
            tracking_metric("ball_speed_kmh", None, evidence=_evidence([], tracks.origin, None, None, 0),
                            reason="El seguimiento no incluye el balón"),
        ]
    summary = movement(ball)
    evidence = _evidence([ball.track_id], tracks.origin, summary.start, summary.end, summary.frames)
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
            [ball.track_id], tracks.origin, (event.period, event.clock_ms),
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


def team_shape_metrics(tracks: TrackSet, team_ids: Sequence[str]) -> list[MetricValue]:
    """Ancho, profundidad y compactación media de los jugadores de campo del equipo."""
    instants = tracks.instants()
    results = []
    for team_id in team_ids:
        widths, depths, spreads = [], [], []
        track_ids: set[str] = set()
        for instant in instants:
            points = [
                (track, x, y) for track, x, y in instant.positions
                if track.team_id == team_id and track.kind is TrackedKind.PLAYER
            ]
            if len(points) < 3:
                continue
            track_ids.update(track.track_id for track, _, _ in points)
            xs = [x for _, x, _ in points]
            ys = [y for _, _, y in points]
            cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
            widths.append(max(ys) - min(ys))
            depths.append(max(xs) - min(xs))
            spreads.append(sum(hypot(x - cx, y - cy) for _, x, y in points) / len(points))
        evidence = _evidence(
            sorted(track_ids), tracks.origin,
            (instants[0].period, instants[0].clock_ms) if instants else None,
            (instants[-1].period, instants[-1].clock_ms) if instants else None, len(widths),
        )
        reason = "Menos de 3 jugadores de campo seguidos por instante"
        for key, values in (
            ("team_width_m", widths), ("team_depth_m", depths), ("team_compactness_m", spreads)
        ):
            results.append(
                tracking_metric(key, round(sum(values) / len(values), 1) if values else None,
                                evidence=evidence, team_id=team_id, reason=reason)
            )
    return results


def ball_carrier(instant: Instant) -> tuple[Track, float, float] | None:
    """Persona con equipo a menos de 2 m del balón y más cercana a él."""
    ball = next(((x, y) for track, x, y in instant.positions if track.kind is TrackedKind.BALL), None)
    if ball is None:
        return None
    people = [p for p in instant.positions if p[0].is_person and p[0].team_id]
    if not people:
        return None
    nearest = min(people, key=lambda p: hypot(p[1] - ball[0], p[2] - ball[1]))
    if hypot(nearest[1] - ball[0], nearest[2] - ball[1]) > CONTROL_RADIUS_M:
        return None
    return nearest


def pressure_metrics(tracks: TrackSet, team_ids: Sequence[str]) -> list[MetricValue]:
    """``pressure_proximity_share``: instantes con el rival en control y un defensor a ≤ 5 m."""
    instants = tracks.instants()
    results = []
    for team_id in team_ids:
        controlled = 0
        pressed = 0
        nearest_distances: list[float] = []
        pressing_tracks: set[str] = set()
        for instant in instants:
            carried = ball_carrier(instant)
            if carried is None or carried[0].team_id in {team_id, None}:
                continue
            _, cx, cy = carried
            defenders = [p for p in instant.positions if p[0].team_id == team_id and p[0].is_person]
            if not defenders:
                continue
            controlled += 1
            distance, closest = min((hypot(x - cx, y - cy), track.track_id) for track, x, y in defenders)
            nearest_distances.append(distance)
            if distance <= PRESSURE_RADIUS_M:
                pressed += 1
                pressing_tracks.add(closest)
        evidence = _evidence(sorted(pressing_tracks), tracks.origin,
                             (instants[0].period, instants[0].clock_ms) if instants else None,
                             (instants[-1].period, instants[-1].clock_ms) if instants else None, controlled)
        reason = "El rival no tuvo el balón controlado en ningún instante"
        share = round(100 * pressed / controlled, 1) if controlled else None
        results.append(
            tracking_metric(
                "pressure_proximity_share", share, evidence=evidence, team_id=team_id, reason=reason,
                components=[
                    IndicatorComponent(key="instants_pressed", team_id=team_id, value=pressed, unit="count"),
                    IndicatorComponent(key="instants_opponent_control", value=controlled, unit="count"),
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
    tracks: TrackSet, team_ids: Sequence[str], events: Sequence[MatchEvent] = ()
) -> list[MetricValue]:
    return [
        *player_tracking_metrics(tracks),
        *ball_tracking_metrics(tracks, events),
        *team_shape_metrics(tracks, team_ids),
        *pressure_metrics(tracks, team_ids),
    ]


def tracking_alerts(tracks: TrackSet) -> list[TrackingAlert]:
    """Avisos por umbral, causales: cada uno se emite en la muestra que cruza el umbral.

    * ``speed_record``: al terminar un episodio sobre 30 km/h, si su pico supera en al
      menos 1 km/h el último récord avisado del partido.
    * ``distance_milestone``: un jugador alcanza cada 1 000 m recorridos.
    """
    limits = [_limit(tracks)]
    video_by_time = {
        (s.period, s.clock_ms): s.video_time_ms for t in tracks.tracks.values() for s in t.samples
    }
    candidates: list[tuple[tuple[int, int], TrackingAlert]] = []
    people = [t for t in tracks.tracks.values() if t.is_person]

    # Récords de velocidad: un aviso por episodio sobre 30 km/h, al terminar, con su pico.
    peaks = []
    for track in people:
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
        evidence = _evidence([track.track_id], tracks.origin, (start.period, start.clock_ms),
                             (end.period, end.clock_ms), 0)
        candidates.append((when, _alert(
            "speed_record", tracks, when, video_by_time.get(when), track, limits,
            [tracking_metric("top_speed_kmh", round(kmh, 1), evidence=evidence, team_id=track.team_id,
                             player_id=track.player_id, components=components)],
        )))

    # Hitos de distancia por jugador.
    for track in people:
        total = 0.0
        next_step = DISTANCE_STEP_M
        first = track.samples[0] if track.samples else None
        for _, current, length, _, ok in _segments(track.samples, PLAYER_MAX_SPEED_MS):
            if not ok:
                continue
            total += length
            if total >= next_step:
                when = (current.period, current.clock_ms)
                evidence = _evidence([track.track_id], tracks.origin,
                                     (first.period, first.clock_ms) if first else None, when, 0)
                candidates.append((when, _alert(
                    "distance_milestone", tracks, when, video_by_time.get(when), track, limits,
                    [tracking_metric("distance_covered_m", round(next_step), evidence=evidence,
                                     team_id=track.team_id, player_id=track.player_id)],
                )))
                next_step += DISTANCE_STEP_M
    candidates.sort(key=lambda item: (item[0], item[1].alert_id))
    return [alert for _, alert in candidates]


def _alert(
    kind: str, tracks: TrackSet, when: tuple[int, int], video_time_ms: int | None, track: Track,
    limits: list[str], facts: list[MetricValue],
) -> TrackingAlert:
    period, clock = when
    extra = [] if track.player_id else [LIMIT_IDENTITY]
    return TrackingAlert(
        alert_id=f"alert-{kind}-{track.track_id}-p{period}-{clock}",
        match_id=tracks.match_id, kind=kind, period=period, clock_ms=clock, video_time_ms=video_time_ms,
        team_id=track.team_id, player_id=track.player_id, track_id=track.track_id,
        origin=tracks.origin, facts=facts, evidence_limits=limits + extra,
    )


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
