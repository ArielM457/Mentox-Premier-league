"""Adaptador de filas exportadas por SoccerNet GameState/TrackLab.

El `.pklz` de TrackLab se convierte primero a JSONL dentro del contenedor del
modelo. Este módulo recibe esas filas simples, conserva equipo/dorsal como
observaciones y produce `TrackingFrame v1` solo cuando hay pista y posición de
campo válidas. Un dorsal o un `track_id` nunca se convierte en `player_id`.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from math import isfinite
from typing import Any

from match_intelligence.application.realtime_observations import VisionObservationEnvelope
from match_intelligence.domain.analytics.tracking import (
    TrackedKind,
    TrackedObject,
    TrackingFrame,
    TrackingSource,
)

_KINDS = {
    "player": TrackedKind.PLAYER,
    "goalkeeper": TrackedKind.GOALKEEPER,
    "referee": TrackedKind.REFEREE,
    "ball": TrackedKind.BALL,
}


@dataclass(frozen=True, slots=True)
class GameStateConversion:
    observations: list[VisionObservationEnvelope]
    frames: list[TrackingFrame]
    ignored_rows: int
    rows_without_pitch_position: int


def convert_gamestate_rows(
    rows: Iterable[Mapping[str, object]],
    *,
    match_id: str,
    fps: float,
    period: int,
    pitch_length_m: float,
    pitch_width_m: float,
    team_by_side: Mapping[str, str] | None = None,
    clock_at_first_frame_ms: int = 0,
    video_at_first_frame_ms: int = 0,
    produced_at: datetime | None = None,
) -> GameStateConversion:
    if fps <= 0:
        raise ValueError("fps debe ser mayor que cero")
    if pitch_length_m <= 0 or pitch_width_m <= 0:
        raise ValueError("las dimensiones del campo deben ser positivas")
    team_by_side = team_by_side or {}
    produced_at = produced_at or datetime.now(UTC)
    observations: list[VisionObservationEnvelope] = []
    grouped: dict[int, list[TrackedObject]] = defaultdict(list)
    ignored = 0
    missing_pitch = 0

    for ordinal, row in enumerate(rows):
        try:
            frame_index = int(row["frame_index"])  # type: ignore[arg-type]
        except (KeyError, TypeError, ValueError):
            ignored += 1
            continue
        if frame_index < 0:
            ignored += 1
            continue
        offset_ms = int(round(frame_index / fps * 1_000))
        role = str(row.get("role") or "other").lower()
        side = str(row.get("team")) if row.get("team") is not None else None
        track_value = row.get("track_id")
        track_id = _track_id(track_value)
        confidence = _confidence(row.get("bbox_confidence"))
        position = _pitch_position(row.get("bbox_pitch"), pitch_length_m, pitch_width_m)
        if position is None:
            missing_pitch += 1

        detection_id = str(row.get("detection_id") or ordinal)
        payload: dict[str, Any] = {
            "match_id": match_id,
            "frame_index": frame_index,
            "period": period,
            "clock_ms": clock_at_first_frame_ms + offset_ms,
            "video_time_ms": video_at_first_frame_ms + offset_ms,
            "track_id": track_id,
            "role": role,
            "team_side": side,
            "team_id": team_by_side.get(side) if side else None,
            "jersey_number": _optional_int(row.get("jersey_number")),
            "bbox_ltwh": row.get("bbox_ltwh"),
            "pitch_position_m": (
                {"x": position[0], "y": position[1]} if position is not None else None
            ),
            "bbox_confidence": confidence,
            "role_confidence": _confidence(row.get("role_confidence")),
            "jersey_confidence": _confidence(row.get("jersey_confidence")),
            "player_id": None,
            "identity_status": "unconfirmed",
        }
        observations.append(VisionObservationEnvelope(
            observation_id=f"gs-{match_id}-{detection_id}",
            source="soccernet-gamestate",
            kind="game_state_detection",
            timestamp_ms=video_at_first_frame_ms + offset_ms,
            payload=payload,
            produced_at=produced_at,
        ))

        kind = _KINDS.get(role)
        if kind is None or track_id is None or position is None:
            continue
        team_id = team_by_side.get(side) if side and kind in {
            TrackedKind.PLAYER, TrackedKind.GOALKEEPER
        } else None
        grouped[frame_index].append(TrackedObject(
            track_id=track_id,
            kind=kind,
            team_id=team_id,
            player_id=None,
            x_m=round(position[0], 3),
            y_m=round(position[1], 3),
            confidence=confidence,
        ))

    frames = []
    for frame_index in sorted(grouped):
        offset_ms = int(round(frame_index / fps * 1_000))
        frames.append(TrackingFrame(
            match_id=match_id,
            period=period,
            clock_ms=clock_at_first_frame_ms + offset_ms,
            video_time_ms=video_at_first_frame_ms + offset_ms,
            source=TrackingSource.VIDEO_MODEL,
            objects=grouped[frame_index],
        ))
    return GameStateConversion(observations, frames, ignored, missing_pitch)


def _track_id(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and not isfinite(value):
        return None
    text = str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)
    return f"trk-gs-{text}" if text else None


def _confidence(value: object) -> float | None:
    if not isinstance(value, (int, float)) or not isfinite(float(value)):
        return None
    result = float(value)
    return result if 0 <= result <= 1 else None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if 0 <= number <= 99 else None


def _pitch_position(value: object, length: float, width: float) -> tuple[float, float] | None:
    if not isinstance(value, Mapping):
        return None
    try:
        centered_x = float(value["x_bottom_middle"])  # type: ignore[arg-type]
        centered_y = float(value["y_bottom_middle"])  # type: ignore[arg-type]
    except (KeyError, TypeError, ValueError):
        return None
    if not isfinite(centered_x) or not isfinite(centered_y):
        return None
    x = centered_x + length / 2
    y = centered_y + width / 2
    if not (0 <= x <= length and 0 <= y <= width):
        return None
    return x, y
