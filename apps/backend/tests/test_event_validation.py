from match_intelligence.adapters.http.router import validate_events
from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.application.validation import validate_event_batch
from match_intelligence.main import app


def _raw_event(index: int = 0) -> dict[str, object]:
    return generate_acceptance_match().events[index].model_dump(mode="json")


def test_valid_event_preserves_identity_and_time() -> None:
    candidate = _raw_event()

    report = validate_event_batch([candidate])

    assert report.rejected_count == 0
    assert report.accepted_count == 1
    accepted = report.accepted[0]
    assert accepted.event_id == candidate["event_id"]
    assert accepted.match_id == candidate["match_id"]
    assert accepted.period == candidate["period"]
    assert accepted.clock_ms == candidate["clock_ms"]
    assert accepted.video_time_ms == candidate["video_time_ms"]


def test_event_without_optional_fields_is_accepted() -> None:
    candidate = _raw_event()
    for field in (
        "video_time_ms",
        "player_id",
        "start",
        "end",
        "outcome",
        "confidence",
        "related_event_ids",
    ):
        candidate.pop(field)

    report = validate_event_batch([candidate])

    assert report.rejected_count == 0
    assert report.accepted_count == 1
    assert report.accepted[0].video_time_ms is None
    assert report.accepted[0].player_id is None
    assert report.accepted[0].related_event_ids == []


def test_missing_required_field_has_a_structured_rejection() -> None:
    candidate = _raw_event()
    candidate.pop("clock_ms")

    report = validate_event_batch([candidate])

    assert report.accepted_count == 0
    assert report.rejected_count == 1
    rejection = report.rejected[0]
    assert rejection.index == 0
    assert rejection.event_id == candidate["event_id"]
    assert any(
        issue.location == ("clock_ms",) and issue.code == "missing"
        for issue in rejection.issues
    )
    assert all(issue.message for issue in rejection.issues)


def test_invalid_event_does_not_stop_later_valid_events() -> None:
    first = _raw_event(0)
    invalid = _raw_event(1)
    last = _raw_event(2)
    invalid.pop("team_id")

    report = validate_event_batch([first, invalid, last])

    assert [event.event_id for event in report.accepted] == [
        first["event_id"],
        last["event_id"],
    ]
    assert [rejection.index for rejection in report.rejected] == [1]
    assert report.rejected[0].event_id == invalid["event_id"]


def test_invalid_values_and_unknown_fields_are_reported() -> None:
    candidate = _raw_event()
    candidate["period"] = 0
    candidate["unexpected"] = True

    report = validate_event_batch([candidate])

    issues = {(issue.location, issue.code) for issue in report.rejected[0].issues}
    assert (("period",), "greater_than_equal") in issues
    assert (("unexpected",), "extra_forbidden") in issues


def test_non_object_candidate_is_rejected_without_stopping_the_batch() -> None:
    valid = _raw_event()

    report = validate_event_batch(["not-an-event", valid])

    assert report.accepted_count == 1
    assert report.rejected_count == 1
    assert report.rejected[0].event_id is None
    assert report.rejected[0].issues[0].code == "model_type"


def test_batch_endpoint_returns_machine_readable_results() -> None:
    valid = _raw_event()
    invalid = _raw_event(1)
    invalid.pop("clock_ms")

    body = validate_events([valid, invalid])

    assert body["accepted_count"] == 1
    assert body["rejected_count"] == 1
    assert body["accepted"][0]["event_id"] == valid["event_id"]
    assert body["rejected"][0]["index"] == 1
    assert body["rejected"][0]["issues"][0]["location"] == ["clock_ms"]

    operation = app.openapi()["paths"]["/api/v1/events/validate-batch"]["post"]
    assert "200" in operation["responses"]
