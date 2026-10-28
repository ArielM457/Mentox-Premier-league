"""Servidor SOLO para pruebas de navegador: modelos HTTP dobles, MP4 MESSI real.

No se instala como ruta de producción. Ejecutar mediante validate_hybrid_browser.py.
"""

import asyncio
import json
import os
from pathlib import Path

# Nunca consumir credenciales o colas reales en esta prueba.
for name in ("EVENT_TRANSPORT", "VISION_OBSERVATION_TRANSPORT", "ROUTING_TRANSPORT"):
    os.environ[name] = "memory"
os.environ.update({
    "NARRATIVE_PROVIDER": "provisional", "SUPABASE_ENABLED": "false",
    "SOCCERNET_GAMESTATE_ENABLED": "false", "VISION_SIMULATOR_ENABLED": "auto",
    "VISION_STARTUP_MATCH_ID": "synthetic-live-001", "VISION_PREPARE_ON_STARTUP": "true",
    "AZURE_BLOB_SERVICE_ENDPOINT": "https://local-test-only.invalid",
    "VISION_VIDEO_BLOB_NAME": "messi/browser-fixture/match.mp4",
    "ROBOFLOW_SUITE_ENDPOINT": "http://127.0.0.1:8127/__test__/roboflow",
    "ROBOFLOW_SUITE_API_KEY": "local-test-key",
    "SOCCERNET_ENDPOINT": "http://127.0.0.1:8127/__test__/teamspotting",
    "SOCCERNET_API_KEY": "local-test-key",
})

from fastapi import HTTPException, Request
from fastapi.staticfiles import StaticFiles
from match_intelligence.main import app
from match_intelligence.adapters.http import integration_router as integration
from match_intelligence.adapters.http.routing_router import routing_pipeline

root = Path(os.environ["PRIME_BROWSER_REPLAY_DIR"])
counts = {"player": 0, "ball": 0, "pitch": 0, "teamspotting": 0, "synthetic_demo": 0}


async def local_artifacts():
    manifest = json.loads((root / "reference-manifest.json").read_text())
    names = {"match.mp4": "match.mp4", "events.jsonl": "reference-events.jsonl",
             "metadata.jsonl": "reference-metadata.jsonl", "tracking.jsonl": "reference-tracking.jsonl"}
    return manifest, {name: (root / filename).read_bytes() for name, filename in names.items()}


integration.simulated_video._download = local_artifacts


@app.get("/__test__/roboflow/health/ready")
async def spatial_ready():
    return {"status": "ready", "models": ["player", "ball", "pitch"], "device": "HTTP_TEST_DOUBLE"}


@app.post("/__test__/roboflow/v1/predict")
async def spatial(request: Request):
    if request.headers.get("x-api-key") != "local-test-key":
        raise HTTPException(401)
    payload = await request.body()
    if b"\xff\xd8" not in payload:
        raise HTTPException(422, "No se recibió un JPEG de navegador")
    await asyncio.sleep(0.02)
    output = []
    for model in ("player", "ball", "pitch"):
        counts[model] += 1
        detections = [] if model == "pitch" else [{"label": model, "confidence": 0.8,
            "bounding_box": [0.35, 0.3, 0.38, 0.38] if model == "player" else [0.5, 0.5, 0.51, 0.51]}]
        output.append({"model": model, "detections": detections})
    return {"results": output, "device": "HTTP_TEST_DOUBLE", "inference_ms": 20}


@app.get("/__test__/teamspotting/health/ready")
async def temporal_ready():
    return {"status": "ready", "device": "HTTP_TEST_DOUBLE"}


@app.post("/__test__/teamspotting/v1/predict")
async def temporal(request: Request):
    if request.headers.get("x-api-key") != "local-test-key":
        raise HTTPException(401)
    counts["teamspotting"] += 1
    await asyncio.sleep(0.05)
    return {"device": "HTTP_TEST_DOUBLE", "processing_time_ms": 50, "predictions": [
        {"prediction_id": f"p-{index}", "video_time_ms": time, "label": "pass", "confidence": 0.8}
        for index, time in enumerate((100, 2100, 3900, 82000))]}


@app.get("/__test__/status")
async def status():
    return {"providers": counts, "routing": routing_pipeline.status(),
            "simulator": integration.simulated_video.status(), "capture": integration.live_vision_capture.status("synthetic-live-001")}


app.mount("/", StaticFiles(directory=Path(__file__).resolve().parents[2] / "frontend" / "dist", html=True), name="test-frontend")
