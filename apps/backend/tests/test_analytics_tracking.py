"""Analítica de seguimiento con trayectorias de resultado conocido y con el mock."""

import pytest
from analytics_builders import A, B, Events

from match_intelligence.adapters.sources.analytics_scenarios import generate_analytics_scenario
from match_intelligence.adapters.sources.roboflow_tracking import frames_from_roboflow
from match_intelligence.adapters.sources.tracking_mock import generate_mock_tracking
from match_intelligence.application.analytics.pipeline import MatchAnalytics, build_snapshot
from match_intelligence.domain.analytics.catalog import METRIC_CATALOG
from match_intelligence.domain.analytics.tracking import (
    TrackedKind,
    TrackedObject,
    TrackingFrame,
    TrackingSource,
    ball_tracking_metrics,
    player_tracking_metrics,
    pressure_metrics,
    team_shape_metrics,
    tracking_alerts,
    tracking_metrics,
)
from match_intelligence.domain.contracts import EventOutcome


def _frames(paths: dict[str, list[tuple[int, float, float]]], *, period: int = 1) -> list[TrackingFrame]:
    """``paths``: pista -> [(ms, x, y)]. ``ball`` es el balón; ``a-*``/``b-*`` jugadores."""
    by_time: dict[int, list[TrackedObject]] = {}
    for track, points in paths.items():
        for clock, x, y in points:
            if track == "ball":
                item = TrackedObject(track_id="trk-ball", kind=TrackedKind.BALL, x_m=x, y_m=y)
            else:
                team = A if track.startswith("a-") else B
                item = TrackedObject(track_id=f"trk-{track}", kind=TrackedKind.PLAYER, team_id=team,
                                     player_id=track, x_m=x, y_m=y)
            by_time.setdefault(clock, []).append(item)
    return [
        TrackingFrame(match_id="test-001", period=period, clock_ms=clock, video_time_ms=clock,
                      source=TrackingSource.SYNTHETIC_MOCK, objects=objects)
        for clock, objects in sorted(by_time.items())
    ]


def _line(speed_ms: float, seconds: float, *, start_ms: int = 0, x0: float = 10.0, y: float = 20.0, hz: int = 5):
    step = 1000 // hz
    return [(start_ms + i * step, x0 + speed_ms * i * step / 1000, y) for i in range(int(seconds * hz) + 1)]


def _by_key(metrics, player=None, team=None):
    return {m.key: m for m in metrics if m.player_id == player and (team is None or m.team_id == team)}


def test_constant_speed_gives_exact_distance_and_top_speed() -> None:
    metrics = _by_key(player_tracking_metrics(_frames({"a-1": _line(5.0, 10)})), "a-1")

    assert metrics["distance_covered_m"].value == pytest.approx(50.0, abs=0.01)
    assert metrics["top_speed_kmh"].value == 18.0
    assert metrics["sprints"].value == 0
    assert metrics["high_intensity_distance_m"].value == 0.0
    evidence = metrics["distance_covered_m"].tracking_evidence
    assert evidence.source == "synthetic_mock" and evidence.track_ids == ["trk-a-1"] and evidence.frames == 51


def test_sprint_and_high_intensity_distance() -> None:
    sprint = _line(8.0, 2.0)
    jog = _line(2.0, 4.0, start_ms=2_200, x0=sprint[-1][1] + 0.4)
    metrics = _by_key(player_tracking_metrics(_frames({"a-1": sprint + jog})), "a-1")

    assert metrics["sprints"].value == 1
    assert metrics["top_speed_kmh"].value == 28.8
    assert metrics["high_intensity_distance_m"].value == pytest.approx(16.0, abs=0.01)


def test_impossible_jumps_and_lost_tracks_are_not_counted() -> None:
    path = _line(4.0, 4.0)
    path[10] = (path[10][0], path[10][1] + 30, path[10][2])   # salto de 30 m en 0,2 s y vuelta
    del path[15:20]                                            # 1 s sin la pista
    metrics = _by_key(player_tracking_metrics(_frames({"a-1": path})), "a-1")

    discarded = metrics["distance_covered_m"].components[0]
    assert discarded.key == "discarded_segments" and discarded.value == 2
    # 20 tramos de 0,8 m: 2 descartados por el salto y 6 perdidos en el hueco.
    assert metrics["distance_covered_m"].value == pytest.approx(0.8 * 12, abs=0.01)


