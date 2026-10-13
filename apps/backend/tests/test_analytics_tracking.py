"""Analítica de seguimiento: cálculos con trayectorias conocidas y entrada desde Persona 1."""

import pytest
from analytics_builders import A, B, Events, metadata

from analytics_scenarios import generate_analytics_scenario
from tracking_mock import generate_mock_tracking
from match_intelligence.application.analytics.pipeline import MatchAnalytics, build_snapshot
from match_intelligence.application.analytics.tracking_input import (
    TrackingInput,
    VideoClock,
    tracks_from_observations,
)
from match_intelligence.application.vision_evaluation import PredictionOrigin
from match_intelligence.application.visual_identity import (
    ConfirmedPlayerIdentity,
    IdentityEvidenceKind,
    PlayerIdentityResolver,
    VisualTrackObservation,
)
from match_intelligence.domain.analytics.catalog import METRIC_CATALOG
from match_intelligence.domain.analytics.tracking import (
    Sample,
    Track,
    TrackedKind,
    TrackSet,
    ball_tracking_metrics,
    player_tracking_metrics,
    pressure_metrics,
    team_shape_metrics,
    tracking_alerts,
    tracking_metrics,
)
from match_intelligence.domain.contracts import EventOutcome, Position


def _tracks(paths: dict[str, list[tuple[int, float, float]]], *, period: int = 1) -> TrackSet:
    """``paths``: pista -> [(ms, x_m, y_m)]. ``ball`` es el balón; ``a-*``/``b-*`` jugadores."""
    tracks = {}
    for name, points in paths.items():
        kind = TrackedKind.BALL if name == "ball" else TrackedKind.PLAYER
        team = None if name == "ball" else (A if name.startswith("a-") else B)
        tracks[name] = Track(
            track_id=name, kind=kind, team_id=team, player_id=None if name == "ball" else name,
            samples=[Sample(period, clock, clock, x, y) for clock, x, y in points],
        )
    return TrackSet("test-001", "simulated_fixture", tracks)


def _merge(*sets: TrackSet) -> TrackSet:
    tracks: dict[str, Track] = {}
    for item in sets:
        for name, track in item.tracks.items():
            if name in tracks:
                tracks[name].samples.extend(track.samples)
            else:
                tracks[name] = Track(track.track_id, track.kind, track.team_id, track.player_id, list(track.samples))
    return TrackSet("test-001", "simulated_fixture", tracks)


def _line(speed_ms: float, seconds: float, *, start_ms: int = 0, x0: float = 10.0, y: float = 20.0, hz: int = 5):
    step = 1000 // hz
    return [(start_ms + i * step, x0 + speed_ms * i * step / 1000, y) for i in range(int(seconds * hz) + 1)]


def _by_key(metrics, player=None, team=None):
    return {m.key: m for m in metrics if m.player_id == player and (team is None or m.team_id == team)}


# --- Cálculos con trayectorias de resultado conocido -----------------------------

def test_constant_speed_gives_exact_distance_and_top_speed() -> None:
    metrics = _by_key(player_tracking_metrics(_tracks({"a-1": _line(5.0, 10)})), "a-1")

    assert metrics["distance_covered_m"].value == pytest.approx(50.0, abs=0.01)
    assert metrics["top_speed_kmh"].value == 18.0
    assert metrics["sprints"].value == 0
    assert metrics["high_intensity_distance_m"].value == 0.0
    evidence = metrics["distance_covered_m"].tracking_evidence
    assert evidence.source == "simulated_fixture" and evidence.track_ids == ["a-1"] and evidence.frames == 51


def test_sprint_and_high_intensity_distance() -> None:
    sprint = _line(8.0, 2.0)
    jog = _line(2.0, 4.0, start_ms=2_200, x0=sprint[-1][1] + 0.4)
    metrics = _by_key(player_tracking_metrics(_tracks({"a-1": sprint + jog})), "a-1")

    assert metrics["sprints"].value == 1
    assert metrics["top_speed_kmh"].value == 28.8
    assert metrics["high_intensity_distance_m"].value == pytest.approx(16.0, abs=0.01)


def test_impossible_jumps_and_lost_tracks_are_not_counted() -> None:
    path = _line(4.0, 4.0)
    path[10] = (path[10][0], path[10][1] + 30, path[10][2])   # salto de 30 m en 0,2 s y vuelta
    del path[15:20]                                            # 1 s sin la pista
    metrics = _by_key(player_tracking_metrics(_tracks({"a-1": path})), "a-1")

    discarded = metrics["distance_covered_m"].components[0]
    assert discarded.key == "discarded_segments" and discarded.value == 2
    # 20 tramos de 0,8 m: 2 descartados por el salto y 6 perdidos en el hueco.
    assert metrics["distance_covered_m"].value == pytest.approx(0.8 * 12, abs=0.01)


