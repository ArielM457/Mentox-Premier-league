import asyncio

import pytest

from match_intelligence.application.live_vision_capture import (
    CaptureNotPlayingError,
    CaptureUnavailableError,
    LiveVisionCapture,
    LiveVisionSettings,
)


class Predictor:
    async def readiness(self):
        return {"status": "ready", "models": ["player", "ball", "pitch"]}

    async def predict(self, image, content_type):
        return {
            "device": "test-gpu",
            "inference_ms": 12.5,
            "results": [
                {
                    "model": "player",
                    "detections": [
                        {"label": "player", "confidence": 0.9, "bounding_box": [0.1, 0.2, 0.3, 0.4]}
                    ],
                },
                {"model": "ball", "detections": []},
            ],
        }


class Publisher:
    def __init__(self):
        self.items = []

    async def publish_many(self, observations):
        self.items.extend(observations)
        return len(observations)


class PredictorNotReady(Predictor):
    async def readiness(self):
        return {"status": "starting"}


def capture():
    publisher = Publisher()
    service = LiveVisionCapture(
        Predictor(),
        publisher,
        LiveVisionSettings("https://model.example", "secret", interval_ms=1000),
    )
    return service, publisher


def test_capture_is_rejected_until_play() -> None:
    async def scenario():
        service, _ = capture()
        with pytest.raises(CaptureNotPlayingError):
            await service.capture(
                match_id="match-1", video_time_ms=0, image=b"jpeg", content_type="image/jpeg"
            )

    asyncio.run(scenario())


def test_model_is_prepared_before_playback() -> None:
    async def scenario():
        service, _ = capture()
        result = await service.ensure_ready()
        assert result["status"] == "ready"
        assert service.status()["model_ready"] is True
        assert service.status()["playing"] is False

    asyncio.run(scenario())


def test_model_not_ready_does_not_enable_capture() -> None:
    async def scenario():
        service = LiveVisionCapture(
            PredictorNotReady(),
            Publisher(),
            LiveVisionSettings("https://model.example", "secret"),
        )
        with pytest.raises(CaptureUnavailableError, match="no está listo"):
            await service.ensure_ready()
        assert service.status()["model_ready"] is False
        assert service.status()["playing"] is False

    asyncio.run(scenario())


def test_play_publishes_normalized_observations_and_pause_stops() -> None:
    async def scenario():
        service, publisher = capture()
        service.play("match-1")
        result = await service.capture(
            match_id="match-1", video_time_ms=1000, image=b"jpeg", content_type="image/jpeg"
        )
        assert result["accepted"] is True
        assert result["observations"] == 1
        assert publisher.items[0].source == "roboflow-player"
        assert publisher.items[0].payload["match_id"] == "match-1"
        service.pause("match-1")
        with pytest.raises(CaptureNotPlayingError):
            await service.capture(
                match_id="match-1", video_time_ms=2000, image=b"jpeg2", content_type="image/jpeg"
            )

    asyncio.run(scenario())


def test_interval_skips_duplicate_second_without_model_call() -> None:
    async def scenario():
        service, _ = capture()
        service.play("match-1")
        await service.capture(
            match_id="match-1", video_time_ms=1000, image=b"one", content_type="image/jpeg"
        )
        result = await service.capture(
            match_id="match-1", video_time_ms=1500, image=b"two", content_type="image/jpeg"
        )
        assert result == {"accepted": False, "reason": "capture_interval"}

    asyncio.run(scenario())


def test_seeking_back_allows_capture_at_the_new_position() -> None:
    async def scenario():
        service, _ = capture()
        service.play("m")
        await service.capture(match_id="m", video_time_ms=8000, image=b"jpeg", content_type="image/jpeg")
        service.seek("m")
        result = await service.capture(match_id="m", video_time_ms=1000, image=b"jpeg", content_type="image/jpeg")
        assert result["accepted"] is True

    asyncio.run(scenario())


def test_pause_and_quick_resume_discard_old_inflight_frame() -> None:
    async def scenario():
        service, publisher = capture()
        started, finish = asyncio.Event(), asyncio.Event()

        class SlowPredictor(Predictor):
            async def predict(self, image, content_type):
                started.set()
                await finish.wait()
                return await super().predict(image, content_type)

        service.predictor = SlowPredictor()
        service.play("m")
        task = asyncio.create_task(service.capture(
            match_id="m", video_time_ms=8000, image=b"jpeg", content_type="image/jpeg",
        ))
        await started.wait()
        service.pause("m")
        service.play("m")
        finish.set()
        assert (await task)["accepted"] is False
        assert publisher.items == []

    asyncio.run(scenario())
