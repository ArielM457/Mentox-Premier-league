from match_intelligence.adapters.messaging.memory import InMemoryEventConsumer
from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.application.deduplication import EventDeduplicator


def test_same_match_and_event_id_is_accepted_only_once() -> None:
    event = generate_acceptance_match().events[0]

    report = EventDeduplicator().process((event, event))

    assert report.accepted == (event,)
    assert report.accepted_count == 1
    assert report.duplicate_count == 1


def test_duplicate_is_recorded_with_diagnostic_positions() -> None:
    event = generate_acceptance_match().events[0]
    deduplicator = EventDeduplicator()

    report = deduplicator.process((event, event))

    duplicate = report.duplicates[0]
    assert duplicate.index == 1
    assert duplicate.key == (event.match_id, event.event_id)
    assert duplicate.first_seen_sequence == 0
    assert duplicate.duplicate_sequence == 1
    assert deduplicator.duplicates == (duplicate,)


def test_key_combines_match_id_and_event_id() -> None:
    first = generate_acceptance_match(match_id="match-a").events[0]
    other_match = generate_acceptance_match(match_id="match-b").events[0]

    report = EventDeduplicator().process((first, other_match))

    assert report.accepted == (first, other_match)
    assert report.duplicate_count == 0


def test_retry_is_detected_across_separate_consume_operations() -> None:
    event = generate_acceptance_match().events[0]
    deduplicator = EventDeduplicator()

    first_report = deduplicator.process((event,))
    retry_report = deduplicator.process((event,))

    assert first_report.accepted == (event,)
    assert retry_report.accepted == ()
    assert retry_report.duplicate_count == 1
    assert retry_report.duplicates[0].duplicate_sequence == 1


def test_identity_key_wins_when_retry_payload_changes() -> None:
    event = generate_acceptance_match().events[0]
    changed_retry = event.model_copy(update={"clock_ms": event.clock_ms + 1_000})

    report = EventDeduplicator().process((event, changed_retry))

    assert report.accepted == (event,)
    assert report.duplicate_count == 1


def test_local_consumer_does_not_deliver_published_retry_twice() -> None:
    events = generate_acceptance_match().events
    consumer = InMemoryEventConsumer()

    first_report = consumer.consume(events)
    retry_report = consumer.consume(events)

    assert first_report.accepted == events
    assert retry_report.accepted == ()
    assert consumer.events == events
    assert len(consumer.duplicates) == len(events)


def test_deduplicator_instances_do_not_share_state() -> None:
    event = generate_acceptance_match().events[0]

    first_consumer = EventDeduplicator().process((event,))
    independent_consumer = EventDeduplicator().process((event,))

    assert first_consumer.accepted == (event,)
    assert independent_consumer.accepted == (event,)
