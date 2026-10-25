"""Lecturas «¿qué habría pasado si…?» (``what_if@1``) y análisis de un momento."""

import pytest
from analytics_builders import A, B, Events, metadata
from fastapi.testclient import TestClient

from match_intelligence.adapters.http.registry import (
    ANALYTICS_MATCH_ID,
    LIVE_MATCH_ID,
    _default_registry,
    get_registry,
)
from match_intelligence.application.analytics.moment_analysis import MomentNotFound, analyze_moment
from match_intelligence.domain.analytics.pitch import PitchFrame
from match_intelligence.domain.analytics.tracking import Sample, Track, TrackedKind, TrackSet
from match_intelligence.domain.analytics.what_if import (
    LIMIT_SIMULATED,
    early_shot,
    earlier_pass,
    frame_at,
    keeper_steps,
    supporting_run,
)
from match_intelligence.main import app

FRAME = PitchFrame.from_metadata(metadata())  # 100 x 50 m; A ataca hacia x = 100 en el período 1


def track(track_id: str, kind: TrackedKind, team: str | None, player: str | None, *points) -> Track:
    """``points``: (segundo, x, y) en metros."""
    samples = [Sample(1, int(s * 1000), int(s * 1000) + 1000, x, y) for s, x, y in points]
    return Track(track_id, kind, team, player, samples)


def track_set(*tracks: Track, origin: str = "simulated_fixture") -> TrackSet:
    return TrackSet("test-001", origin, {t.track_id: t for t in tracks})


def comparison(reading, key):
    return next(c for c in reading.comparisons if c.key == key)


def test_earlier_pass_compares_passer_and_receiver_space_one_second_before() -> None:
    ev = Events()
    pass_ = ev.pass_(10, A, "a-4", (50, 50), (70, 50))
    tracks = track_set(
        track("t-a4", TrackedKind.PLAYER, A, "a-4", (9, 50, 34), (10, 50, 34)),
        track("t-a5", TrackedKind.PLAYER, A, "a-5", (9, 70, 34), (10, 70, 34)),
        track("t-b6", TrackedKind.PLAYER, B, "b-6", (9, 56, 34), (10, 52, 34)),
        track("t-b7", TrackedKind.PLAYER, B, "b-7", (9, 70, 40), (10, 70, 37)),
    )
    pass_ = pass_.model_copy(update={"receiver_player_id": "a-5"})
    reading = earlier_pass(tracks, [pass_])
    assert reading.available and reading.alternative_clock_ms == 9_000
    assert (comparison(reading, "passer_space_m").actual, comparison(reading, "passer_space_m").alternative) == (2.0, 6.0)
    assert (comparison(reading, "receiver_space_m").actual, comparison(reading, "receiver_space_m").alternative) == (3.0, 6.0)
    assert LIMIT_SIMULATED in reading.evidence_limits
    assert reading.tracking_evidence.source == "simulated_fixture"


def test_supporting_run_points_to_the_freest_teammate_within_25_m() -> None:
    ev = Events()
    event = ev.pass_(10, A, "a-4", (50, 50), (55, 50))
    tracks = track_set(
        track("t-a4", TrackedKind.PLAYER, A, "a-4", (10, 50, 34)),
        track("t-a5", TrackedKind.PLAYER, A, "a-5", (10, 55, 34)),
        track("t-a6", TrackedKind.PLAYER, A, "a-6", (10, 60, 44)),
        track("t-a7", TrackedKind.PLAYER, A, "a-7", (10, 95, 10)),  # libre pero a más de 25 m
        track("t-b6", TrackedKind.PLAYER, B, "b-6", (10, 56, 34)),
        track("t-b7", TrackedKind.PLAYER, B, "b-7", (10, 70, 44)),
    )
    reading = supporting_run(tracks, event)
    space = comparison(reading, "support_space_m")
    assert (space.player_id, space.actual) == ("a-5", 1.0)
    assert (space.alternative_player_id, space.alternative) == ("a-6", 10.0)