def test_periods_are_never_joined() -> None:
    first = _frames({"a-1": _line(3.0, 2.0)})
    second = _frames({"a-1": _line(3.0, 2.0, x0=80.0)}, period=2)

    metrics = _by_key(player_tracking_metrics(first + second), "a-1")

    assert metrics["distance_covered_m"].value == pytest.approx(12.0, abs=0.01)


def test_ball_and_shot_speed_use_the_second_after_the_shot() -> None:
    events = Events(video_offset_ms=0)
    shot = events.shot(2.0, A, "a-9", (80, 50), outcome=EventOutcome.SAVED)
    ball = [(t, 80.0, 25.0) for t in range(0, 2_001, 200)] + _line(30.0, 0.6, start_ms=2_200, x0=86.0, y=25.0)
    frames = _frames({"ball": ball})

    metrics = ball_tracking_metrics(frames, events.items)
    shot_speed = next(m for m in metrics if m.key == "shot_speed_kmh")

    assert next(m for m in metrics if m.key == "ball_speed_kmh").value == 108.0
    assert shot_speed.value == 108.0 and shot_speed.source_event_ids == [shot.event_id]
    no_ball = ball_tracking_metrics(_frames({"a-1": _line(1.0, 1.0)}))
    assert no_ball[0].available is False


def _carrier_frames(defender_distance: float) -> list[TrackingFrame]:
    return _frames({
        "b-1": [(t, 50.0, 25.0) for t in range(0, 1_001, 200)],
        "ball": [(t, 50.5, 25.0) for t in range(0, 1_001, 200)],
        "a-1": [(t, 50.0 + defender_distance, 25.0) for t in range(0, 1_001, 200)],
    })


def test_pressure_by_proximity_positive_and_negative() -> None:
    close = _by_key(pressure_metrics(_carrier_frames(3.0), (A, B)), team=A)
    far = _by_key(pressure_metrics(_carrier_frames(8.0), (A, B)), team=A)

    assert close["pressure_proximity_share"].value == 100.0
    assert close["nearest_defender_m"].value == 3.0
    assert far["pressure_proximity_share"].value == 0.0
    # B nunca defendió: A no tuvo el balón controlado.
    assert _by_key(pressure_metrics(_carrier_frames(3.0), (A, B)), team=B)["pressure_proximity_share"].available is False


def test_team_shape_with_known_geometry() -> None:
    frames = _frames({
        "a-1": [(0, 10.0, 10.0)], "a-2": [(0, 30.0, 10.0)], "a-3": [(0, 20.0, 40.0)],
        "b-1": [(0, 60.0, 20.0)],
    })
    shape = _by_key(team_shape_metrics(frames, (A, B)), team=A)

    assert shape["team_width_m"].value == 30.0
    assert shape["team_depth_m"].value == 20.0
    assert shape["team_compactness_m"].value == pytest.approx(round((14.1421 * 2 + 20) / 3, 1), abs=0.05)
    assert _by_key(team_shape_metrics(frames, (A, B)), team=B)["team_width_m"].available is False


def test_speed_record_alert_once_per_episode_and_distance_milestones() -> None:
    first = _line(9.0, 3.0)                                              # 32,4 km/h
    rest = _line(2.0, 3.0, start_ms=3_200, x0=first[-1][1] + 0.4)
    second = _line(9.1, 2.0, start_ms=6_400, x0=rest[-1][1] + 1.8)      # +0,4 km/h: sin aviso
    runner = _line(5.0, 210.0, y=40.0)                                    # 1 050 m
    alerts = tracking_alerts(_frames({"a-1": first + rest + second, "b-1": runner}))

    records = [a for a in alerts if a.kind == "speed_record"]
    assert [(a.player_id, a.facts[0].value) for a in records] == [("a-1", 32.4)]
    milestones = [a for a in alerts if a.kind == "distance_milestone"]
    assert [(a.player_id, a.facts[0].value, a.clock_ms) for a in milestones] == [("b-1", 1000, 200_000)]
    assert all("simulado" in a.evidence_limits[0] for a in alerts)


