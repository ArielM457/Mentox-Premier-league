import asyncio

import pytest

from match_intelligence.adapters.messaging.memory import InMemoryEventPublisher
from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.application.replay import (
    MatchReplay,
    ReplayState,
    ReplayStateError,
)
from match_intelligence.domain.contracts import MatchEvent


class RecordingSleep:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


class ControlledFirstSleep:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.calls = 0

    async def __call__(self, _: float) -> None:
        self.calls += 1
        if self.calls == 1:
            self.started.set()
            await self.release.wait()


def _event_ids(events: tuple[MatchEvent, ...]) -> list[str]:
    return [event.event_id for event in events]


def test_start_publishes_the_complete_match_in_order() -> None:
    async def scenario() -> None:
        match = generate_acceptance_match()
        publisher = InMemoryEventPublisher()
        sleep = RecordingSleep()
        replay = MatchReplay(match.events, publisher, sleep=sleep)

        await replay.start()

        assert _event_ids(publisher.events) == _event_ids(match.events)
        assert replay.position == len(match.events)
        assert replay.state is ReplayState.COMPLETED
        assert len(sleep.delays) == len(match.events)

    asyncio.run(scenario())


def test_pause_blocks_publication_until_resume() -> None:
    async def scenario() -> None:
        match = generate_acceptance_match()
        publisher = InMemoryEventPublisher()
        sleep = ControlledFirstSleep()
        replay = MatchReplay(match.events, publisher, sleep=sleep)
        task = asyncio.create_task(replay.start())

        await sleep.started.wait()
        replay.pause()
        sleep.release.set()
        await asyncio.sleep(0)

        assert replay.state is ReplayState.PAUSED
        assert publisher.events == ()

        replay.resume()
        await task

        assert _event_ids(publisher.events) == _event_ids(match.events)
        assert replay.state is ReplayState.COMPLETED

    asyncio.run(scenario())


def test_restart_invalidates_an_active_run_and_starts_from_the_beginning() -> None:
    async def scenario() -> None:
        match = generate_acceptance_match()
        publisher = InMemoryEventPublisher()
        sleep = ControlledFirstSleep()
        replay = MatchReplay(match.events, publisher, sleep=sleep)
        interrupted_task = asyncio.create_task(replay.start())

        await sleep.started.wait()
        replay.restart()
        sleep.release.set()
        await interrupted_task

        assert replay.state is ReplayState.IDLE
        assert replay.position == 0
        assert publisher.events == ()

        await replay.start()

        assert _event_ids(publisher.events) == _event_ids(match.events)
        assert replay.state is ReplayState.COMPLETED

    asyncio.run(scenario())


def test_acceleration_changes_delays_but_not_events() -> None:
    async def scenario() -> None:
        match = generate_acceptance_match()
        normal_publisher = InMemoryEventPublisher()
        fast_publisher = InMemoryEventPublisher()
        normal_sleep = RecordingSleep()
        fast_sleep = RecordingSleep()
        normal = MatchReplay(match.events, normal_publisher, speed=1, sleep=normal_sleep)
        fast = MatchReplay(match.events, fast_publisher, speed=4, sleep=fast_sleep)

        await normal.start()
        await fast.start()

        assert _event_ids(normal_publisher.events) == _event_ids(fast_publisher.events)
        assert normal_publisher.events == fast_publisher.events
        assert fast_sleep.delays == pytest.approx(
            [delay / 4 for delay in normal_sleep.delays]
        )

    asyncio.run(scenario())


def test_speed_can_be_changed_before_starting() -> None:
    async def scenario() -> None:
        match = generate_acceptance_match()
        publisher = InMemoryEventPublisher()
        sleep = RecordingSleep()
        replay = MatchReplay(match.events, publisher, speed=1, sleep=sleep)

        replay.set_speed(2)
        await replay.start()

        assert replay.speed == 2
        assert sleep.delays[0] == pytest.approx(2.5)
        assert _event_ids(publisher.events) == _event_ids(match.events)

    asyncio.run(scenario())


def test_local_replay_has_no_azure_configuration_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario() -> None:
        for name in (
            "AZURE_EVENTHUB_CONNECTION_STRING",
            "AZURE_EVENTHUB_NAMESPACE",
            "AZURE_STORAGE_CONNECTION_STRING",
        ):
            monkeypatch.delenv(name, raising=False)

        match = generate_acceptance_match()
        publisher = InMemoryEventPublisher()
        replay = MatchReplay(match.events, publisher, speed=100, sleep=RecordingSleep())

        await replay.start()

        assert publisher.events == match.events

    asyncio.run(scenario())


@pytest.mark.parametrize("invalid_speed", [0, -1, float("nan"), float("inf")])
def test_speed_must_be_finite_and_positive(invalid_speed: float) -> None:
    match = generate_acceptance_match()
    publisher = InMemoryEventPublisher()

    with pytest.raises(ValueError, match="finita y mayor que cero"):
        MatchReplay(match.events, publisher, speed=invalid_speed)


def test_invalid_state_transitions_are_rejected() -> None:
    match = generate_acceptance_match()
    replay = MatchReplay(match.events, InMemoryEventPublisher(), sleep=RecordingSleep())

    with pytest.raises(ReplayStateError, match="pausar"):
        replay.pause()
    with pytest.raises(ReplayStateError, match="reanudar"):
        replay.resume()


def test_events_must_be_ordered_within_the_period() -> None:
    match = generate_acceptance_match()
    unordered = (match.events[1], match.events[0])

    with pytest.raises(ValueError, match="ordenados por reloj"):
        MatchReplay(unordered, InMemoryEventPublisher())
