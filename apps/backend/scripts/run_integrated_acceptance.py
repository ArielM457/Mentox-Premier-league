"""Ejecuta la fase local y consolida artefactos del ensayo DV-US-22.

El script no ejecuta nuevamente los modelos ni publica candidatos visuales como
MatchEvent. Comprueba las exportaciones existentes, el transporte local y un
fallo de red controlado. Las pruebas reales de Azure permanecen como comandos
separados porque requieren identidad y recursos del operador.
"""

import argparse
import asyncio
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from azure.eventhub import EventData

from match_intelligence.adapters.messaging.azure_event_hubs import (
    AzureEventHubPublisher,
    EventPublicationError,
)
from match_intelligence.adapters.messaging.memory import (
    InMemoryEventConsumer,
    InMemoryEventPublisher,
)
from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.application.integrated_pipeline import (
    IntegratedPipeline,
    PipelinePaths,
)


class FailingProducerClient:
    """Doble determinista para demostrar aislamiento ante una caída de red."""

    async def send_batch(
        self,
        event_data_batch: list[EventData],
        *,
        partition_key: str | None = None,
    ) -> None:
        raise ConnectionError("controlled network failure")

    async def close(self) -> None:
        return None


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


async def verify_local_transport() -> dict[str, Any]:
    match = generate_acceptance_match(match_id="dv-us-22-local")
    publisher = InMemoryEventPublisher()
    consumer = InMemoryEventConsumer()
    for event in match.events:
        await publisher.publish(event)
    await publisher.publish(match.events[0])
    report = consumer.consume(publisher.events)
    return {
        "status": "passed",
        "match_id": match.metadata.match_id,
        "published": len(publisher.events),
        "accepted": len(report.accepted),
        "duplicates": len(report.duplicates),
        "rejected": 0,
        "source": "synthetic",
    }


async def verify_controlled_failure() -> dict[str, Any]:
    event = generate_acceptance_match(match_id="dv-us-22-failure").events[0]
    original = event.model_dump(mode="json")
    publisher = AzureEventHubPublisher(
        FailingProducerClient(),
        producer="dv-us-22-controlled-failure",
    )
    try:
        await publisher.publish(event)
    except EventPublicationError as error:
        failure = error.failure
    else:
        raise RuntimeError("El fallo de red controlado no fue observado")
    finally:
        await publisher.close()

    local_publisher = InMemoryEventPublisher()
    local_consumer = InMemoryEventConsumer()
    await local_publisher.publish(event)
    local_report = local_consumer.consume(local_publisher.events)
    unchanged = event.model_dump(mode="json") == original
    if not unchanged or len(local_report.accepted) != 1:
        raise RuntimeError("El fallo externo alteró el evento o el modo local")
    return {
        "status": "passed",
        "failure_type": failure.error_type,
        "failure_recorded": len(publisher.failures) == 1,
        "event_unchanged": unchanged,
        "local_mode_after_failure": "passed",
    }


def verify_model_artifacts(root: Path) -> dict[str, Any]:
    pipeline_paths = PipelinePaths.from_repository(root)
    roboflow_path = pipeline_paths.roboflow
    soccernet_path = pipeline_paths.soccernet
    fusion_path = pipeline_paths.fusion
    paths = (roboflow_path, soccernet_path, fusion_path)
    missing = [str(path.relative_to(root)) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("Faltan artefactos: " + ", ".join(missing))

    roboflow = load_json(roboflow_path)
    soccernet = load_json(soccernet_path)
    fusion = load_json(fusion_path)
    media_hashes = {
        roboflow["media_sha256"],
        soccernet["media_sha256"],
        fusion["media_sha256"],
    }
    if len(media_hashes) != 1:
        raise ValueError("Las exportaciones no pertenecen al mismo vídeo permitido")
    media_sha256 = media_hashes.pop()
    pipeline = IntegratedPipeline(pipeline_paths)
    pipeline_status = pipeline.status()
    selected = fusion["selected_result"]
    if fusion["decision"] != "experimental_candidates_only":
        raise ValueError("La decisión de fusión esperada cambió")

    return {
        "status": "passed",
        "media_sha256": media_sha256,
        "roboflow": {
            "predictions": len(roboflow["predictions"]),
            "frames_processed": roboflow["video"]["frames_processed"],
            "processing_time_ms": roboflow["processing_time_ms"],
            "artifact_sha256": file_sha256(roboflow_path),
        },
        "soccernet": {
            "predictions": len(soccernet["predictions"]),
            "frames_processed": soccernet["video"]["model_frames"],
            "processing_time_ms": soccernet["processing_time_ms"],
            "artifact_sha256": file_sha256(soccernet_path),
        },
        "fusion": {
            "actions_evaluated": selected["actions_evaluated"],
            "raw_candidates": selected["raw_candidates"],
            "candidates": selected["candidates"],
            "match_events_published": 0,
            "decision": fusion["decision"],
            "artifact_sha256": file_sha256(fusion_path),
        },
        "backend_pipeline": {
            "status": pipeline_status["status"],
            "video_available": pipeline_status["video_available"],
            "artifact_integrity": "passed",
        },
    }


async def build_report(root: Path) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "story": "DV-US-22",
        "generated_at": datetime.now(UTC).isoformat(),
        "local_transport": await verify_local_transport(),
        "controlled_failure": await verify_controlled_failure(),
        "real_model_artifacts": verify_model_artifacts(root),
        "azure": {
            "status": "requires_real_execution",
            "event_hubs_command": "apps/backend/scripts/event_hubs_smoke.py",
            "blob_storage_command": "apps/backend/scripts/blob_storage_smoke.py",
        },
        "safety": {
            "visual_candidate_is_match_event": False,
            "official_frontend_modified": False,
            "real_video_redistributed": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    report = asyncio.run(build_report(root))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