def test_periods_are_never_joined() -> None:
    both = _merge(_tracks({"a-1": _line(3.0, 2.0)}), _tracks({"a-1": _line(3.0, 2.0, x0=80.0)}, period=2))

    assert _by_key(player_tracking_metrics(both), "a-1")["distance_covered_m"].value == pytest.approx(12.0, abs=0.01)


def test_ball_and_shot_speed_use_the_second_after_the_shot() -> None:
    events = Events(video_offset_ms=0)
    shot = events.shot(2.0, A, "a-9", (80, 50), outcome=EventOutcome.SAVED)
    ball = [(t, 80.0, 25.0) for t in range(0, 2_001, 200)] + _line(30.0, 0.6, start_ms=2_200, x0=86.0, y=25.0)

    metrics = ball_tracking_metrics(_tracks({"ball": ball}), events.items)
    shot_speed = next(m for m in metrics if m.key == "shot_speed_kmh")

    assert next(m for m in metrics if m.key == "ball_speed_kmh").value == 108.0
    assert shot_speed.value == 108.0 and shot_speed.source_event_ids == [shot.event_id]
    assert ball_tracking_metrics(_tracks({"a-1": _line(1.0, 1.0)}))[0].available is False


def _carrier(defender_distance: float) -> TrackSet:
    return _tracks({
        "b-1": [(t, 50.0, 25.0) for t in range(0, 1_001, 200)],
        "ball": [(t, 50.5, 25.0) for t in range(0, 1_001, 200)],
        "a-1": [(t, 50.0 + defender_distance, 25.0) for t in range(0, 1_001, 200)],
    })


def test_pressure_by_proximity_positive_and_negative() -> None:
    close = _by_key(pressure_metrics(_carrier(3.0), (A, B)), team=A)
    far = _by_key(pressure_metrics(_carrier(8.0), (A, B)), team=A)

    assert close["pressure_proximity_share"].value == 100.0
    assert close["nearest_defender_m"].value == 3.0
    assert far["pressure_proximity_share"].value == 0.0
    assert _by_key(pressure_metrics(_carrier(3.0), (A, B)), team=B)["pressure_proximity_share"].available is False


def test_team_shape_with_known_geometry() -> None:
    tracks = _tracks({"a-1": [(0, 10.0, 10.0)], "a-2": [(0, 30.0, 10.0)], "a-3": [(0, 20.0, 40.0)],
                      "b-1": [(0, 60.0, 20.0)]})
    shape = _by_key(team_shape_metrics(tracks, (A, B)), team=A)

    assert shape["team_width_m"].value == 30.0
    assert shape["team_depth_m"].value == 20.0
    assert shape["team_compactness_m"].value == pytest.approx(round((14.1421 * 2 + 20) / 3, 1), abs=0.05)
    assert _by_key(team_shape_metrics(tracks, (A, B)), team=B)["team_width_m"].available is False


def test_speed_record_alert_once_per_episode_and_distance_milestones() -> None:
    first = _line(9.0, 3.0)                                              # 32,4 km/h
    rest = _line(2.0, 3.0, start_ms=3_200, x0=first[-1][1] + 0.4)
    second = _line(9.1, 2.0, start_ms=6_400, x0=rest[-1][1] + 1.8)      # +0,4 km/h: sin aviso
    alerts = tracking_alerts(_tracks({"a-1": first + rest + second, "b-1": _line(5.0, 210.0, y=40.0)}))

    assert [(a.player_id, a.facts[0].value) for a in alerts if a.kind == "speed_record"] == [("a-1", 32.4)]
    assert [(a.player_id, a.facts[0].value, a.clock_ms) for a in alerts if a.kind == "distance_milestone"] == [
        ("b-1", 1000, 200_000)
    ]
    assert all(a.origin == "simulated_fixture" and "simulado" in a.evidence_limits[0] for a in alerts)


# --- Entrada desde las observaciones de Persona 1 ---------------------------------

def _observation(track: str, video_ms: int, x: float, team: str | None = A, **extra) -> VisualTrackObservation:
    return VisualTrackObservation(
        observation_id=extra.get("observation_id", f"obs-{track}-{video_ms}"),
        match_id=extra.get("match_id", "test-001"), video_time_ms=video_ms, track_id=track,
        detector_confidence=0.9, team_id=team, position=extra.get("position", Position(x=x, y=50.0)),
    )


def test_video_clock_places_observations_in_their_period() -> None:
    events = Events(video_offset_ms=1_000)
    events.pass_(10, A, "a-1", (20, 50), (30, 50))
    events.pass_(5, A, "a-1", (30, 50), (40, 50), period=2)
    clock = VideoClock.from_events(events.items)

    assert clock.period_starts == ((1, 1_000), (2, 601_000))
    assert clock.locate(11_000) == (1, 10_000)
    assert clock.locate(611_000) == (2, 10_000)
    assert clock.locate(500) is None


