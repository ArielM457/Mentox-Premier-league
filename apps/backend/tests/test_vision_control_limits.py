"""El simulador MESSI y los modelos son compartidos: un visitante no puede adelantarlos ni despertarlos a voluntad."""

import asyncio

import httpx
from fastapi.testclient import TestClient

from test_messi_replay import MATCH, prepared
from match_intelligence.main import app
from match_intelligence.adapters.http import integration_router as integration
from match_intelligence.application.realtime_observations import RealtimeObservationHub
from match_intelligence.application.routing import MemoryRoutingTransport, RoutedEventPipeline
from match_intelligence.application.vision_runtime import VisionObservationRuntime, VisionRuntimeSettings

ROOT = "/api/v1/integration/live"


def test_advance_needs_the_current_generation_and_cannot_outrun_the_video(monkeypatch):
    async def scenario():
        simulator, _ = await prepared(monkeypatch)
        monkeypatch.setattr(integration, "simulated_video", simulator)
        monkeypatch.setattr(integration, "vision_runtime", VisionObservationRuntime(RealtimeObservationHub(), VisionRuntimeSettings()))
        monkeypatch.setattr(integration, "observation_playback", None)
        monkeypatch.setattr(integration, "routing_pipeline", RoutedEventPipeline(MemoryRoutingTransport()))
        monkeypatch.setattr(integration, "model_preparation_status", {"status": "ready", "match_id": MATCH})
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            async def post(action, at, generation=None):
                return await client.post(
                    f"{ROOT}/playback/{action}",
                    json={"match_id": MATCH, "video_time_ms": at, "playback_generation": generation},
                )

            generation = (await post("play", 0)).json()["playback_generation"]
            anonymous = await post("advance", 1000)
            # El replay de prueba dura 4 s: 3,5 s no pudo transcurrir justo después de Play.
            ahead = await post("advance", 3500, generation)
            assert simulator._position == 0
            valid = await post("advance", 1000, generation)
            assert simulator._position == 1000
            await post("seek", 1000)
            stale = await post("advance", 3500, generation)

        assert anonymous.status_code == 409 and "playback_generation" in anonymous.json()["detail"]
        assert ahead.status_code == 409 and "tiempo transcurrido" in ahead.json()["detail"]
        assert valid.status_code == 200
        # Un paquete de antes del salto se ignora sin error, como antes.
        assert stale.status_code == 200 and simulator._position == 1000

    asyncio.run(scenario())


def test_only_the_video_match_can_wake_the_models(monkeypatch):
    monkeypatch.setenv("VISION_STARTUP_MATCH_ID", MATCH)
    started = []

    async def start(match_id):
        started.append(match_id)
        return {"status": "ready", "match_id": match_id}

    monkeypatch.setattr(integration, "_start_model_preparation", start)
    client = TestClient(app)

    other = client.post(f"{ROOT}/models/prepare", params={"match_id": "synthetic-acceptance-001"})
    missing = client.post(f"{ROOT}/models/prepare")
    video = client.post(f"{ROOT}/models/prepare", params={"match_id": MATCH})

    assert other.status_code == 404
    assert missing.status_code == 422
    assert video.status_code == 200 and started == [MATCH]
