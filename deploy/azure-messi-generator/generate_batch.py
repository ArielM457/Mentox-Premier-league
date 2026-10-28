#!/usr/bin/env python3
"""Generate deterministic MESSI replays and upload them to Azure Blob Storage."""

from __future__ import annotations

import hashlib
import json
import math
import mimetypes
import os
import shutil
import subprocess
import sys
import time
from importlib.metadata import PackageNotFoundError, version
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.storage.blob import BlobServiceClient, ContentSettings


MESSI_COMMIT = "b04b15c59d36c1e4f44e02d0886b2d0d7261f689"
STYLES = ("balanced", "tiki_taka", "long_ball")


def _positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} debe ser un entero, no {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"{name} debe ser mayor que cero")
    return value


def _positive_float(name: str, default: float) -> float:
    raw = os.environ.get(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} debe ser numérico, no {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"{name} debe ser mayor que cero")
    return value


def _boolean(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "1" if default else "0").strip().lower()
    if raw in {"1", "true", "yes", "si", "sí"}:
        return True
    if raw in {"0", "false", "no"}:
        return False
    raise ValueError(f"{name} debe ser 0 o 1")


@dataclass(frozen=True)
class Settings:
    count: int
    base_seed: int
    seconds: float
    control_fps: float
    render_fps: float
    render_mode: str
    state_stride: int
    batch_id: str
    output_root: Path
    upload_enabled: bool
    overwrite: bool
    blob_endpoint: str | None
    container: str
    prefix: str

    @classmethod
    def from_environment(cls) -> "Settings":
        count = _positive_int("MENTOX_MATCH_COUNT", 30)
        base_seed = _positive_int("MENTOX_BASE_SEED", 20261025)
        seconds = _positive_float("MENTOX_MATCH_SECONDS", 180.0)
        control_fps = _positive_float("MENTOX_CONTROL_FPS", 15.0)
        render_fps = _positive_float("MENTOX_RENDER_FPS", 15.0)
        state_stride = _positive_int("MENTOX_STATE_STRIDE", 15)
        if not math.isclose(render_fps, control_fps, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(
                "MENTOX_RENDER_FPS debe coincidir con MENTOX_CONTROL_FPS en el Job GPU; "
                "usar valores distintos activa la captura completa de subpasos de MESSI"
            )
        render_mode = os.environ.get("MENTOX_RENDER_MODE", "light")
        if render_mode not in {"light", "rich", "clean"}:
            raise ValueError("MENTOX_RENDER_MODE debe ser light, rich o clean")
        batch_id = os.environ.get(
            "MENTOX_BATCH_ID",
            f"messi-{base_seed}-{count}x{seconds:g}s",
        )
        if not batch_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in batch_id):
            raise ValueError("MENTOX_BATCH_ID solo admite letras, números, guion y guion bajo")
        endpoint = os.environ.get("AZURE_BLOB_SERVICE_ENDPOINT")
        upload_enabled = _boolean("MENTOX_UPLOAD_ENABLED", True)
        if upload_enabled and not endpoint:
            raise ValueError(
                "AZURE_BLOB_SERVICE_ENDPOINT es obligatorio cuando MENTOX_UPLOAD_ENABLED=1"
            )
        return cls(
            count=count,
            base_seed=base_seed,
            seconds=seconds,
            control_fps=control_fps,
            render_fps=render_fps,
            render_mode=render_mode,
            state_stride=state_stride,
            batch_id=batch_id,
            output_root=Path(os.environ.get("MENTOX_OUTPUT_DIR", "/work/output")),
            upload_enabled=upload_enabled,
            overwrite=_boolean("MENTOX_OVERWRITE", False),
            blob_endpoint=endpoint,
            container=os.environ.get("MENTOX_BLOB_CONTAINER", "synthetic-videos"),
            prefix=os.environ.get("MENTOX_BLOB_PREFIX", "messi"),
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _styles(index: int) -> tuple[str, str]:
    home = STYLES[index % len(STYLES)]
    away = STYLES[(index // len(STYLES) + index + 1) % len(STYLES)]
    if home == away:
        away = STYLES[(STYLES.index(away) + 1) % len(STYLES)]
    return home, away


def _content_settings(path: Path) -> ContentSettings:
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return ContentSettings(
        content_type=content_type,
        content_disposition="inline" if path.suffix == ".mp4" else None,
        cache_control="public, max-age=3600" if path.suffix == ".mp4" else "no-cache",
    )


class Storage:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.container = None
        if settings.upload_enabled:
            managed_identity_client_id = os.environ.get("AZURE_CLIENT_ID")
            if managed_identity_client_id:
                credential = ManagedIdentityCredential(client_id=managed_identity_client_id)
            else:
                credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
            service = BlobServiceClient(settings.blob_endpoint, credential=credential)
            self.container = service.get_container_client(settings.container)

    def completed(self, match_id: str) -> bool:
        if self.container is None or self.settings.overwrite:
            return False
        blob = self.container.get_blob_client(self._name(match_id, "manifest.json"))
        try:
            properties = blob.get_blob_properties()
        except ResourceNotFoundError:
            return False
        return properties.metadata.get("status") == "complete"

    def upload(self, match_id: str, path: Path, *, metadata: dict[str, str]) -> str | None:
        if self.container is None:
            return None
        blob_name = self._name(match_id, path.name)
        with path.open("rb") as stream:
            self.container.upload_blob(
                name=blob_name,
                data=stream,
                # Si una ejecución anterior dejó un lote parcial, los nombres
                # deterministas se reemplazan antes de publicar el manifiesto.
                overwrite=True,
                content_settings=_content_settings(path),
                metadata=metadata,
                max_concurrency=4,
            )
        return blob_name

    def _name(self, match_id: str, filename: str) -> str:
        return f"{self.settings.prefix}/{self.settings.batch_id}/{match_id}/{filename}"


def _run_match(settings: Settings, index: int, match_dir: Path) -> dict[str, object]:
    match_id = f"messi-{index + 1:03d}"
    seed = settings.base_seed + index
    home, away = _styles(index)
    video = match_dir / "match.mp4"
    command = [
        "soccerworld-demo",
        "--home",
        home,
        "--away",
        away,
        "--seconds",
        str(settings.seconds),
        "--seed",
        str(seed),
        "--control-fps",
        str(settings.control_fps),
        "--render-fps",
        str(settings.render_fps),
        "--compressed-match",
        "--mode",
        "rich" if settings.render_mode == "clean" else settings.render_mode,
        "--state-stride",
        str(settings.state_stride),
        "--out",
        str(video),
    ]
    if settings.render_mode == "clean":
        command.append("--clean-hud")
    started = time.perf_counter()
    completed = subprocess.run(command, check=False, text=True)
    duration = time.perf_counter() - started
    if completed.returncode != 0:
        raise RuntimeError(f"MESSI terminó con código {completed.returncode} para {match_id}")

    expected = (video, match_dir / "events.jsonl", match_dir / "tracking.jsonl", match_dir / "metadata.jsonl")
    missing = [str(path) for path in expected if not path.is_file()]
    if missing:
        raise RuntimeError(f"MESSI no produjo los artefactos esperados: {missing}")

    return {
        "schema_version": "the-prime-moment.messi-match.v1",
        "match_id": match_id,
        "batch_id": settings.batch_id,
        "seed": seed,
        "home_style": home,
        "away_style": away,
        "compressed_match": True,
        "video_duration_seconds": settings.seconds,
        "control_fps": settings.control_fps,
        "render_fps": settings.render_fps,
        "state_stride": settings.state_stride,
        "render_mode": settings.render_mode,
        "messi_commit": MESSI_COMMIT,
        "generation_duration_seconds": round(duration, 3),
        "generated_at": datetime.now(UTC).isoformat(),
        "source": "synthetic",
        "artifacts": [
            {
                "name": path.name,
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in expected
        ],
    }


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _require_gpu() -> list[dict[str, object]]:
    import jax

    devices = [
        {
            "id": int(device.id),
            "platform": device.platform,
            "kind": getattr(device, "device_kind", "unknown"),
        }
        for device in jax.devices()
    ]
    if not devices or any(device["platform"] not in {"gpu", "cuda"} for device in devices):
        raise RuntimeError(f"El Job requiere GPU CUDA; JAX informó {devices}")
    print(json.dumps({"jax_devices": devices}), flush=True)
    return devices


def _runtime_diagnostics() -> None:
    packages: dict[str, str] = {}
    for package in (
        "jax",
        "jaxlib",
        "jax-cuda12-plugin",
        "jax-cuda12-pjrt",
        "nvidia-cuda-runtime-cu12",
        "nvidia-cudnn-cu12",
    ):
        try:
            packages[package] = version(package)
        except PackageNotFoundError:
            packages[package] = "not-installed"
    print(
        json.dumps(
            {
                "runtime": {
                    "python": sys.version.split()[0],
                    "packages": packages,
                    "ld_library_path": os.environ.get("LD_LIBRARY_PATH"),
                }
            }
        ),
        flush=True,
    )


def main() -> int:
    settings = Settings.from_environment()
    settings.output_root.mkdir(parents=True, exist_ok=True)
    _runtime_diagnostics()
    devices = _require_gpu()
    storage = Storage(settings)
    print(
        json.dumps(
            {
                "configuration": asdict(settings)
                | {"output_root": str(settings.output_root)}
            },
            default=str,
        )
    )

    results: list[dict[str, object]] = []
    for index in range(settings.count):
        match_id = f"messi-{index + 1:03d}"
        if storage.completed(match_id):
            print(f"[{index + 1}/{settings.count}] {match_id} ya está completo; se omite")
            results.append({"match_id": match_id, "status": "skipped_existing"})
            continue

        match_dir = settings.output_root / match_id
        if match_dir.exists():
            shutil.rmtree(match_dir)
        match_dir.mkdir(parents=True)
        print(f"[{index + 1}/{settings.count}] generando {match_id}", flush=True)
        manifest = _run_match(settings, index, match_dir)
        manifest_path = match_dir / "manifest.json"
        _write_json(manifest_path, manifest)

        metadata = {
            "status": "complete",
            "match_id": match_id,
            "batch_id": settings.batch_id,
            "provenance": "synthetic",
            "generator": "messi",
        }
        artifact_paths = sorted(path for path in match_dir.iterdir() if path != manifest_path)
        expected_blob_names = [
            storage._name(match_id, path.name) for path in artifact_paths
        ] + [storage._name(match_id, manifest_path.name)]
        manifest["uploaded_blobs"] = expected_blob_names if storage.container is not None else []
        _write_json(manifest_path, manifest)

        uploaded: list[str] = []
        # Publicar el manifiesto al final evita marcar como completo un lote
        # cuyos archivos anteriores no terminaron de subir.
        for path in [*artifact_paths, manifest_path]:
            blob_name = storage.upload(match_id, path, metadata=metadata)
            if blob_name:
                uploaded.append(blob_name)
        if uploaded != manifest["uploaded_blobs"]:
            raise RuntimeError(f"La lista de blobs de {match_id} quedó incompleta")
        results.append(manifest)
        print(f"[{index + 1}/{settings.count}] {match_id} completo", flush=True)
        shutil.rmtree(match_dir)

    batch_manifest = {
        "schema_version": "the-prime-moment.messi-batch.v1",
        "batch_id": settings.batch_id,
        "requested_matches": settings.count,
        "completed_or_existing": len(results),
        "created_at": datetime.now(UTC).isoformat(),
        "messi_commit": MESSI_COMMIT,
        "jax_devices": devices,
        "results": results,
    }
    batch_path = settings.output_root / "batch-manifest.json"
    _write_json(batch_path, batch_manifest)
    if storage.container is not None:
        blob_name = f"{settings.prefix}/{settings.batch_id}/batch-manifest.json"
        with batch_path.open("rb") as stream:
            storage.container.upload_blob(
                blob_name,
                stream,
                overwrite=True,
                content_settings=ContentSettings(content_type="application/json", cache_control="no-cache"),
                metadata={"status": "complete", "batch_id": settings.batch_id, "provenance": "synthetic"},
            )
    print(json.dumps({"status": "complete", "batch_id": settings.batch_id, "matches": len(results)}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__, "error": str(exc)}), file=sys.stderr)
        raise
