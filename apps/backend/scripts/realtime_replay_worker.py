"""Reproduce exportaciones como un worker continuo para validar el canal en vivo."""

import argparse
import asyncio
import json
from pathlib import Path
from time import monotonic

import aiohttp


def load_items(roboflow: Path, soccernet: Path) -> list[dict[str, object]]:
    roboflow_document = json.loads(roboflow.read_text(encoding="utf-8"))
    spatial = roboflow_document["predictions"] + roboflow_document.get(
        "pitch_observations", []
    )
    actions = json.loads(soccernet.read_text(encoding="utf-8"))["predictions"]
    items = [
        {
            "observation_id": item["prediction_id"],
            "source": f"roboflow-{item.get('model_role', 'player')}",
            "kind": "spatial_detection",
            "timestamp_ms": item["timestamp_ms"],
            "payload": item,
        }
        for item in spatial
    ] + [
        {
            "observation_id": item["prediction_id"],
            "source": "soccernet",
            "kind": "temporal_action",
            "timestamp_ms": item["timestamp_ms"],
            "payload": item,
        }
        for item in actions
    ]
    return sorted(items, key=lambda item: int(item["timestamp_ms"]))


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roboflow", required=True, type=Path)
    parser.add_argument("--soccernet", required=True, type=Path)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8018/api/v1/integration/live/observations")
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args()
    if args.speed <= 0:
        raise ValueError("speed debe ser mayor que cero")
    items = load_items(args.roboflow, args.soccernet)
    started = monotonic()
    async with aiohttp.ClientSession() as session:
        for item in items:
            target = int(item["timestamp_ms"]) / 1_000 / args.speed
            await asyncio.sleep(max(0, target - (monotonic() - started)))
            async with session.post(args.endpoint, json=item) as response:
                response.raise_for_status()
    print(json.dumps({"published": len(items), "speed": args.speed}))


if __name__ == "__main__":
    asyncio.run(main())
