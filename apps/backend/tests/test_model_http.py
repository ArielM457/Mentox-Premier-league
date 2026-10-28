import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
import aiohttp

from match_intelligence.application.live_vision_capture import (
    CaptureUnavailableError, LiveVisionSettings, RoboflowSuitePredictor,
)
from match_intelligence.application.model_http import model_payload, ModelStartingError, wait_for_model


class Response:
    def __init__(self, text, status=200):
        self.body, self.status = text, status

    async def text(self):
        return self.body


def test_azure_proxy_error_text_is_kept_for_diagnostics():
    assert asyncio.run(model_payload(Response("stream timeout", 504)))["detail"] == "stream timeout"


def test_cold_start_retries_without_repeating_inference():
    async def scenario():
        calls = 0
        async def health():
            nonlocal calls
            calls += 1
            if calls < 3:
                raise ModelStartingError("arrancando")
            return {"status": "ready"}
        assert (await wait_for_model(health, timeout_seconds=1, interval_seconds=0))["status"] == "ready"
        assert calls == 3
        async def unauthorized():
            raise ValueError("401")
        with pytest.raises(ValueError, match="401"):
            await wait_for_model(unauthorized)
    asyncio.run(scenario())


def test_cold_start_deadline_is_bounded():
    async def not_ready():
        raise ModelStartingError("no GPU")
    with pytest.raises(ModelStartingError):
        asyncio.run(wait_for_model(not_ready, timeout_seconds=0))


@pytest.mark.parametrize("change", ["missing_detections", "invalid_box", "duplicate_model", "nan_confidence"])
def test_invalid_roboflow_results_are_rejected(monkeypatch, change):
    async def scenario():
        import json
        outputs = [{"model": model, "detections": []} for model in ("player", "ball", "pitch")]
        if change == "missing_detections":
            del outputs[0]["detections"]
        elif change == "duplicate_model":
            outputs.append(outputs[0])
        else:
            outputs[0]["detections"] = [{"label": "player", "bounding_box": [0.2, 0.1, 0.3, 0.5], "confidence": 0.9}]
            if change == "invalid_box":
                outputs[0]["detections"][0]["bounding_box"][0] = 2
            else:
                outputs[0]["detections"][0]["confidence"] = float("nan")
        predictor = RoboflowSuitePredictor(LiveVisionSettings("https://model", "key"))
        @asynccontextmanager
        async def post(*args, **kwargs):
            yield Response(json.dumps({"results": outputs}))
        monkeypatch.setattr(predictor, "_session_for_request", lambda: SimpleNamespace(post=post))
        with pytest.raises(CaptureUnavailableError):
            await predictor.predict(b"jpeg", "image/jpeg")
    asyncio.run(scenario())


def test_roboflow_prediction_requires_all_three_model_outputs(monkeypatch):
    async def scenario():
        predictor = RoboflowSuitePredictor(LiveVisionSettings("https://model", "key"))

        @asynccontextmanager
        async def post(*args, **kwargs):
            yield Response('{"results":[{"model":"player","detections":[]}]}')

        monkeypatch.setattr(predictor, "_session_for_request", lambda: SimpleNamespace(post=post))
        with pytest.raises(CaptureUnavailableError, match="tres modelos"):
            await predictor.predict(b"jpeg", "image/jpeg")

    asyncio.run(scenario())


def test_roboflow_connection_failure_is_reported_as_unavailable(monkeypatch):
    async def scenario():
        predictor = RoboflowSuitePredictor(LiveVisionSettings("https://model", "key"))

        @asynccontextmanager
        async def post(*args, **kwargs):
            raise aiohttp.ClientConnectionError("Conexión cerrada")
            yield

        monkeypatch.setattr(predictor, "_session_for_request", lambda: SimpleNamespace(post=post))
        with pytest.raises(CaptureUnavailableError, match="no respondió"):
            await predictor.predict(b"jpeg", "image/jpeg")

    asyncio.run(scenario())
