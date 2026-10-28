"""Fallos controlados: sin repetir jugadas ni conservar captura tras pausa."""

import asyncio

import pytest

from test_messi_replay import MATCH, prepared
from match_intelligence.application.realtime_observations import RealtimeObservationHub
from match_intelligence.application.routing import MemoryRoutingTransport, RoutedEventPipeline
from match_intelligence.application.teamspotting_analysis import TeamSpottingAnalysis, TeamSpottingSettings
from match_intelligence.adapters.http.integration_router import video_response
from fastapi import HTTPException


def test_publication_retry_does_not_repeat_already_routed_event(monkeypatch):
    async def scenario():
        service, _ = await prepared(monkeypatch)
        pipeline = RoutedEventPipeline(MemoryRoutingTransport())
        hub = RealtimeObservationHub()
        class FailingPublisher:
            calls = 0
            async def publish(self, observation):
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError("canal de observaciones caído")
                return await hub.publish(observation)
        publisher = FailingPublisher()
        await service.control("play", MATCH, 0, publisher, pipeline)
        with pytest.raises(RuntimeError):
            await service.control("advance", MATCH, 1000, publisher, pipeline)
        assert pipeline.status()["ingress_published"] == 1
        await service.control("advance", MATCH, 1000, publisher, pipeline)
        assert pipeline.status()["ingress_published"] == 1
        assert hub.snapshot()["accepted"] == 1
    asyncio.run(scenario())


def test_pause_interrupts_a_slow_queue_before_next_event(monkeypatch):
    async def scenario():
        service, _ = await prepared(monkeypatch)
        started, finish = asyncio.Event(), asyncio.Event()
        hub = RealtimeObservationHub()
        class SlowPipeline:
            calls = 0
            async def evaluate(self, request):
                self.calls += 1
                started.set()
                await finish.wait()
        pipeline = SlowPipeline()
        await service.control("play", MATCH, 0, hub, pipeline)
        task = asyncio.create_task(service.control("advance", MATCH, 4000, hub, pipeline))
        await started.wait()
        service.halt(MATCH)
        finish.set()
        await task
        assert pipeline.calls == 1  # El tiro siguiente no se entrega tras pausar.
        assert not service._playing
    asyncio.run(scenario())


def test_failed_delivery_is_retried_even_after_resume_at_a_later_time(monkeypatch):
    async def scenario():
        service, _ = await prepared(monkeypatch)
        hub = RealtimeObservationHub()
        class RecoveringPipeline(RoutedEventPipeline):
            failed = True
            async def evaluate(self, request):
                if self.failed:
                    raise RuntimeError("Service Bus no accesible")
                return await super().evaluate(request)
        pipeline = RecoveringPipeline(MemoryRoutingTransport())
        await service.control("play", MATCH, 0, hub, pipeline)
        with pytest.raises(RuntimeError):
            await service.control("advance", MATCH, 3000, hub, pipeline)
        assert service.status()["events_pending_delivery"] == 2
        service.halt(MATCH)
        pipeline.failed = False
        await service.control("play", MATCH, 3500, hub, pipeline)
        await service.control("advance", MATCH, 4000, hub, pipeline)
        assert pipeline.status()["ingress_published"] == 2
        assert pipeline.status()["important_published"] == 1
        assert service.status()["events_pending_delivery"] == 0
    asyncio.run(scenario())


def test_visual_transport_failure_does_not_block_important_delivery(monkeypatch):
    async def scenario():
        service, _ = await prepared(monkeypatch)
        pipeline = RoutedEventPipeline(MemoryRoutingTransport())
        class FailedVision:
            async def publish(self, observation):
                raise RuntimeError("Event Hub de visión caído")
        publisher = FailedVision()
        await service.control("play", MATCH, 0, publisher, pipeline)
        with pytest.raises(RuntimeError, match="Observaciones pendientes"):
            await service.control("advance", MATCH, 4000, publisher, pipeline)
        assert pipeline.status()["important_published"] == 1
        assert service.status()["events_routed"] == 2
        assert service.status()["observation_error"]
        with pytest.raises(RuntimeError):
            await service.control("advance", MATCH, 4000, publisher, pipeline)
        assert pipeline.status()["important_published"] == 1
    asyncio.run(scenario())


@pytest.mark.parametrize("bad", [
    {}, {"predictions": None}, {"predictions": [{"prediction_id": "p", "video_time_ms": -1, "label": "pass", "confidence": 0.9}]},
    {"predictions": [{"prediction_id": "p", "video_time_ms": 1, "label": "pass", "confidence": float("nan")}]},
])
def test_malformed_teamspotting_response_does_not_cache_fake_success(monkeypatch, bad):
    async def scenario():
        analysis = TeamSpottingAnalysis(None, TeamSpottingSettings("https://model", "key", "https://blob", "videos", "match.mp4"))
        async def ready():
            return {"status": "ready"}
        async def predict(video):
            return bad
        monkeypatch.setattr(analysis, "readiness", ready)
        monkeypatch.setattr(analysis, "_predict", predict)
        analysis.bind_video(b"video")
        with pytest.raises(Exception):
            await analysis.prepare(MATCH)
        assert analysis.status()["status"] == "failed"
        assert analysis.predictions == ()
    asyncio.run(scenario())


@pytest.mark.parametrize("header,start,end", [(None, 0, 9), ("bytes=0-", 0, 9), ("bytes=3-5", 3, 5), ("bytes=-3", 7, 9), ("bytes=7-999", 7, 9)])
def test_video_ranges(header, start, end):
    response = video_response(b"0123456789", header, "hash")
    assert response.body == b"0123456789"[start:end + 1]
    assert response.status_code == (206 if header else 200)


@pytest.mark.parametrize("header", ["bytes=-0", "bytes=9-2", "bytes=10-", "bytes=0-1,3-4", "items=0-1", "bytes=-", "bytes=x-y"])
def test_invalid_video_ranges(header):
    with pytest.raises(HTTPException) as error:
        video_response(b"0123456789", header, "hash")
    assert error.value.status_code == 416
