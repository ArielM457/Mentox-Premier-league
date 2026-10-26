#!/usr/bin/env bash
set -euo pipefail

gpu_index="${MENTOX_CUDA_DEVICE:-0}"
frame_limit="${MENTOX_GAMESTATE_FRAME_LIMIT:-250}"
low_vram_profile="${MENTOX_GAMESTATE_LOW_VRAM:-0}"
video_path="${MENTOX_GAMESTATE_VIDEO_PATH:-}"

mkdir -p /tmp/mentox-home /data /models /output \
  "${XDG_CACHE_HOME}" "${HF_HOME}" "${TORCH_HOME}" "${MPLCONFIGDIR}"

python - <<'PY'
import json
import os
import torch

index = int(os.environ.get("MENTOX_CUDA_DEVICE", "0"))
if not torch.cuda.is_available():
    raise RuntimeError(
        "PyTorch no detecta CUDA dentro del contenedor. "
        "Verifique NVIDIA Container Toolkit y --gpus all."
    )
if index >= torch.cuda.device_count():
    raise RuntimeError(
        f"GPU solicitada {index}; disponibles: {torch.cuda.device_count()}"
    )
torch.cuda.set_device(index)
properties = torch.cuda.get_device_properties(index)
print(json.dumps({
    "cuda_available": True,
    "cuda_version": torch.version.cuda,
    "gpu_index": index,
    "gpu_name": torch.cuda.get_device_name(index),
    "gpu_memory_bytes": properties.total_memory,
    "torch_version": torch.__version__,
}, indent=2))
PY

machine_arguments=()
if [[ "${low_vram_profile}" == "1" ]]; then
  machine_arguments=(
    "modules.bbox_detector.batch_size=1"
    "modules.pose_bottomup.batch_size=1"
    "modules.reid.batch_size=8"
    "modules.track.batch_size=8"
    "modules.pitch.batch_size=1"
    "modules.calibration.batch_size=1"
    "modules.jersey_number_detect.batch_size=1"
  )
fi

dataset_arguments=()
if [[ -n "${video_path}" ]]; then
  [[ -f "${video_path}" ]] || {
    echo "El vídeo solicitado no existe dentro del contenedor: ${video_path}" >&2
    exit 1
  }
  dataset_arguments=(
    "dataset=video"
    "dataset.video_path=${video_path}"
    "dataset.eval_set=val"
    "dataset.nvid=1"
    "dataset.nframes=${frame_limit}"
    "eval=trackeval"
  )
  echo "Modo MP4 externo: ${video_path}"
else
  dataset_arguments=(
    "dataset.nvid=1"
    "dataset.nframes=${frame_limit}"
  )
  echo "Modo dataset oficial SoccerNet GSR."
fi

tracklab -cn soccernet \
  "home_dir=/tmp/mentox-home" \
  "data_dir=/data" \
  "model_dir=/models" \
  "test_tracking=true" \
  "eval_tracking=false" \
  "use_wandb=false" \
  "state.save_file=/output/sn-gamestate.pklz" \
  "visualization.cfg.save_videos=true" \
  "hydra.run.dir=/output/run" \
  "${dataset_arguments[@]}" \
  "${machine_arguments[@]}"

python /opt/mentox/export_tracker_state.py \
  --state /output/sn-gamestate.pklz \
  --output /output/gamestate-observations.jsonl
