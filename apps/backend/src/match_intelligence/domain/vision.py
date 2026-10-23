"""Contratos persistibles para observaciones de SoccerNet y Roboflow."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .contracts import EventType, Position


class BoundingBox(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class SoccerNetActionRecord(BaseModel):
    """Acción detectada en un fotograma; todavía necesita fusión y validación."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    observation_id: str = Field(min_length=1)
    match_id: str = Field(min_length=1)
    frame_index: int = Field(ge=0)
    period: int = Field(ge=1, le=4)
    clock_ms: int = Field(ge=0)
    video_time_ms: int = Field(ge=0)
    event_type: EventType
    possession_team_id: str | None = None
    shirt_color_label: str | None = None
    player_id: str | None = None
    ball_position: Position | None = None
    confidence: float = Field(ge=0, le=1)


class RoboflowDetectionRecord(BaseModel):
    """Detección cruda y auditable antes de convertirla a ``TrackingFrame``."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    detection_id: str = Field(min_length=1)
    match_id: str = Field(min_length=1)
    frame_index: int = Field(ge=0)
    video_time_ms: int = Field(ge=0)
    class_name: Literal["player", "goalkeeper", "referee", "ball", "other"]
    confidence: float = Field(ge=0, le=1)
    bounding_box: BoundingBox
    track_id: str | None = None
    team_id: str | None = None
    shirt_color_label: str | None = None
    player_id: str | None = None
    pitch_position: Position | None = None
    processing_latency_ms: int = Field(ge=0)
