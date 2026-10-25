"""Genera un clip sintético de GRF y un manifiesto reproducible para DV-US-17."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from gfootball.env import config, football_env


OUTPUT_DIRECTORY = Path("/output")
SCENARIO = "11_vs_11_stochastic"
MAX_STEPS = 300
GRF_COMMIT = "3d9e754720a95621bba6475c4d3b0d56fe919014"
OUTPUT_VIDEO = OUTPUT_DIRECTORY / "grf-dv-us-17.mp4"
OUTPUT_MANIFEST = OUTPUT_DIRECTORY / "grf-dv-us-17.manifest.json"


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def newest_avi() -> Path:
    candidates = sorted(
        OUTPUT_DIRECTORY.rglob("*.avi"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise RuntimeError("GRF no produjo ningún archivo AVI")
    return candidates[0]


def convert_to_mp4(source: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(OUTPUT_VIDEO),
        ],
        check=True,
    )


def probe_video() -> dict[str, object]:
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,avg_frame_rate:format=duration",
            "-of",
            "json",
            str(OUTPUT_VIDEO),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def generate_episode() -> int:
    values = {
        "action_set": "full",
        "dump_full_episodes": True,
        "level": SCENARIO,
        "players": ["bot:left_players=1", "bot:right_players=1"],
        "real_time": False,
        "tracesdir": str(OUTPUT_DIRECTORY),
        "write_video": True,
    }
    environment = football_env.FootballEnv(config.Config(values))
    environment.reset()
    steps = 0
    done = False
    try:
        while not done and steps < MAX_STEPS:
            _, _, done, _ = environment.step([])
            steps += 1
        if not done:
            environment.write_dump("dv_us_17_step_limit")
    finally:
        environment.close()
    return steps


def main() -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    steps = generate_episode()
    source_video = newest_avi()
    convert_to_mp4(source_video)
    probe = probe_video()
    manifest = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "Google Research Football",
        "generator_commit": GRF_COMMIT,
        "generator_license": "Apache-2.0",
        "source_repository": "https://github.com/google-research/football",
        "scenario": SCENARIO,
        "players": ["bot:left_players=1", "bot:right_players=1"],
        "synthetic": True,
        "redistribution_decision": "local_and_private_blob",
        "steps": steps,
        "step_limit": MAX_STEPS,
        "video": {
            "filename": OUTPUT_VIDEO.name,
            "bytes": OUTPUT_VIDEO.stat().st_size,
            "sha256": sha256_file(OUTPUT_VIDEO),
            "probe": probe,
        },
        "limitations": [
            "El repositorio oficial fue archivado en 2026.",
            "El clip es una simulación y no una transmisión real.",
            "La licencia del código no representa marcas ni ligas reales.",
        ],
    }
    OUTPUT_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
