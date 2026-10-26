"""Las rutas de captura y vídeo no cargan en memoria más de lo permitido."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from match_intelligence.adapters.http import integration_router
from match_intelligence.main import app

MATCH_ID = "synthetic-live-001"
FRAME = f"/api/v1/integration/live/capture/frame?match_id={MATCH_ID}&video_time_ms=1000"


@pytest.fixture
def playing(monkeypatch: pytest.MonkeyPatch):
    capture = integration_router.live_vision_capture
    monkeypatch.setattr(capture, "settings", replace(capture.settings, max_image_bytes=1_000))
    capture.play(MATCH_ID)
    yield capture
    capture.restart(MATCH_ID)


def test_paused_capture_is_rejected_before_reading_the_body() -> None:
    response = TestClient(app).post(FRAME, content=b"x" * 50_000, headers={"Content-Type": "image/jpeg"})
    assert response.status_code == 409


def test_declared_size_over_the_limit_is_rejected(playing) -> None:
    response = TestClient(app).post(FRAME, content=b"x" * 2_000, headers={"Content-Type": "image/jpeg"})
    assert response.status_code == 413


def test_streamed_body_stops_at_the_limit(playing) -> None:
    def chunks():
        for _ in range(5):
            yield b"x" * 400

    # Sin Content-Length: el corte ocurre mientras se lee.
    response = TestClient(app).post(FRAME, content=chunks(), headers={"Content-Type": "image/jpeg"})
    assert response.status_code == 413


def test_frame_within_the_limit_reaches_the_model(playing) -> None:
    response = TestClient(app).post(FRAME, content=b"x" * 500, headers={"Content-Type": "image/jpeg"})
    # Sin ROBOFLOW_SUITE_ENDPOINT, el modelo no está disponible: el límite ya no interviene.
    assert response.status_code == 503


class Blob:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.requested: list[tuple[int, int]] = []

    async def get_blob_properties(self):
        return SimpleNamespace(size=len(self.data))

    async def download_blob(self, offset: int, length: int):
        self.requested.append((offset, length))
        part = self.data[offset:offset + length]

        async def chunks():
            for start in range(0, len(part), 1_000):
                yield part[start:start + 1_000]

        return SimpleNamespace(chunks=chunks)


@pytest.fixture
def video(monkeypatch: pytest.MonkeyPatch):
    blob = Blob(bytes(range(256)) * 40)  # 10 240 bytes
    closed: list[str] = []

    class Service:
        def __init__(self, account_url, credential) -> None:
            pass

        def get_blob_client(self, container, blob):  # noqa: ARG002 - firma del SDK
            return blob_client

        async def close(self) -> None:
            closed.append("service")

    class Credential:
        async def close(self) -> None:
            closed.append("credential")

    blob_client = blob
    monkeypatch.setenv("AZURE_BLOB_SERVICE_ENDPOINT", "https://cuenta.blob.core.windows.net")
    monkeypatch.setenv("VISION_VIDEO_BLOB_NAME", "messi/lote/match.mp4")
    monkeypatch.setattr(integration_router, "BlobServiceClient", Service)
    monkeypatch.setattr(integration_router, "DefaultAzureCredential", Credential)
    monkeypatch.setattr(integration_router, "VIDEO_RANGE_MAX_BYTES", 4_096)
    return SimpleNamespace(blob=blob, closed=closed)


def test_open_range_is_capped_and_streamed(video) -> None:
    response = TestClient(app).get("/api/v1/integration/live/video", headers={"Range": "bytes=0-"})
    assert response.status_code == 206
    assert response.headers["content-range"] == "bytes 0-4095/10240"
    assert response.content == video.blob.data[:4_096]
    assert video.blob.requested == [(0, 4_096)]
    assert sorted(video.closed) == ["credential", "service"]


def test_full_video_is_streamed_without_a_range(video) -> None:
    response = TestClient(app).get("/api/v1/integration/live/video")
    assert response.status_code == 200
    assert response.content == video.blob.data
    assert sorted(video.closed) == ["credential", "service"]


def test_invalid_range_closes_the_clients(video) -> None:
    response = TestClient(app).get("/api/v1/integration/live/video", headers={"Range": "bytes=-5"})
    assert response.status_code == 416
    assert sorted(video.closed) == ["credential", "service"]