def test_persona_1_observations_become_tracks_with_confirmed_identity_only() -> None:
    events = Events(video_offset_ms=0)
    events.pass_(1, A, "a-1", (20, 50), (30, 50))
    observations = (
        _observation("trk-7", 1_000, 10.0),
        _observation("trk-7", 1_200, 11.0),
        _observation("trk-9", 1_000, 50.0),
        _observation("ball", 1_000, 20.0, team=None),
        _observation("trk-ref", 1_000, 40.0, team=None),
        _observation("trk-7", 1_400, 12.0, position=None),
        _observation("trk-7", 1_400, 12.0, match_id="otro", observation_id="obs-otro"),
    )
    resolver = PlayerIdentityResolver({"a-1", "a-2"})
    identity = resolver.resolve(observations[0], ConfirmedPlayerIdentity(
        match_id="test-001", track_id="trk-7", player_id="a-1",
        evidence_kind=IdentityEvidenceKind.MANUAL_CONFIRMATION, evidence_reference="ref-1", verified_by="revisor",
    ))
    unconfirmed = resolver.resolve(observations[2])

    conversion = tracks_from_observations(
        metadata(), events.items,
        TrackingInput(observations=observations, identities=(identity, unconfirmed),
                      origin=PredictionOrigin.ACTUAL_MODEL),
    )
    tracks = conversion.tracks.tracks

    assert conversion.tracks.origin == "actual_model" and not conversion.tracks.is_simulated
    assert tracks["trk-7"].player_id == "a-1" and tracks["trk-9"].player_id is None
    assert tracks["ball"].kind is TrackedKind.BALL and tracks["trk-ref"].kind is TrackedKind.UNASSIGNED
    assert [s.x for s in tracks["trk-7"].samples] == [10.0, 11.0]  # campo de 100 m: 10 % = 10 m
    assert set(conversion.skipped_observation_ids) == {"obs-trk-7-1400", "obs-otro"}
    alerts = tracking_alerts(conversion.tracks)
    assert alerts == []  # pocas muestras: sin récords ni hitos


def test_contradicting_identities_are_dropped() -> None:
    events = Events(video_offset_ms=0)
    events.pass_(1, A, "a-1", (20, 50), (30, 50))
    first, second = _observation("trk-7", 1_000, 10.0), _observation("trk-7", 1_200, 11.0)
    resolver = PlayerIdentityResolver({"a-1", "a-2"})
    identities = tuple(
        resolver.resolve(obs, ConfirmedPlayerIdentity(
            match_id="test-001", track_id="trk-7", player_id=player,
            evidence_kind=IdentityEvidenceKind.MANUAL_CONFIRMATION, evidence_reference="ref", verified_by="r",
        ))
        for obs, player in ((first, "a-1"), (second, "a-2"))
    )

    conversion = tracks_from_observations(metadata(), events.items, TrackingInput((first, second), identities))

    assert conversion.conflicting_track_ids == ("trk-7",)
    assert conversion.tracks.tracks["trk-7"].player_id is None


# --- Datos simulados con el formato de Persona 1 ------------------------------------

def test_mock_produces_persona_1_observations_and_plausible_values() -> None:
    match = generate_analytics_scenario()
    mock = generate_mock_tracking(match.metadata, match.events)

    assert mock == generate_mock_tracking(match.metadata, match.events)
    assert mock.origin is PredictionOrigin.SIMULATED_FIXTURE
    assert all(isinstance(o, VisualTrackObservation) for o in mock.observations)
    assert len(mock.identities) == 14 and mock.goalkeeper_player_ids == {"aurora-1", "rio-1"}
    conversion = tracks_from_observations(match.metadata, match.events, mock)
    assert conversion.skipped_observation_ids == () and conversion.conflicting_track_ids == ()
    tracks = conversion.tracks
    assert {s.period for t in tracks.tracks.values() for s in t.samples} == {1, 2}

    metrics = tracking_metrics(tracks, ("team-aurora", "team-rio"), match.events)
    speeds = [m for m in metrics if m.player_id and m.key == "top_speed_kmh"]
    assert len(speeds) == 14 and all(10 <= m.value <= 31.5 for m in speeds)
    assert all(250 <= m.value <= 1_500 for m in metrics if m.key == "distance_covered_m")
    assert 80 <= next(m for m in metrics if m.key == "ball_speed_kmh").value <= 144
    for item in metrics:
        assert METRIC_CATALOG[item.key].unit == item.unit


def test_snapshot_uses_tracking_up_to_its_own_time_only() -> None:
    match = generate_analytics_scenario()
    tracks = tracks_from_observations(match.metadata, match.events, generate_mock_tracking(match.metadata, match.events)).tracks

    plain = build_snapshot(match.metadata, match.events[:40])
    early = build_snapshot(match.metadata, match.events[:40], tracking=tracks)
    late = MatchAnalytics(tracking_provider=lambda _: tracks).snapshot(match.metadata, match.events)

    def distance(snapshot):
        return next(m for m in snapshot.metrics if m.key == "distance_covered_m" and m.player_id == "aurora-8")

    assert distance(plain).available is False
    assert distance(early).available and distance(early).tracking_evidence.end_clock_ms <= early.clock_ms
    assert distance(late).value > distance(early).value