def test_mock_tracking_is_deterministic_and_plausible() -> None:
    match = generate_analytics_scenario()
    frames = generate_mock_tracking(match.metadata, match.events)

    assert frames == generate_mock_tracking(match.metadata, match.events)
    assert {f.source for f in frames} == {TrackingSource.SYNTHETIC_MOCK}
    assert {f.period for f in frames} == {1, 2}
    metrics = tracking_metrics(frames, ("team-aurora", "team-rio"), match.events)
    players = [m for m in metrics if m.player_id and m.key == "top_speed_kmh"]
    assert len(players) == 14
    assert all(10 <= m.value <= 31.5 for m in players)
    distances = [m.value for m in metrics if m.key == "distance_covered_m"]
    assert all(250 <= value <= 1_500 for value in distances)  # unos 9,9 minutos de juego
    ball = next(m for m in metrics if m.key == "ball_speed_kmh")
    assert 80 <= ball.value <= 144
    for item in metrics:
        assert METRIC_CATALOG[item.key].unit == item.unit


def test_snapshot_uses_tracking_up_to_its_own_time_only() -> None:
    match = generate_analytics_scenario()
    frames = generate_mock_tracking(match.metadata, match.events)

    plain = build_snapshot(match.metadata, match.events[:40])
    early = build_snapshot(match.metadata, match.events[:40], tracking=frames)
    late = MatchAnalytics(tracking_provider=lambda _: frames).snapshot(match.metadata, match.events)

    def distance(snapshot):
        return next(m for m in snapshot.metrics if m.key == "distance_covered_m" and m.player_id == "aurora-8")

    assert distance(plain).available is False
    assert distance(early).available and distance(early).tracking_evidence.end_clock_ms <= early.clock_ms
    assert distance(late).value > distance(early).value


def test_roboflow_rows_become_video_frames_without_inventing_identity() -> None:
    rows = [
        {"frame_index": 0, "fps": 25.0, "tracker_id": 7, "class_name": "player", "team": 1,
         "pitch_x": 6000.0, "pitch_y": 3500.0, "confidence": 0.9},
        {"frame_index": 0, "fps": 25.0, "tracker_id": 1, "class_name": "ball", "team": None,
         "pitch_x": 6100.0, "pitch_y": 3500.0, "confidence": 0.4},
        {"frame_index": 0, "fps": 25.0, "tracker_id": 2, "class_name": "ball", "team": None,
         "pitch_x": 100.0, "pitch_y": 100.0, "confidence": 0.8},
        {"frame_index": 25, "fps": 25.0, "tracker_id": 7, "class_name": "player", "team": 1,
         "pitch_x": 6600.0, "pitch_y": 3500.0, "confidence": 0.9},
        {"frame_index": 25, "fps": 25.0, "tracker_id": 9, "class_name": "spectator", "team": None,
         "pitch_x": 1.0, "pitch_y": 1.0},
        {"frame_index": "x"},
    ]
    conversion = frames_from_roboflow(
        rows, match_id="video-001", period=1, pitch_length_m=105.0, pitch_width_m=68.0,
        team_by_group={0: "team-aurora", 1: "team-rio"}, clock_at_first_frame_ms=600_000,
    )

    assert conversion.ignored_rows == 2
    first, second = conversion.frames
    assert (first.clock_ms, second.clock_ms) == (600_000, 601_000)
    assert first.source is TrackingSource.VIDEO_MODEL
    player = next(o for o in first.objects if o.kind is TrackedKind.PLAYER)
    assert (player.x_m, player.y_m, player.team_id, player.player_id) == (52.5, 34.0, "team-rio", None)
    balls = [o for o in first.objects if o.kind is TrackedKind.BALL]
    assert len(balls) == 1 and balls[0].confidence == 0.8
    metrics = player_tracking_metrics(conversion.frames)
    assert next(m for m in metrics if m.key == "distance_covered_m").tracking_evidence.source == "video_model"
