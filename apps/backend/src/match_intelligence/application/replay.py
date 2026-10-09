import asyncio
from collections.abc import Awaitable, Callable, Sequence
from enum import StrEnum
from math import isfinite
from typing import Protocol

from match_intelligence.domain.contracts import MatchEvent


class ReplayState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


class ReplayStateError(RuntimeError):
    """Indica que un control no es válido para el estado actual."""


class EventPublisher(Protocol):
    async def publish(self, event: MatchEvent) -> None:
        """Publica un evento sin modificarlo."""


Sleep = Callable[[float], Awaitable[None]]


class MatchReplay:
    """Emite eventos progresivamente según el reloj del partido.

    El reproductor depende de un puerto de publicación y de una función de
    espera. De este modo funciona con memoria local y puede probarse sin dormir
    en tiempo real ni conectarse a Azure.
    """

    def __init__(
        self,
        events: Sequence[MatchEvent],
        publisher: EventPublisher,
        *,
        speed: float = 1.0,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._events = tuple(events)
        self._validate_order(self._events)
        self._publisher = publisher
        self._sleep = sleep
        self._speed = self._validate_speed(speed)
        self._state = ReplayState.IDLE
        self._cursor = 0
        self._generation = 0
        self._resume_gate = asyncio.Event()
        self._resume_gate.set()

    @property
    def state(self) -> ReplayState:
        return self._state

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def position(self) -> int:
        """Número de eventos publicados en la ejecución actual."""
        return self._cursor

    @property
    def total_events(self) -> int:
        return len(self._events)

    def set_speed(self, speed: float) -> None:
        """Cambia la velocidad para las esperas que todavía no comenzaron."""
        self._speed = self._validate_speed(speed)

    def pause(self) -> None:
        if self._state is not ReplayState.RUNNING:
            raise ReplayStateError("Solo se puede pausar una reproducción activa")
        self._state = ReplayState.PAUSED
        self._resume_gate.clear()

    def resume(self) -> None:
        if self._state is not ReplayState.PAUSED:
            raise ReplayStateError("Solo se puede reanudar una reproducción pausada")
        self._state = ReplayState.RUNNING
        self._resume_gate.set()

    def restart(self) -> None:
        """Invalida la ejecución actual y vuelve al inicio del flujo."""
        self._generation += 1
        self._cursor = 0
        self._state = ReplayState.IDLE
        self._resume_gate.set()

    async def start(self) -> None:
        if self._state in {ReplayState.RUNNING, ReplayState.PAUSED}:
            raise ReplayStateError("La reproducción ya está activa")
        if self._state is ReplayState.COMPLETED:
            raise ReplayStateError("Reinicia la reproducción antes de iniciarla de nuevo")

        generation = self._generation
        self._state = ReplayState.RUNNING

        while self._cursor < len(self._events):
            await self._resume_gate.wait()
            if generation != self._generation:
                return

            event = self._events[self._cursor]
            delay_ms = self._delay_before(self._cursor)
            await self._sleep(delay_ms / 1_000 / self._speed)

            # Una pausa o un reinicio puede ocurrir mientras transcurre la espera.
            await self._resume_gate.wait()
            if generation != self._generation:
                return

            await self._publisher.publish(event)
            self._cursor += 1

        if generation == self._generation:
            self._state = ReplayState.COMPLETED

    def _delay_before(self, index: int) -> int:
        current = self._events[index]
        if index == 0:
            return current.clock_ms

        previous = self._events[index - 1]
        if current.period == previous.period:
            return current.clock_ms - previous.clock_ms

        # clock_ms vuelve a cero al comenzar otro período.
        return current.clock_ms

    @staticmethod
    def _validate_speed(speed: float) -> float:
        if not isfinite(speed) or speed <= 0:
            raise ValueError("La velocidad debe ser finita y mayor que cero")
        return speed

    @staticmethod
    def _validate_order(events: tuple[MatchEvent, ...]) -> None:
        for previous, current in zip(events, events[1:]):
            if current.period < previous.period:
                raise ValueError("Los períodos deben estar ordenados")
            if current.period == previous.period and current.clock_ms < previous.clock_ms:
                raise ValueError("Los eventos de un período deben estar ordenados por reloj")
