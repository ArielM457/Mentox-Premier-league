"""Regresiones de concurrencia y aislamiento del arranque de modelos."""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from match_intelligence.adapters.http import integration_router as integration
from match_intelligence.application.match_session import NotFoundError
from match_intelligence.application.integrated_pipeline import PipelineArtifactError


def reset_preparation(monkeypatch):
    monkeypatch.setattr(integration, "model_preparation_task", None)
    monkeypatch.setattr(integration, "model_preparation_status", {
        "status": "idle", "match_id": None, "error": None,
    })


def test_cancelled_client_does_not_cancel_shared_preparation(monkeypatch) -> None:
    async def scenario():
        reset_preparation(monkeypatch)
        started, finish = asyncio.Event(), asyncio.Event()

        async def prepare(match_id):
            started.set()
            await finish.wait()
            integration.model_preparation_status.update(status="ready")
            return {"status": "ready", "match_id": match_id}

        monkeypatch.setattr(integration, "_prepare_models", prepare)
        client = asyncio.create_task(integration.prepare_live_models("m"))
        await started.wait()
        shared = integration.model_preparation_task
        client.cancel()
        with pytest.raises(asyncio.CancelledError):
            await client
        assert shared is not None and not shared.cancelled()
        with pytest.raises(HTTPException) as conflict:
            integration._start_model_preparation("different-match")
        assert conflict.value.status_code == 409
        finish.set()
        assert (await shared)["match_id"] == "m"
        refreshed = integration._start_model_preparation("m")
        assert refreshed is not shared
        assert (await refreshed)["status"] == "ready"

    asyncio.run(scenario())


def test_failed_model_does_not_restart_other_inflight_models(monkeypatch) -> None:
    monkeypatch.setenv("SOCCERNET_GAMESTATE_ENABLED", "true")
    async def scenario():
        reset_preparation(monkeypatch)
        called = []

        async def roboflow():
            return {"status": "ready"}

        async def teamspotting(match_id):
            await asyncio.sleep(0)
            called.append("teamspotting")
            return {"status": "ready", "predictions": 0}

        async def gamestate(match_id, metadata):
            called.append("gamestate")
            raise RuntimeError("Pesos inválidos")

        def missing(match_id):
            raise NotFoundError("m")

        monkeypatch.setattr(integration, "get_registry", lambda: SimpleNamespace(get=missing))
        monkeypatch.setattr(integration, "live_vision_settings", SimpleNamespace(endpoint="https://model"))
        monkeypatch.setattr(integration, "live_vision_capture", SimpleNamespace(ensure_ready=roboflow))
        monkeypatch.setattr(integration, "teamspotting_analysis", SimpleNamespace(prepare=teamspotting))
        monkeypatch.setattr(integration, "gamestate_analysis", SimpleNamespace(prepare=gamestate))
        with pytest.raises(Exception, match="Pesos inválidos"):
            await integration._start_model_preparation("m")
        assert sorted(called) == ["gamestate", "teamspotting"]
        states = integration.model_preparation_status["models"]
        assert states["teamspotting"]["status"] == "ready"
        assert states["gamestate"]["status"] == "failed"

    asyncio.run(scenario())


def test_runtime_status_does_not_require_old_local_artifacts(monkeypatch) -> None:
    def missing():
        raise PipelineArtifactError("Artefactos antiguos ausentes")

    monkeypatch.setattr(integration, "pipeline", SimpleNamespace(status=missing))
    result = asyncio.run(integration.integration_status())
    assert result["status"] == "historical_artifacts_unavailable"
    assert "model_preparation" in result["runtime"]


def test_blob_video_never_replays_observations_from_another_local_video(monkeypatch) -> None:
    monkeypatch.setenv("AZURE_BLOB_SERVICE_ENDPOINT", "https://blob")
    monkeypatch.setenv("VISION_VIDEO_BLOB_NAME", "new-match.mp4")
    monkeypatch.setattr(integration, "observation_playback", None)
    playback = integration.get_observation_playback()
    assert playback.snapshot()["total_observations"] == 0
