from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from match_intelligence.domain.contracts import MatchEvent


class VideoPlaybackState(StrEnum):
    PAUSED = "paused"
    PLAYING = "playing"


class VideoTimingBasis(StrEnum):
    PROVIDED_EVENT_TIMESTAMP = "provided_event_timestamp"


class VideoSyncError(ValueError):
    """La secuencia o una operación no permite sincronización determinista."""


@dataclass(frozen=True, slots=True)
class SynchronizedEvent:
    """Evento asociado al vídeo mediante una marca entregada por su fuente.

    La base temporal explícita evita presentar ``video_time_ms`` como resultado
    de detección automática.
    """

    event: MatchEvent
    timing_basis: VideoTimingBasis = VideoTimingBasis.PROVIDED_EVENT_TIMESTAMP

    @property
    def clock_ms(self) -> int:
        return self.event.clock_ms

    @property
    def video_time_ms(self) -> int:
        assert self.event.video_time_ms is not None
        return self.event.video_time_ms


class SynchronizedEventPublisher(Protocol):
    async def publish(self, event: SynchronizedEvent) -> None: ...


class MatchStateRebuilder(Protocol):
    async def rebuild(
        self,
        events: tuple[MatchEvent, ...],
        *,
        video_time_ms: int,
    ) -> None: ...


class VideoSynchronizedReplay:
    """Coordina eventos con la posición de un vídeo sin generar mensajes al saltar."""

    def __init__(
        self,
        events: Sequence[MatchEvent],
        publisher: SynchronizedEventPublisher,
        state_rebuilder: MatchStateRebuilder,
    ) -> None:
        self._events = tuple(events)
        self._validate_events(self._events)
        self._publisher = publisher
        self._state_rebuilder = state_rebuilder
        self._state = VideoPlaybackState.PAUSED
        self._video_time_ms = 0
        self._cursor = 0

    @property
    def state(self) -> VideoPlaybackState:
        return self._state

    @property
    def video_time_ms(self) -> int:
        return self._video_time_ms

    @property
    def position(self) -> int:
        """Cantidad de eventos incorporados hasta la posición actual del vídeo."""
        return self._cursor

    def play(self) -> None:
        self._state = VideoPlaybackState.PLAYING

    def pause(self) -> None:
        self._state = VideoPlaybackState.PAUSED

    async def advance_to(self, video_time_ms: int) -> tuple[SynchronizedEvent, ...]:
        """Publica únicamente los eventos cruzados durante el avance normal."""
        self._validate_position(video_time_ms)
        if self._state is VideoPlaybackState.PAUSED:
            return ()
        if video_time_ms < self._video_time_ms:
            raise VideoSyncError("Para retroceder el vídeo se debe usar seek")

        published: list[SynchronizedEvent] = []
        while self._cursor < len(self._events):
            event = self._events[self._cursor]
            assert event.video_time_ms is not None
            if event.video_time_ms > video_time_ms:
                break
            if self._state is VideoPlaybackState.PAUSED:
                break

            synchronized = SynchronizedEvent(event=event)
            await self._publisher.publish(synchronized)
            published.append(synchronized)
            self._cursor += 1

        self._video_time_ms = video_time_ms
        return tuple(published)

    async def seek(self, video_time_ms: int) -> tuple[MatchEvent, ...]:
        """Reconstruye el estado hasta el destino sin publicar mensajes históricos."""
        self._validate_position(video_time_ms)
        cursor = self._cursor_for(video_time_ms)
        history = self._events[:cursor]
        await self._state_rebuilder.rebuild(history, video_time_ms=video_time_ms)
        self._cursor = cursor
        self._video_time_ms = video_time_ms
        return history

    async def restart(self) -> None:
        self.pause()
        await self.seek(0)

    def _cursor_for(self, video_time_ms: int) -> int:
        cursor = 0
        for event in self._events:
            assert event.video_time_ms is not None
            if event.video_time_ms > video_time_ms:
                break
            cursor += 1
        return cursor

    @staticmethod
    def _validate_position(video_time_ms: int) -> None:
        if isinstance(video_time_ms, bool) or not isinstance(video_time_ms, int):
            raise VideoSyncError("video_time_ms debe ser un entero")
        if video_time_ms < 0:
            raise VideoSyncError("video_time_ms no puede ser negativo")

    @staticmethod
    def _validate_events(events: tuple[MatchEvent, ...]) -> None:
        if not events:
            return

        match_id = events[0].match_id
        previous_time = -1
        for event in events:
            if event.match_id != match_id:
                raise VideoSyncError("Todos los eventos deben pertenecer al mismo partido")
            if event.video_time_ms is None:
                raise VideoSyncError(
                    f"El evento {event.event_id} no tiene video_time_ms"
                )
            if event.video_time_ms < previous_time:
                raise VideoSyncError("Los eventos deben estar ordenados por video_time_ms")
            previous_time = event.video_time_ms
