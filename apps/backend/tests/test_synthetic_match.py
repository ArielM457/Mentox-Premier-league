from match_intelligence.adapters.sources.synthetic import (
    SyntheticMatch,
    generate_acceptance_match,
)
from match_intelligence.domain.contracts import EventOutcome, EventSource, EventType


def _serialize(match: SyntheticMatch) -> tuple[dict[str, object], list[dict[str, object]]]:
    return (
        match.metadata.model_dump(mode="json"),
        [event.model_dump(mode="json") for event in match.events],
    )


def test_same_seed_produces_the_same_match() -> None:
    first = generate_acceptance_match(seed=41)
    second = generate_acceptance_match(seed=41)

    assert _serialize(first) == _serialize(second)


def test_custom_match_id_is_preserved_in_metadata_and_events() -> None:
    match = generate_acceptance_match(match_id="team-demo-42")

    assert match.metadata.match_id == "team-demo-42"
    assert all(event.match_id == "team-demo-42" for event in match.events)


def test_different_seeds_change_the_generated_positions() -> None:
    first = generate_acceptance_match(seed=41)
    second = generate_acceptance_match(seed=42)

    assert _serialize(first) != _serialize(second)


def test_acceptance_match_contains_every_required_event_type() -> None:
    match = generate_acceptance_match()

    assert {event.type for event in match.events} == {
        EventType.PASS,
        EventType.SHOT,
        EventType.TACKLE,
        EventType.POSSESSION_CHANGE,
        EventType.PRESSURE,
        EventType.RECOVERY,
    }


def test_acceptance_match_contains_control_transition_and_decisive_moment() -> None:
    match = generate_acceptance_match()
    events_by_id = {event.event_id: event for event in match.events}
    goal = events_by_id["evt-010"]

    control_sequence = [event.type for event in match.events[:5]]
    transition_sequence = [event.type for event in match.events[5:]]

    assert control_sequence == [
        EventType.PRESSURE,
        EventType.PASS,
        EventType.PASS,
        EventType.TACKLE,
        EventType.POSSESSION_CHANGE,
    ]
    assert transition_sequence == [
        EventType.RECOVERY,
        EventType.PASS,
        EventType.PRESSURE,
        EventType.PASS,
        EventType.SHOT,
    ]
    assert events_by_id["evt-003"].related_event_ids == ["evt-002"]
    assert events_by_id["evt-006"].related_event_ids == ["evt-005"]
    assert goal.type is EventType.SHOT
    assert goal.outcome is EventOutcome.GOAL
    assert goal.related_event_ids == ["evt-006", "evt-007", "evt-009"]


def test_acceptance_match_is_synthetic_and_uses_fictional_teams() -> None:
    match = generate_acceptance_match()

    assert match.metadata.home_team.name == "Aurora FC"
    assert match.metadata.away_team.name == "Río Unido"
    assert all(event.source is EventSource.SYNTHETIC for event in match.events)
    assert all(event.confidence is None for event in match.events)


def test_metadata_is_complete_and_internally_consistent() -> None:
    match = generate_acceptance_match()
    metadata = match.metadata
    team_ids = {metadata.home_team.team_id, metadata.away_team.team_id}

    assert metadata.pitch_length_m == 105.0
    assert metadata.pitch_width_m == 68.0
    assert {player.team_id for player in metadata.players} == team_ids
    assert {(item.period, item.team_id) for item in metadata.attacking_directions} == {
        (1, "team-aurora"),
        (1, "team-rio"),
        (2, "team-aurora"),
        (2, "team-rio"),
    }
    assert all(event.team_id in team_ids for event in match.events)
    assert all(
        event.player_id is None
        or any(player.player_id == event.player_id for player in metadata.players)
        for event in match.events
    )


def test_event_identifiers_and_clocks_are_stable_and_ordered() -> None:
    match = generate_acceptance_match()

    assert [event.event_id for event in match.events] == [
        f"evt-{number:03d}" for number in range(1, 11)
    ]
    assert [event.clock_ms for event in match.events] == sorted(
        event.clock_ms for event in match.events
    )
    assert len({event.event_id for event in match.events}) == len(match.events)


def test_every_related_event_reference_exists_and_points_backwards() -> None:
    match = generate_acceptance_match()
    positions = {event.event_id: index for index, event in enumerate(match.events)}

    for index, event in enumerate(match.events):
        assert all(reference in positions for reference in event.related_event_ids)
        assert all(positions[reference] < index for reference in event.related_event_ids)
