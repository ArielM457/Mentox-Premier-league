"""Verifica los argumentos reales del ejecutor sin cargar modelos ni CUDA."""

import os
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parent


@pytest.mark.parametrize("save_visualization", ["false", "true"])
def test_runner_sets_tracklab_visualization_at_constructor_level(tmp_path, save_visualization):
    binaries = tmp_path / "bin"
    binaries.mkdir()
    python = binaries / "python"
    python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    python.chmod(0o755)
    tracklab = binaries / "tracklab"
    tracklab.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n', encoding="utf-8")
    tracklab.chmod(0o755)
    video = tmp_path / "input.mp4"
    video.write_bytes(b"stub-video")
    environment = {
        **os.environ,
        "PATH": str(binaries) + os.pathsep + os.environ["PATH"],
        "MENTOX_GAMESTATE_VIDEO_PATH": str(video),
        "MENTOX_GAMESTATE_OUTPUT_DIR": str(tmp_path / "output"),
        "MENTOX_GAMESTATE_SAVE_VISUALIZATION": save_visualization,
        "MENTOX_GAMESTATE_FRAME_LIMIT": "0",
        "MENTOX_GAMESTATE_LOW_VRAM": "0",
    }
    for variable in ("XDG_CACHE_HOME", "HF_HOME", "TORCH_HOME", "MPLCONFIGDIR"):
        environment[variable] = str(tmp_path / variable.lower())
    result = subprocess.run(
        ["bash", str(ROOT / "run_analysis.sh")],
        env=environment, capture_output=True, text=True, check=True, timeout=10,
    )
    arguments = result.stdout.splitlines()
    assert "visualization.save_videos=" + save_visualization in arguments
    assert not any(argument.startswith("visualization.cfg.save_videos=") for argument in arguments)
    assert "test_tracking=true" in arguments
    assert "eval_tracking=false" in arguments
