"""Flujo HTTP completo con proveedores de inferencia dobles, sin GPU ni Azure."""

import asyncio
from hashlib import sha256
from types import SimpleNamespace

import httpx
import pytest

from test_messi_replay import MATCH, prepared
from match_intelligence.main import app
from match_intelligence.adapters.http import integration_router as integration
from match_intelligence.adapters.http.registry import get_registry
from match_intelligence.application.live_vision_capture import LiveVisionCapture, LiveVisionSettings
from match_intelligence.application.teamspotting_analysis import TeamSpottingAnalysis, TeamSpottingSettings
from match_intelligence.application.realtime_observations import RealtimeObservationHub
from match_intelligence.application.vision_runtime import VisionObservationRuntime, VisionRuntimeSettings
from match_intelligence.application.routing import RoutedEventPipeline, MemoryRoutingTransport


class Predictor:
    async def readiness(self):
        return {"status": "ready", "models": ["player", "ball", "pitch"]}

    async def predict(self, image, content_type):
        return {"results": [{"model": model, "detections": [{
            "label": "player" if model == "player" else model,
            "confidence": 0.8, "bounding_box": [0.1, 0.1, 0.2, 0.3],
        }]} for model in ("player", "ball", "pitch")]}


def test_roboflow_teamspotting_messi_without_gamestate(monkeypatch):
    async def scenario():
        simulator, registry = await prepared(monkeypatch)
        hub = RealtimeObservationHub()
        runtime = VisionObservationRuntime(hub, VisionRuntimeSettings())
        settings = LiveVisionSettings("https://roboflow.test", "test-key")
        capture = LiveVisionCapture(Predictor(), runtime, settings)
        temporal = TeamSpottingAnalysis(runtime, TeamSpottingSettings(
            "https://teamspotting.test", "test-key", "https://storage.test", "videos", "match.mp4"))
        async def ready():
            return {"status": "ready"}
        async def video():
            return b"synthetic MP4 test double"
        async def predict(video):
            return {"predictions": [{"prediction_id": "p1", "label": "pass", "video_time_ms": 500, "confidence": 0.8}]}
        monkeypatch.setattr(temporal, "readiness", ready)
        monkeypatch.setattr(temporal, "_download_video", video)
        monkeypatch.setattr(temporal, "_predict", predict)
        monkeypatch.delenv("SOCCERNET_GAMESTATE_ENABLED", raising=False)
        monkeypatch.setenv("SOCCERNET_GAMESTATE_ENDPOINT", "https://retired-never-call.test")
        # Cualquier llamada a GameState haría fallar: no tiene siquiera prepare().
        monkeypatch.setattr(integration, "gamestate_analysis", object())
        monkeypatch.setattr(integration, "simulated_video", simulator)
        monkeypatch.setattr(integration, "get_registry", lambda: registry)
        monkeypatch.setattr(integration, "live_hub", hub)
        monkeypatch.setattr(integration, "vision_runtime", runtime)
        monkeypatch.setattr(integration, "live_vision_settings", settings)
        monkeypatch.setattr(integration, "live_vision_capture", capture)
        monkeypatch.setattr(integration, "teamspotting_analysis", temporal)
        monkeypatch.setattr(integration, "observation_playback", None)
        monkeypatch.setattr(integration, "model_preparation_task", None)
        monkeypatch.setattr(integration, "model_preparation_status", {"status": "idle", "match_id": None})
        routing = RoutedEventPipeline(MemoryRoutingTransport())
        monkeypatch.setattr(integration, "routing_pipeline", routing)
        app.dependency_overrides[get_registry] = lambda: registry
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                root = "/api/v1/integration"
                response = await client.post(root + f"/live/models/prepare?match_id={MATCH}")
                assert response.status_code == 200, response.text
                assert response.json()["models"]["gamestate"]["status"] == "retired"
                assert temporal.runs == 1
                assert hub.snapshot()["accepted"] == 0  # Preparación no publica el futuro.
                assert routing.status()["ingress_published"] == 0
                detail = (await client.get(f"/api/v1/matches/{MATCH}")).json()
                assert detail["data_source"] == "messi_simulator" and detail["duration_ms"] == 4000
                video = await client.get(root + "/live/video", headers={"range": "bytes=0-3"})
                assert video.status_code == 206 and video.content == b"synt"
                assert video.headers["content-range"].startswith("bytes 0-3/")
                suffix = await client.get(root + "/live/video", headers={"range": "bytes=-6"})
                assert suffix.status_code == 206 and suffix.content == b"double"
                invalid = await client.get(root + "/live/video", headers={"range": "bytes=999999-"})
                assert invalid.status_code == 416
                fallback = (await client.get("/api/v1/matches/synthetic-acceptance-001")).json()
                assert fallback["video"]["kind"] == "synthetic_timeline"

                async def control(action, at, generation=None):
                    result = await client.post(root + "/live/playback/" + action,
                                               json={"match_id": MATCH, "video_time_ms": at, "playback_generation": generation})
                    assert result.status_code == 200, result.text
                    return result.json()
                played = await control("play", 0)
                generation = played["playback_generation"]
                captured = await client.post(root + f"/live/capture/frame?match_id={MATCH}&video_time_ms=500",
                                             content=b"jpeg-double", headers={"content-type": "image/jpeg"})
                assert captured.status_code == 202 and captured.json()["models"] == 3
                await control("advance", 1000, generation)
                assert routing.status()["metrics_published"] == 1
                assert routing.transport.ingress[0]["payload"]["events"][0]["receiver_player_id"].endswith("player-7")
                response = await client.get(root + f"/live/observations?match_id={MATCH}&start_ms=0&end_ms=1000")
                observations = response.json()["observations"]
                assert {item["source"] for item in observations} == {
                    "roboflow-player", "roboflow-ball", "roboflow-pitch", "soccernet", "messi-simulator"}
                assert len([item for item in observations if item["kind"] == "simulated_match_event"]) == 1
                assert all(item["timestamp_ms"] <= 1000 for item in observations)
                await control("pause", 1000)
                paused = await client.post(root + f"/live/capture/frame?match_id={MATCH}&video_time_ms=2000", content=b"jpeg-double")
                assert paused.status_code == 409
                await control("advance", 4000, generation)
                assert routing.status()["important_published"] == 0
                new_generation = (await control("play", 1000))["playback_generation"]
                await control("seek", 1000)
                await control("advance", 4000, new_generation)  # Paquete de antes del salto.
                assert routing.status()["important_published"] == 0
                new_generation = (await control("play", 1000))["playback_generation"]
                await control("advance", 3000, new_generation)
                assert routing.status()["important_published"] == 1
                current_status = (await client.get(root + "/status")).json()
                assert current_status["artifact_scope"] == "current_blob_video"
                assert current_status["duration_ms"] == 4000
                assert current_status["media_sha256"] == simulator.replay.media_sha256
                runtime_status = current_status["runtime"]
                assert runtime_status["gamestate"]["status"] == "retired"
                assert runtime_status["simulator"]["events_routed"] == 2
                await control("restart", 0)
                recovered = (await client.get(root + f"/live/observations?match_id={MATCH}&start_ms=0&end_ms=1000")).json()["observations"]
                assert {item["source"] for item in recovered} == {"soccernet", "messi-simulator"}
                assert temporal.runs == 1  # Reinicio no repite la inferencia.
        finally:
            app.dependency_overrides.clear()
            await temporal.close()
            await runtime.close()
    asyncio.run(scenario())


def test_model_with_different_video_hash_does_not_enable_play(monkeypatch):
    async def scenario():
        simulator, registry = await prepared(monkeypatch)
        async def ready():
            return {"status": "ready"}
        async def wrong(match_id):
            return {"status": "ready", "media_sha256": sha256(b"other video").hexdigest()}
        monkeypatch.setattr(integration, "simulated_video", simulator)
        monkeypatch.setattr(integration, "get_registry", lambda: registry)
        monkeypatch.setattr(integration, "live_vision_settings", SimpleNamespace(endpoint="https://model"))
        monkeypatch.setattr(integration, "live_vision_capture", SimpleNamespace(ensure_ready=ready))
        monkeypatch.setattr(integration, "teamspotting_analysis", SimpleNamespace(prepare=wrong))
        monkeypatch.delenv("SOCCERNET_GAMESTATE_ENABLED", raising=False)
        with pytest.raises(Exception, match="vídeos diferentes"):
            await integration._prepare_models(MATCH)
    asyncio.run(scenario())
