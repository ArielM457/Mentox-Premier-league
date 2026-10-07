from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EventType(StrEnum):
    PASS = "pass"
    SHOT = "shot"
    TACKLE = "tackle"
    POSSESSION_CHANGE = "possession_change"
    PRESSURE = "pressure"
    RECOVERY = "recovery"


class EventOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    GOAL = "goal"
    SAVED = "saved"
    BLOCKED = "blocked"
    OFF_TARGET = "off_target"
    UNKNOWN = "unknown"


class EventSource(StrEnum):
    SYNTHETIC = "synthetic"
    VIDEO_MODEL = "video_model"


class Position(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: float = Field(ge=0, le=100, description="Posición horizontal fija del campo")
    y: float = Field(ge=0, le=100, description="Posición vertical fija del campo")


class Team(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team_id: str = Field(min_length=1)
    name: str = Field(min_length=1)


class Player(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_id: str = Field(min_length=1)
    team_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    shirt_number: int | None = Field(default=None, ge=1, le=99)


class AttackDirection(StrEnum):
    LEFT_TO_RIGHT = "left_to_right"
    RIGHT_TO_LEFT = "right_to_left"


class PeriodDirection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: int = Field(ge=1, le=4)
    team_id: str = Field(min_length=1)
    direction: AttackDirection


class MatchMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    match_id: str = Field(min_length=1)
    home_team: Team
    away_team: Team
    pitch_length_m: float = Field(gt=0)
    pitch_width_m: float = Field(gt=0)
    players: list[Player] = Field(default_factory=list)
    attacking_directions: list[PeriodDirection] = Field(default_factory=list)


class MatchEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    event_id: str = Field(min_length=1)
    match_id: str = Field(min_length=1)
    period: int = Field(ge=1, le=4)
    clock_ms: int = Field(ge=0)
    video_time_ms: int | None = Field(default=None, ge=0)
    type: EventType
    team_id: str = Field(min_length=1)
    player_id: str | None = None
    start: Position | None = None
    end: Position | None = None
    outcome: EventOutcome = EventOutcome.UNKNOWN
    source: EventSource
    confidence: float | None = Field(default=None, ge=0, le=1)
    related_event_ids: list[str] = Field(default_factory=list)
