"""Conversión de detecciones de Roboflow Sports a ``TrackingFrame v1``.

El ejemplo de fútbol de Roboflow Sports detecta jugadores, porteros, árbitros
y balón, los sigue con ``tracker_id``, clasifica a los jugadores en dos grupos
por equipo y proyecta las posiciones al campo con una homografía. Este
adaptador recibe esas detecciones ya proyectadas, una por fila::

    {"frame_index": 120, "fps": 25.0, "tracker_id": 7, "class_name": "player",
     "team": 0, "pitch_x": 4210.5, "pitch_y": 3120.0, "confidence": 0.91}

``pitch_x`` y ``pitch_y`` están en las unidades de la configuración del campo
de Roboflow (por defecto 12 000 × 7 000). El formato de fila es una propuesta
para el script de exportación de Persona 1 (DV-US-19) y debe confirmarse con
la revisión fijada de Roboflow Sports.

Reglas:

* El grupo de equipo del clasificador (0 o 1) es arbitrario: hay que indicar
  a qué ``team_id`` corresponde cada grupo.
* No se asigna ``player_id``: un ``tracker_id`` no identifica a un jugador
  (DV-US-12). La analítica informa por pista.
* Las clases desconocidas se ignoran y se cuentan.
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from match_intelligence.domain.analytics.tracking import (
    TrackedKind,
    TrackedObject,
    TrackingFrame,
    TrackingSource,
)

ROBOFLOW_PITCH_LENGTH = 12_000.0
ROBOFLOW_PITCH_WIDTH = 7_000.0

_KINDS = {
    "player": TrackedKind.PLAYER,
    "goalkeeper": TrackedKind.GOALKEEPER,
    "referee": TrackedKind.REFEREE,
    "ball": TrackedKind.BALL,
}


@dataclass(frozen=True, slots=True)
class RoboflowConversion:
    frames: list[TrackingFrame]
    ignored_rows: int


def frames_from_roboflow(
    rows: Iterable[Mapping[str, object]],
    *,
    match_id: str,
    period: int,
    pitch_length_m: float,
    pitch_width_m: float,
    team_by_group: Mapping[int, str],
    clock_at_first_frame_ms: int = 0,
    video_at_first_frame_ms: int = 0,
    config_length: float = ROBOFLOW_PITCH_LENGTH,
    config_width: float = ROBOFLOW_PITCH_WIDTH,
) -> RoboflowConversion:
    grouped: dict[int, list[TrackedObject]] = defaultdict(list)
    fps_by_frame: dict[int, float] = {}
    ignored = 0
    for row in rows:
        kind = _KINDS.get(str(row.get("class_name", "")))
        try:
            frame_index = int(row["frame_index"])  # type: ignore[arg-type]
            fps = float(row["fps"])  # type: ignore[arg-type]
            x = float(row["pitch_x"]) / config_length * pitch_length_m  # type: ignore[arg-type]
            y = float(row["pitch_y"]) / config_width * pitch_width_m  # type: ignore[arg-type]
        except (KeyError, TypeError, ValueError):
            ignored += 1
            continue
        if kind is None or fps <= 0:
            ignored += 1
            continue
        group = row.get("team")
        team_id = team_by_group.get(int(group)) if isinstance(group, int) and kind in {
            TrackedKind.PLAYER, TrackedKind.GOALKEEPER
        } else None
        tracker = row.get("tracker_id")
        track_id = "trk-ball" if kind is TrackedKind.BALL else f"trk-rf-{tracker}"
        confidence = row.get("confidence")
        grouped[frame_index].append(TrackedObject(
            track_id=track_id, kind=kind, team_id=team_id, player_id=None,
            x_m=round(x, 2), y_m=round(y, 2),
            confidence=float(confidence) if isinstance(confidence, (int, float)) else None,
        ))
        fps_by_frame[frame_index] = fps

    frames = []
    for frame_index in sorted(grouped):
        offset_ms = int(round(frame_index / fps_by_frame[frame_index] * 1000))
        frames.append(TrackingFrame(
            match_id=match_id, period=period,
            clock_ms=clock_at_first_frame_ms + offset_ms,
            video_time_ms=video_at_first_frame_ms + offset_ms,
            source=TrackingSource.VIDEO_MODEL,
            objects=_one_ball(grouped[frame_index]),
        ))
    return RoboflowConversion(frames=frames, ignored_rows=ignored)


def _one_ball(objects: list[TrackedObject]) -> list[TrackedObject]:
    """Si el detector ve varios balones, se queda con el de mayor confianza."""
    balls = [o for o in objects if o.kind is TrackedKind.BALL]
    if len(balls) <= 1:
        return objects
    best = max(balls, key=lambda o: o.confidence or 0.0)
    return [o for o in objects if o.kind is not TrackedKind.BALL] + [best]
