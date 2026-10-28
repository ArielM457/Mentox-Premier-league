"""Valida GameState remoto y su adaptador de backend con un MP4 autorizado.

La clave se recibe solo mediante SOCCERNET_GAMESTATE_API_KEY. No administra
recursos Azure: quien lo invoque debe encender y apagar la réplica.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import time

from match_intelligence.application.gamestate_analysis import GameStateAnalysis, GameStateSettings
from match_intelligence.application.realtime_observations import RealtimeObservationHub
from match_intelligence.application.vision_runtime import VisionObservationRuntime, VisionRuntimeSettings
from match_intelligence.domain.contracts import MatchMetadata, Team


def save(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class FileVideoAnalysis(GameStateAnalysis):
    """Sustituye únicamente la descarga Blob para aislar la prueba del modelo."""

    async def _download_video(self) -> bytes:
        return self.input_path.read_bytes()


async def run(args) -> int:
    args.output.mkdir(parents=True, exist_ok=True)
    key = os.environ.get("SOCCERNET_GAMESTATE_API_KEY")
    if not key:
        raise ValueError("Exporte SOCCERNET_GAMESTATE_API_KEY antes de ejecutar")
    settings = GameStateSettings(
        endpoint=args.endpoint.rstrip("/"), api_key=key,
        blob_endpoint="https://validation.invalid", blob_container="local-input",
        blob_name=args.video.name, timeout_seconds=args.timeout,
    )
    hub = RealtimeObservationHub()
    publisher = VisionObservationRuntime(hub, VisionRuntimeSettings(transport="memory"))
    analysis = FileVideoAnalysis(publisher, settings)
    analysis.input_path = args.video
    metadata = MatchMetadata(
        schema_version="1.0", match_id="gamestate-validation",
        home_team=Team(team_id="unverified-home", name="Equipo sin verificar A"),
        away_team=Team(team_id="unverified-away", name="Equipo sin verificar B"),
        pitch_length_m=105, pitch_width_m=68, players=[],
    )
    summary = {
        "started_at": datetime.now(UTC).isoformat(), "endpoint": args.endpoint,
        "video_bytes": args.video.stat().st_size,
        "media_sha256": hashlib.sha256(args.video.read_bytes()).hexdigest(),
        "transport": "memory", "scope": "remote_model_and_backend_adapter",
        "identity_roster_verified": False,
    }
    started = time.monotonic()
    task = None
    server_log = ""
    last_analysis_id = None

    async def fetch_log() -> str:
        identifier = analysis.status().get("analysis_id") or last_analysis_id
        if not identifier:
            return ""
        try:
            async with asyncio.timeout(30):
                async with analysis._http().get(
                    f"{settings.endpoint}/v1/analyses/{identifier}/log",
                    headers=analysis._headers,
                ) as response:
                    if response.status == 200:
                        text = await response.text()
                        (args.output / "analysis.log").write_text(text, encoding="utf-8")
                        return text
        except Exception as error:
            print(f"Log no disponible: {type(error).__name__}", flush=True)
        return ""

    try:
        deadline = time.monotonic() + args.startup_timeout
        while True:
            try:
                ready = await analysis.readiness()
                if ready.get("status") != "ready":
                    raise RuntimeError(str(ready))
                save(args.output / "health.json", ready)
                print(json.dumps({"phase": "ready", **ready}), flush=True)
                break
            except Exception as error:
                if time.monotonic() >= deadline:
                    raise
                print(f"Arranque en curso: {error}", flush=True)
                await asyncio.sleep(5)
        task = asyncio.create_task(analysis.prepare(metadata.match_id, metadata))
        last_log_at = started
        while not task.done():
            await asyncio.wait({task}, timeout=15)
            state = analysis.status()
            last_analysis_id = state.get("analysis_id") or last_analysis_id
            save(args.output / "client-status.json", state)
            print(json.dumps({"elapsed_seconds": round(time.monotonic() - started, 1), **state}), flush=True)
            if time.monotonic() - last_log_at >= 45:
                server_log = await fetch_log() or server_log
                lines = server_log.replace("\r", "\n").splitlines()
                if lines:
                    print(f"Último log: {lines[-1][-350:]}", flush=True)
                last_log_at = time.monotonic()
        result = await task
        save(args.output / "prepare-result.json", result)
        rows = analysis._cached_rows or ()
        with (args.output / "gamestate-observations.jsonl").open("w", encoding="utf-8") as target:
            for row in rows:
                target.write(json.dumps(row, ensure_ascii=False) + "\n")
        with (args.output / "tracking.jsonl").open("w", encoding="utf-8") as target:
            for frame in analysis.tracking_frames:
                target.write(frame.model_dump_json() + "\n")
        save(args.output / "metrics.json", analysis.metrics)
        summary.update(
            status="succeeded", observations=len(rows), tracking_frames=len(analysis.tracking_frames),
            roles=dict(Counter(str(row.get("role")) for row in rows)),
            teams=dict(Counter(str(row.get("team")) for row in rows)),
            observations_with_jersey=sum(row.get("jersey_number") is not None for row in rows),
            observations_with_pitch=sum(row.get("bbox_pitch") is not None for row in rows),
            available_metrics=sum(metric["available"] for metric in analysis.metrics),
            video=analysis.status().get("video"), analysis_id=analysis.status().get("analysis_id"),
        )
        return 0
    except Exception as error:
        summary.update(status="failed", error_type=type(error).__name__, error=str(error),
                       client_status=analysis.status())
        print(f"Validación fallida: {error}", flush=True)
        return 1
    finally:
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        server_log = await fetch_log() or server_log
        identifier = analysis.status().get("analysis_id") or last_analysis_id
        if identifier:
            try:
                async with asyncio.timeout(30):
                    async with analysis._http().get(
                        f"{settings.endpoint}/v1/analyses/{identifier}",
                        headers=analysis._headers,
                    ) as response:
                        if response.status == 200:
                            save(args.output / "server-status.json", await response.json())
            except Exception as error:
                print(f"Estado final no disponible: {type(error).__name__}", flush=True)
        summary.update(
            analysis_id=identifier,
            elapsed_seconds=round(time.monotonic() - started, 3),
            finished_at=datetime.now(UTC).isoformat(),
            download_log_lines=[
                line[-1000:] for line in server_log.replace("\r", "\n").splitlines()
                if "download" in line.lower() or "installing" in line.lower()
            ],
        )
        save(args.output / "summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False), flush=True)
        await analysis.close()
        await publisher.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=3600)
    parser.add_argument("--startup-timeout", type=float, default=600)
    raise SystemExit(asyncio.run(run(parser.parse_args())))
