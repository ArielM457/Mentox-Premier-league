"""Coordina observaciones precomputadas con los controles de un vídeo."""

import asyncio
from bisect import bisect_right
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from match_intelligence.application.integrated_pipeline import IntegratedPipeline
from match_intelligence.application.realtime_observations import LiveObservation


class ObservationPublisher(Protocol):
    async def publish(self, observation: LiveObservation) -> bool: ...

    async def publish_many(
        self, observations: tuple[LiveObservation, ...]
    ) -> int: ...


@dataclass(frozen=True, slots=True)
class PlaybackObservation:
    observation_id: str
    source: str
    kind: str
    timestamp_ms: int
    payload: dict[str, Any]


def load_playback_observations(
    pipeline: IntegratedPipeline,
) -> tuple[PlaybackObservation, ...]:
    observations = [
        PlaybackObservation(
            observation_id=item["prediction_id"],
            source=f"roboflow-{item.get('model_role', 'player')}",
            kind="spatial_detection",
            timestamp_ms=item["timestamp_ms"],
            payload=item,
        )
        for item in pipeline.roboflow["predictions"]
    ]
    observations.extend(
        PlaybackObservation(
            observation_id=item["prediction_id"],
            source="roboflow-pitch",
            kind="spatial_detection",
            timestamp_ms=item["timestamp_ms"],
            payload=item,
        )
        for item in pipeline.roboflow.get("pitch_observations", [])
    )
    observations.extend(
        PlaybackObservation(
            observation_id=item["prediction_id"],
            source="soccernet",
            kind="temporal_action",
            timestamp_ms=item["timestamp_ms"],
            payload=item,
        )
        for item in pipeline.soccernet["predictions"]
    )
    return tuple(sorted(observations, key=lambda item: item.timestamp_ms))


class ObservationPlaybackSession:
    """Publica únicamente el tramo que el reproductor cruza mientras está activo."""

    def __init__(
        self,
        observations: tuple[PlaybackObservation, ...],
        publisher: ObservationPublisher,
    ) -> None:
        self._observations = observations
        self._timestamps = tuple(item.timestamp_ms for item in observations)
        self._publisher = publisher
        self._lock = asyncio.Lock()
        self._playing = False
        self._position_ms = 0
        self._cursor = 0
        self._published = 0

    def snapshot(self) -> dict[str, object]:
        return {
            "playback_state": "playing" if self._playing else "paused",
            "position_ms": self._position_ms,
            "cursor": self._cursor,
            "total_observations": len(self._observations),
            "published_in_session": self._published,
            "timing_basis": "video_player_position",
            "historical_observations_republished": False,
        }

    async def play(self, position_ms: int) -> dict[str, object]:
        async with self._lock:
            self._seek_unlocked(position_ms)
            self._playing = True
            return self.snapshot()

    async def pause(self, position_ms: int) -> dict[str, object]:
        async with self._lock:
            await self._advance_unlocked(position_ms)
            self._playing = False
            return self.snapshot()

    async def advance(self, position_ms: int) -> dict[str, object]:
        async with self._lock:
            await self._advance_unlocked(position_ms)
            return self.snapshot()

    async def seek(self, position_ms: int) -> dict[str, object]:
        async with self._lock:
            self._seek_unlocked(position_ms)
            return self.snapshot()

    async def restart(self) -> dict[str, object]:
        async with self._lock:
            self._playing = False
            self._position_ms = 0
            self._cursor = 0
            self._published = 0
            return self.snapshot()

    def _seek_unlocked(self, position_ms: int) -> None:
        self._position_ms = position_ms
        self._cursor = (
            0 if position_ms == 0 else bisect_right(self._timestamps, position_ms)
        )

    async def _advance_unlocked(self, position_ms: int) -> None:
        if not self._playing:
            return
        if position_ms < self._position_ms:
            self._seek_unlocked(position_ms)
            return

        end_cursor = bisect_right(self._timestamps, position_ms)
        pending = self._observations[self._cursor:end_cursor]
        observations = tuple(
                LiveObservation(
                    observation_id=item.observation_id,
                    source=item.source,
                    kind=item.kind,
                    timestamp_ms=item.timestamp_ms,
                    payload={
                        **item.payload,
                        "playback_position_ms": position_ms,
                    },
                    received_at=datetime.now(UTC),
                )
            for item in pending
        )
        await self._publisher.publish_many(observations)
        self._published += len(pending)
        self._cursor = end_cursor
        self._position_ms = position_ms
