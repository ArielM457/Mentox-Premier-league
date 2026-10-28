"""Validación offline de un paquete MESSI ya descargado; no llama a Azure/GPU."""

import argparse
import asyncio
from collections import Counter
import json
from pathlib import Path
from time import perf_counter

from match_intelligence.adapters.sources.messi_replay import convert_messi_replay
from match_intelligence.application.simulated_video import SimulatedVideo
from match_intelligence.application.realtime_observations import RealtimeObservationHub
from match_intelligence.application.routing import MemoryRoutingTransport, RoutedEventPipeline


async def validate_playback(replay):
    service = SimulatedVideo()
    service.replay, service.match_id, service.phase = replay, replay.metadata.match_id, "ready"
    hub = RealtimeObservationHub()
    pipeline = RoutedEventPipeline(MemoryRoutingTransport())
    generation = await service.control("play", service.match_id, 0, hub, pipeline)
    for position in range(0, replay.duration_ms + 1000, 1000):
        await service.control("advance", service.match_id, min(position, replay.duration_ms), hub, pipeline, generation=generation)
    await service.control("pause", service.match_id, replay.duration_ms, hub, pipeline)
    total_routed = pipeline.status()["ingress_published"]
    assert total_routed == sum(event.type.value != "restart" for event in replay.events)
    assert hub.snapshot()["accepted"] == len(replay.events)
    assert service.status()["events_pending_delivery"] == 0
    # Repetir el mismo vídeo no vuelve a publicar sus hechos ni estadísticas.
    await service.control("restart", service.match_id, 0, hub, pipeline)
    await service.control("play", service.match_id, 0, hub, pipeline)
    await service.control("advance", service.match_id, replay.duration_ms, hub, pipeline)
    await service.control("pause", service.match_id, replay.duration_ms, hub, pipeline)
    assert pipeline.status()["ingress_published"] == total_routed
    return {"status": "passed", "transport": "memory", "entire_video_played": True,
            "restart_does_not_duplicate": True, "observations": hub.snapshot()["accepted"],
            "routing": pipeline.status()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "video", "events", "tracking", "metadata"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--match-id", default="synthetic-live-001")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check-playback", action="store_true", help="Recorre todo el vídeo por colas en memoria, sin esperas ni servicios externos")
    args = parser.parse_args()
    started = perf_counter()
    replay = convert_messi_replay(args.match_id, json.loads(args.manifest.read_text()), {
        "match.mp4": args.video.read_bytes(), "events.jsonl": args.events.read_bytes(),
        "tracking.jsonl": args.tracking.read_bytes(), "metadata.jsonl": args.metadata.read_bytes(),
    })
    report = {
        "status": "validated_offline", "match_id": args.match_id,
        "media_sha256": replay.media_sha256, "source": "messi_simulator",
        "duration_ms": replay.duration_ms, "players": len(replay.metadata.players),
        "events": len(replay.events), "event_types": dict(Counter(event.type.value for event in replay.events)),
        "outcomes": dict(Counter(event.outcome.value for event in replay.events)),
        "tracking_frames": len(replay.tracking), "ignored_records": replay.ignored,
        "normalization_ms": round((perf_counter() - started) * 1000, 3),
        "examples": [event.model_dump(mode="json") for event in replay.events[:3]],
        "limitations": ["No ejecuta inferencia ni valida la precisión de los modelos.",
                        "Los eventos normalizados proceden del simulador.",
                        "Sin evaluar interfaz en navegador ni transportes Azure."],
    }
    if args.check_playback:
        report["playback_validation"] = asyncio.run(validate_playback(replay))
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded)
    print(encoded)


if __name__ == "__main__":
    main()
