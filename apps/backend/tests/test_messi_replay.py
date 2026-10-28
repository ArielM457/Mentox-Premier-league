import asyncio
from hashlib import sha256
import json

import pytest

from match_intelligence.adapters.sources.messi_replay import convert_messi_replay
from match_intelligence.adapters.http.registry import _default_registry
from match_intelligence.application.simulated_video import SimulatedVideo
from match_intelligence.application.realtime_observations import RealtimeObservationHub
from match_intelligence.application.routing import MemoryRoutingTransport, RoutedEventPipeline

MATCH = "synthetic-live-001"


def jsonl(items):
    return "\n".join(json.dumps(item) for item in items).encode()


def replay_files():
    metadata = [
        {"record_type": "replay", "schema": "uos-footballmarl.replay/3"},
        {"record_type": "schemas", "events": "uos-footballmarl.events/6", "tracking": "uos-footballmarl.tracking/2"},
        {"record_type": "coordinates", "origin": "pitch_center", "pitch": {"length": 105, "width": 68}},
        {"record_type": "timebase", "control_fps": 15, "video_duration_s": 4},
        {"record_type": "roster", "starter_player_ids": list(range(22)), "team_id": [0] * 11 + [1] * 11},
    ]
    events = [
        {"type": "period_start", "event_id": 0, "video_time_s": 0, "index": 0},
        {"type": "touch", "label": "PASS", "event_id": 1, "touch_id": 0, "f": 1,
         "video_time_s": 0, "player_id": 6, "team": 0, "ball_pos": [0, 0, 0.1]},
        {"type": "pass_outcome", "event_id": 2, "video_time_s": 0, "source_touch_id": 0,
         "outcome_frame": 16, "outcome": "completed", "team": 0, "player": 6, "receiver": 7,
         "distance_m": 10, "launch_speed": 15},
        {"type": "touch", "label": "DRIBBLE", "event_id": 3, "touch_id": 1, "f": 16,
         "video_time_s": 1, "player_id": 7, "team": 0, "ball_pos": [10, 0, 0.1]},
        {"type": "period_start", "event_id": 4, "video_time_s": 2, "index": 1},
        {"type": "shot_outcome", "event_id": 5, "video_time_s": 2, "outcome_frame": 46,
         "outcome": "goal", "team": 0, "player": 7, "distance_m": 20, "launch_speed": 22},
    ]
    tracking = [{"video_time_s": time, "players": {
        "player_id": list(range(22)), "team_id": [0] * 11 + [1] * 11,
        "pos": [[index, 0] for index in range(22)], "gk": [int(index in (0, 11)) for index in range(22)],
        "on_pitch": [1] * 22}, "ball": {"pos": [time, 0, 0.1]}}
        for time in (0, 1, 2, 3)]
    artifacts = {"match.mp4": b"synthetic MP4 test double", "metadata.jsonl": jsonl(metadata),
                 "events.jsonl": jsonl(events), "tracking.jsonl": jsonl(tracking)}
    return manifest_for(artifacts), artifacts


def manifest_for(artifacts):
    return {"schema_version": "the-prime-moment.messi-match.v1", "source": "synthetic", "video_duration_seconds": 4,
            "artifacts": [{"name": name, "bytes": len(data), "sha256": sha256(data).hexdigest()}
                          for name, data in artifacts.items()]}


def test_replay_preserves_source_identity_and_completion_time():
    manifest, artifacts = replay_files()
    replay = convert_messi_replay(MATCH, manifest, artifacts)
    assert len(replay.metadata.players) == 22
    assert replay.metadata.players[0].name == "Jugador 0"
    assert all(player.shirt_number is None for player in replay.metadata.players)
    assert len(replay.events) == 2  # No duplicar touch + pass_outcome.
    passed, goal = replay.events
    assert passed.video_time_ms == 1000  # No revelar el receptor al lanzar.
    assert passed.player_id.endswith("player-6")
    assert passed.receiver_player_id.endswith("player-7")
    assert passed.outcome == "success" and passed.source == "synthetic"
    assert passed.end.x == pytest.approx((10 + 52.5) / 105 * 100)
    assert goal.video_time_ms == 3000 and goal.clock_ms == 1000 and goal.period == 2
    assert replay.tracking[0].objects[0].x_m == 52.5
    assert replay.tracking[0].source == "synthetic_simulator"
    assert replay.duration_ms == 4000


def test_event_ids_are_repeatable_but_do_not_collide_between_videos():
    manifest, artifacts = replay_files()
    one = convert_messi_replay(MATCH, manifest, artifacts)
    again = convert_messi_replay(MATCH, manifest, artifacts)
    assert [item.event_id for item in one.events] == [item.event_id for item in again.events]
    artifacts["match.mp4"] += b"different video"
    other = convert_messi_replay(MATCH, manifest_for(artifacts), artifacts)
    assert {item.event_id for item in one.events}.isdisjoint(item.event_id for item in other.events)


@pytest.mark.parametrize("filename", ["match.mp4", "events.jsonl", "tracking.jsonl", "metadata.jsonl"])
def test_mismatched_artifacts_fail_closed(filename):
    manifest, artifacts = replay_files()
    artifacts[filename] += b" "
    with pytest.raises(ValueError, match="Integridad"):
        convert_messi_replay(MATCH, manifest, artifacts)