def test_keeper_steps_moves_the_rival_goalkeeper_three_metres_towards_the_ball() -> None:
    ev = Events()
    event = ev.shot(10, A, "a-9", (88, 50))
    tracks = track_set(
        track("t-b1", TrackedKind.GOALKEEPER, B, "b-1", (10, 98, 25)),
        track("ball", TrackedKind.BALL, None, None, (10, 88, 25)),
    )
    reading = keeper_steps(tracks, FRAME, event)
    assert (comparison(reading, "keeper_ball_distance_m").actual, comparison(reading, "keeper_ball_distance_m").alternative) == (10.0, 7.0)
    assert (comparison(reading, "keeper_goal_line_m").actual, comparison(reading, "keeper_goal_line_m").alternative) == (2.0, 5.0)


def test_early_shot_measures_distance_angle_and_space_one_second_before() -> None:
    ev = Events()
    shot = ev.shot(10, A, "a-9", (85, 50))
    tracks = track_set(
        track("t-a9", TrackedKind.PLAYER, A, "a-9", (9, 85, 25), (10, 90, 25)),
        track("t-b5", TrackedKind.PLAYER, B, "b-5", (9, 85, 29), (10, 91, 25)),
    )
    reading = early_shot(tracks, FRAME, [shot])
    assert (comparison(reading, "shot_distance_m").actual, comparison(reading, "shot_distance_m").alternative) == (10.0, 15.0)
    angle = comparison(reading, "shot_angle_deg")
    assert angle.actual > angle.alternative
    assert (comparison(reading, "shooter_space_m").actual, comparison(reading, "shooter_space_m").alternative) == (1.0, 4.0)


def test_readings_explain_why_they_are_unavailable() -> None:
    ev = Events()
    pressure = ev.pressure(10, A, "a-4", (50, 50))
    tracks = track_set(track("t-a4", TrackedKind.PLAYER, A, "a-4", (5, 50, 34)))
    assert earlier_pass(tracks, [pressure]).unavailable_reason == "El momento no incluye un pase."
    assert early_shot(tracks, FRAME, [pressure]).unavailable_reason == "El momento no incluye un remate."
    # Sin muestra a menos de 0,3 s del instante no se inventa la posición.
    assert not supporting_run(tracks, pressure).available
    assert frame_at(tracks, 1, 10_000, None) is None


def test_moment_analysis_uses_only_events_until_the_moment() -> None:
    session = _default_registry().get(ANALYTICS_MATCH_ID)
    shot = next(e for e in session.events if e.type.value == "shot")
    analysis = analyze_moment(
        session.metadata, session.events, candidate_id=f"moment-{shot.event_id}",
        tracks=session.track_set(), preferences={"mode": "analyst"},
    )
    assert analysis.found_in_engine and analysis.kind in {"shot", "goal"}
    assert analysis.reasons and analysis.priority is not None
    allowed = {e.event_id for e in session.events if (e.period, e.clock_ms) <= (shot.period, shot.clock_ms)}
    assert set(analysis.source_event_ids) <= allowed
    assert all(set(f.source_event_ids) <= allowed for f in analysis.facts)
    assert len(analysis.frame.objects) >= 22
    assert {w.scenario.value for w in analysis.what_if} == {
        "earlier_pass", "keeper_steps", "supporting_run", "early_shot",
    }
    with pytest.raises(MomentNotFound):
        analyze_moment(session.metadata, session.events, candidate_id="moment-evt-999")


@pytest.fixture
def client() -> TestClient:
    registry = _default_registry()
    app.dependency_overrides[get_registry] = lambda: registry
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.parametrize("engine", ["provisional", "persona2"])
def test_moment_analysis_route_works_with_both_engines(
    monkeypatch: pytest.MonkeyPatch, engine: str
) -> None:
    monkeypatch.setenv("ANALYTICS_ENGINE", engine)
    monkeypatch.delenv("MATCH_SOURCE", raising=False)
    registry = _default_registry()
    app.dependency_overrides[get_registry] = lambda: registry
    try:
        client = TestClient(app)
        base = f"/api/v1/matches/{LIVE_MATCH_ID}"
        moments = client.get(f"{base}/overlays", params={"mode": "analyst"}).json()["overlays"]
        card = next(m for m in moments if m["kind"] == "yellow_card")
        response = client.get(f"{base}/moments/{card['candidate_id']}/analysis", params={"mode": "analyst"})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["found_in_engine"] and body["kind"] == "yellow_card"
        assert body["frame"]["source"] == "synthetic_mock"
        assert client.get(f"{base}/moments/moment-evt-999/analysis").status_code == 404
    finally:
        app.dependency_overrides.clear()
