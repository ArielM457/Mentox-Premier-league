#!/usr/bin/env bash
set -euo pipefail

experiment_directory="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
data_directory="${MENTOX_GAMESTATE_DATA_DIRECTORY:-${experiment_directory}/data}"
models_directory="${MENTOX_GAMESTATE_MODELS_DIRECTORY:-${experiment_directory}/models}"
output_directory="${MENTOX_GAMESTATE_OUTPUT_DIRECTORY:-${experiment_directory}/output}"
gpu_index="${MENTOX_CUDA_DEVICE:-0}"

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "No se encontró nvidia-smi. sn-gamestate requiere una GPU NVIDIA." >&2
  exit 1
fi
if ! nvidia-smi >/dev/null 2>&1; then
  echo "nvidia-smi no puede comunicarse con el controlador NVIDIA." >&2
  exit 1
fi

echo "GPU anfitriona:"
nvidia-smi --query-gpu=index,name,driver_version,memory.total --format=csv,noheader

gpu_memory_mib="$(nvidia-smi --id="${gpu_index}" --query-gpu=memory.total --format=csv,noheader,nounits | head -n 1 | tr -d ' ')"
if [[ ! "${gpu_memory_mib}" =~ ^[0-9]+$ ]]; then
  echo "No se pudo determinar la VRAM de la GPU ${gpu_index}." >&2
  exit 1
fi

if (( gpu_memory_mib <= 8192 )); then
  frame_limit="${MENTOX_GAMESTATE_FRAME_LIMIT:-100}"
  low_vram_profile="1"
  echo "Perfil experimental de 6-8 GB: smoke limitado a ${frame_limit} cuadros."
  echo "También se reducirán los lotes de detección, ReID, tracking y dorsal."
else
  frame_limit="${MENTOX_GAMESTATE_FRAME_LIMIT:-250}"
  low_vram_profile="0"
  echo "Perfil GameState estándar: smoke limitado a ${frame_limit} cuadros."
fi
mkdir -p "${data_directory}" "${models_directory}" "${output_directory}"

sudo docker build \
  --build-arg GAMESTATE_COMMIT=1c958345067218297d221e45e1a6405f975f83e0 \
  --tag mentox/soccernet-gamestate:1c95834-cuda117 \
  "${experiment_directory}"

sudo docker run --rm \
  --gpus all \
  --user "$(id -u):$(id -g)" \
  --env MENTOX_CUDA_DEVICE="${gpu_index}" \
  --env MENTOX_GAMESTATE_FRAME_LIMIT="${frame_limit}" \
  --env MENTOX_GAMESTATE_LOW_VRAM="${low_vram_profile}" \
  --volume "${data_directory}:/data" \
  --volume "${models_directory}:/models" \
  --volume "${output_directory}:/output" \
  mentox/soccernet-gamestate:1c95834-cuda117

echo "Estado de tracking: ${output_directory}/sn-gamestate.pklz"
echo "Resultados y vídeo: ${output_directory}/run"