@pytest.mark.parametrize("change", ["foreign_player", "duplicate_event", "unknown_schema", "nan", "duplicate_tracking"])
def test_invalid_replay_is_not_silently_replaced_by_mock(change):
    _, artifacts = replay_files()
    if change == "unknown_schema":
        artifacts["metadata.jsonl"] = artifacts["metadata.jsonl"].replace(b"events/6", b"events/999")
    elif change == "duplicate_tracking":
        artifacts["tracking.jsonl"] += b"\n" + artifacts["tracking.jsonl"].splitlines()[-1]
    else:
        events = [json.loads(line) for line in artifacts["events.jsonl"].splitlines()]
        if change == "foreign_player":
            events[2]["receiver"] = 15  # Equipo opuesto.
        elif change == "duplicate_event":
            events.append(events[2])
        else:
            events[2]["outcome_frame"] = float("nan")
        artifacts["events.jsonl"] = jsonl(events)
    with pytest.raises(ValueError):
        convert_messi_replay(MATCH, manifest_for(artifacts), artifacts)


def test_playback_is_causal_deduplicated_and_routes_to_both_queues(monkeypatch):
    async def scenario():
        service, registry = await prepared(monkeypatch)
        hub = RealtimeObservationHub()
        pipeline = RoutedEventPipeline(MemoryRoutingTransport())
        async def control(action, at):
            await service.control(action, MATCH, at, hub, pipeline)
        await control("advance", 4000)
        assert pipeline.status()["ingress_published"] == 0
        await control("play", 0)
        await control("advance", 500)
        assert pipeline.status()["ingress_published"] == 0
        await control("pause", 1000)
        assert pipeline.status()["metrics_published"] == 1
        await control("advance", 4000)
        assert pipeline.status()["important_published"] == 0
        await control("play", 1000)
        await control("advance", 3000)
        assert pipeline.status()["important_published"] == 1
        await control("restart", 0)
        await control("play", 0)
        await control("advance", 4000)
        assert pipeline.status()["ingress_published"] == 2
        session = registry.get(MATCH)
        assert len(session.events_until(999)) == 0
        assert session.snapshot(2999).score[session.metadata.home_team.team_id] == 0
        assert session.snapshot(3000).score[session.metadata.home_team.team_id] == 1
        assert session.duration_ms == 4000
    asyncio.run(scenario())


async def prepared(monkeypatch):
    monkeypatch.setenv("AZURE_BLOB_SERVICE_ENDPOINT", "https://storage.example")
    monkeypatch.setenv("VISION_VIDEO_BLOB_NAME", "messi/batch/messi-001/match.mp4")
    monkeypatch.setenv("VISION_SIMULATOR_ENABLED", "auto")
    monkeypatch.setenv("VISION_STARTUP_MATCH_ID", MATCH)
    service = SimulatedVideo()
    async def download():
        return replay_files()
    monkeypatch.setattr(service, "_download", download)
    registry = _default_registry()
    await service.prepare(MATCH, registry)
    return service, registry


def test_model_candidates_never_impute_identity_or_change_statistics(monkeypatch):
    async def scenario():
        service, _ = await prepared(monkeypatch)
        predictions = [
            {"prediction_id": "a", "label": "pass", "video_time_ms": 50, "confidence": 0.7},
            {"prediction_id": "b", "label": "pass", "video_time_ms": 100, "confidence": 0.8},
            {"prediction_id": "wrong-kind", "label": "shot", "video_time_ms": 50},
            {"prediction_id": "future", "label": "pass", "video_time_ms": 1100},
        ]
        assert service.observations(MATCH, 0, 999, predictions) == []
        obs = service.observations(MATCH, 0, 1000, predictions)[0]
        assert obs.source == "messi-simulator"
        assert len(obs.payload["model_candidates"]) == 2
        assert obs.payload["identity_source"] == "messi_simulator"
        assert obs.payload["confidence"] is None
        assert len(service.replay.events) == 2
        assert service.observations("other", 0, 4000, predictions) == []
        metrics = service.analytics(MATCH, 1000)["metrics"]
        assert any(item["key"] == "pass_distance_m" and item["value"] == 10 for item in metrics)
        assert not any(item["key"] == "shot_launch_speed_kmh" for item in metrics)
        assert not any(item["key"] == "top_speed_kmh" and item["available"] for item in metrics)
    asyncio.run(scenario())


def test_simulator_cache_does_not_replace_session_twice(monkeypatch):
    async def scenario():
        service, registry = await prepared(monkeypatch)
        original = registry.get(MATCH)
        await service.prepare(MATCH, registry)
        assert registry.get(MATCH) is original
        registry.load_synthetic(scenario="live", match_id=MATCH)
        await service.prepare(MATCH, registry)
        assert registry.get(MATCH).data_source == "messi_simulator"
        assert (await service.prepare("other", registry))["status"] == "disabled"
        assert service.match_id == MATCH
    asyncio.run(scenario())


def test_corrupt_bundle_does_not_replace_ariel_fallback(monkeypatch):
    async def scenario():
        service, registry = await prepared(monkeypatch)
        registry.load_synthetic(scenario="live", match_id=MATCH)
        before = registry.get(MATCH)
        service._key = None
        async def corrupt():
            manifest, artifacts = replay_files()
            artifacts["events.jsonl"] += b"bad"
            return manifest, artifacts
        monkeypatch.setattr(service, "_download", corrupt)
        with pytest.raises(ValueError, match="Integridad"):
            await service.prepare(MATCH, registry)
        assert registry.get(MATCH) is before
        assert service.phase == "failed"
    asyncio.run(scenario())
