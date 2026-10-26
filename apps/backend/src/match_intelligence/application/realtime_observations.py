"""Cola en vivo para observaciones de workers de visión."""

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VisionObservationEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    observation_id: str = Field(min_length=1, max_length=160)
    source: str = Field(min_length=1, max_length=80)
    kind: str = Field(min_length=1, max_length=80)
    timestamp_ms: int = Field(ge=0)
    payload: dict[str, Any]
    produced_at: datetime


@dataclass(frozen=True, slots=True)
class LiveObservation:
    observation_id: str
    source: str
    kind: str
    timestamp_ms: int
    payload: dict[str, Any]
    received_at: datetime

    def as_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "source": self.source,
            "kind": self.kind,
            "timestamp_ms": self.timestamp_ms,
            "payload": self.payload,
            "received_at": self.received_at.isoformat(),
            "processing_delay_ms": self.payload.get("processing_delay_ms"),
        }


class RealtimeObservationHub:
    def __init__(self, *, history_size: int = 5_000, subscriber_size: int = 500) -> None:
        self._history: deque[LiveObservation] = deque(maxlen=history_size)
        self._seen: set[tuple[str, str]] = set()
        self._subscribers: set[asyncio.Queue[LiveObservation]] = set()
        self._subscriber_size = subscriber_size
        self.accepted = 0
        self.duplicates = 0
        self.dropped = 0

    async def publish(self, observation: LiveObservation) -> bool:
        key = (observation.source, observation.observation_id)
        if key in self._seen:
            self.duplicates += 1
            return False
        self._seen.add(key)
        self._history.append(observation)
        self.accepted += 1
        for queue in tuple(self._subscribers):
            if queue.full():
                queue.get_nowait()
                self.dropped += 1
            queue.put_nowait(observation)
        return True

    def subscribe(self) -> asyncio.Queue[LiveObservation]:
        queue: asyncio.Queue[LiveObservation] = asyncio.Queue(self._subscriber_size)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[LiveObservation]) -> None:
        self._subscribers.discard(queue)

    def snapshot(self) -> dict[str, Any]:
        return {
            "status": "running",
            "accepted": self.accepted,
            "duplicates": self.duplicates,
            "dropped_for_slow_consumers": self.dropped,
            "history_size": len(self._history),
            "subscribers": len(self._subscribers),
            "latest": self._history[-1].as_dict() if self._history else None,
        }

    def clear(self) -> None:
        self._history.clear()
        self._seen.clear()
        self.accepted = self.duplicates = self.dropped = 0
