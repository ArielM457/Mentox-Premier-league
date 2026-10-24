#!/usr/bin/env bash
set -euo pipefail

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "No se encontró nvidia-smi. Use run-cpu.sh o instale el controlador NVIDIA." >&2
  exit 1
fi

if ! sudo docker info 2>/dev/null | grep -q 'nvidia'; then
  echo "Aviso: Docker no anuncia el runtime NVIDIA; se comprobará con --gpus all." >&2
fi

echo "GPU anfitriona:"
nvidia-smi --query-gpu=index,name,driver_version,memory.total --format=csv,noheader

gpu_index="${MENTOX_CUDA_DEVICE:-0}"
gpu_memory_mib="$(nvidia-smi --id="${gpu_index}" --query-gpu=memory.total --format=csv,noheader,nounits | head -n 1 | tr -d ' ')"
if [[ ! "${gpu_memory_mib}" =~ ^[0-9]+$ ]]; then
  echo "No se pudo determinar la VRAM de la GPU ${gpu_index}." >&2
  exit 1
fi

# Las variables definidas manualmente siempre tienen prioridad.
if (( gpu_memory_mib <= 8192 )); then
  export MENTOX_PLAYER_IMAGE_SIZE="${MENTOX_PLAYER_IMAGE_SIZE:-640}"
  export MENTOX_BALL_IMAGE_SIZE="${MENTOX_BALL_IMAGE_SIZE:-640}"
  export MENTOX_PITCH_IMAGE_SIZE="${MENTOX_PITCH_IMAGE_SIZE:-640}"
  export MENTOX_PITCH_STRIDE="${MENTOX_PITCH_STRIDE:-10}"
  export MENTOX_CUDA_HALF="${MENTOX_CUDA_HALF:-1}"
  echo "Perfil automático de VRAM baja: 640 px, campo cada 10 cuadros y FP16."
else
  echo "Perfil automático estándar: resolución y frecuencia completas."
fi

experiment_directory="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${experiment_directory}/run_variant.sh" cuda
