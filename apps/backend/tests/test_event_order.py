from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.application.event_order import (
    ArrivalStatus,
    EventOrderTracker,
    LateEventPolicy,
    MatchTime,
)


def test_event_behind_the_match_watermark_is_marked_late() -> None:
    events = generate_acceptance_match().events
    tracker = EventOrderTracker()

    report = tracker.process((events[2], events[1]))

    assert [item.status for item in report.forwarded] == [
        ArrivalStatus.ON_TIME,
        ArrivalStatus.LATE,
    ]
    assert report.late_count == 1
    assert report.late[0].event_id == events[1].event_id


def test_late_event_is_forwarded_in_arrival_order_and_recorded() -> None:
    events = generate_acceptance_match().events
    tracker = EventOrderTracker()

    report = tracker.process((events[2], events[0], events[3]))

    assert [item.event for item in report.forwarded] == [
        events[2],
        events[0],
        events[3],
    ]
    assert report.policy is LateEventPolicy.FORWARD_AND_FLAG
    record = report.late[0]
    assert record.index == 1
    assert record.match_id == events[0].match_id
    assert record.event_time == MatchTime(period=1, clock_ms=5_000)
    assert record.watermark == MatchTime(period=1, clock_ms=12_000)
    assert tracker.late_events == (record,)


def test_late_event_does_not_move_watermark_backwards() -> None:
    events = generate_acceptance_match().events
    tracker = EventOrderTracker()

    tracker.process((events[2], events[0]))

    assert tracker.watermark_for(events[0].match_id) == MatchTime(
        period=1,
        clock_ms=12_000,
    )


def test_order_is_tracked_across_separate_batches() -> None:
    events = generate_acceptance_match().events
    tracker = EventOrderTracker()

    first = tracker.process((events[4],))
    second = tracker.process((events[3],))

    assert first.late_count == 0
    assert second.late_count == 1
    assert second.late[0].arrival_sequence == 1


def test_same_clock_is_not_late() -> None:
    events = generate_acceptance_match().events
    tracker = EventOrderTracker()

    report = tracker.process((events[3], events[4]))

    assert report.late_count == 0
    assert all(item.status is ArrivalStatus.ON_TIME for item in report.forwarded)


def test_new_period_advances_order_even_when_clock_restarts() -> None:
    event = generate_acceptance_match().events[-1]
    second_period = event.model_copy(
        update={"event_id": "evt-period-2", "period": 2, "clock_ms": 1_000}
    )

    report = EventOrderTracker().process((event, second_period))

    assert report.late_count == 0
    assert report.forwarded[-1].status is ArrivalStatus.ON_TIME


def test_event_from_previous_period_is_late_after_period_transition() -> None:
    event = generate_acceptance_match().events[-1]
    second_period = event.model_copy(
        update={"event_id": "evt-period-2", "period": 2, "clock_ms": 1_000}
    )
    previous_period_retry = event.model_copy(update={"event_id": "evt-late-period-1"})

    report = EventOrderTracker().process(
        (event, second_period, previous_period_retry)
    )

    assert report.late_count == 1
    assert report.late[0].event_id == "evt-late-period-1"
    assert report.late[0].watermark.period == 2


def test_matches_have_independent_watermarks() -> None:
    match_a = generate_acceptance_match(match_id="match-a").events
    match_b = generate_acceptance_match(match_id="match-b").events
    tracker = EventOrderTracker()

    report = tracker.process((match_a[3], match_b[0]))

    assert report.late_count == 0
    assert tracker.watermark_for("match-a") == MatchTime(1, 16_000)
    assert tracker.watermark_for("match-b") == MatchTime(1, 5_000)
