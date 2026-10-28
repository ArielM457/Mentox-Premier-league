#!/usr/bin/env bash
set -euo pipefail

: "${MENTOX_GAMESTATE_VIDEO_PATH:?Falta MENTOX_GAMESTATE_VIDEO_PATH}"
: "${MENTOX_GAMESTATE_OUTPUT_DIR:?Falta MENTOX_GAMESTATE_OUTPUT_DIR}"

frame_limit="${MENTOX_GAMESTATE_FRAME_LIMIT:-0}"
low_vram_profile="${MENTOX_GAMESTATE_LOW_VRAM:-0}"
save_visualization="${MENTOX_GAMESTATE_SAVE_VISUALIZATION:-false}"

[[ -f "${MENTOX_GAMESTATE_VIDEO_PATH}" ]] || {
  echo "No existe el MP4: ${MENTOX_GAMESTATE_VIDEO_PATH}" >&2
  exit 1
}

mkdir -p "${MENTOX_GAMESTATE_OUTPUT_DIR}" \
  "${XDG_CACHE_HOME}" "${HF_HOME}" "${TORCH_HOME}" "${MPLCONFIGDIR}"

python - <<'PY'
import json
import torch

if not torch.cuda.is_available():
    raise RuntimeError("Azure no expuso una GPU CUDA al contenedor")
torch.cuda.set_device(0)
properties = torch.cuda.get_device_properties(0)
print(json.dumps({
    "cuda_available": True,
    "cuda_version": torch.version.cuda,
    "gpu_name": torch.cuda.get_device_name(0),
    "gpu_memory_bytes": properties.total_memory,
    "torch_version": torch.__version__,
}))
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

frame_arguments=()
if [[ "${frame_limit}" =~ ^[1-9][0-9]*$ ]]; then
  frame_arguments=("dataset.nframes=${frame_limit}")
fi

tracklab -cn soccernet \
  "home_dir=/home/prime" \
  "data_dir=/work/dataset" \
  "model_dir=/models" \
  "dataset=video" \
  "dataset.video_path=${MENTOX_GAMESTATE_VIDEO_PATH}" \
  "dataset.eval_set=val" \
  "dataset.nvid=1" \
  "eval=trackeval" \
  "test_tracking=true" \
  "eval_tracking=false" \
  "use_wandb=false" \
  "state.save_file=${MENTOX_GAMESTATE_OUTPUT_DIR}/sn-gamestate.pklz" \
  "visualization.save_videos=${save_visualization}" \
  "hydra.run.dir=${MENTOX_GAMESTATE_OUTPUT_DIR}/run" \
  "${frame_arguments[@]}" \
  "${machine_arguments[@]}"

python /opt/prime/export_tracker_state.py \
  --state "${MENTOX_GAMESTATE_OUTPUT_DIR}/sn-gamestate.pklz" \
  --output "${MENTOX_GAMESTATE_OUTPUT_DIR}/gamestate-observations.jsonl"

