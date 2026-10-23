#!/usr/bin/env bash
set -euo pipefail

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "No se encontró nvidia-smi. Instale el controlador NVIDIA o use run-cpu.sh." >&2
  exit 1
fi
if ! nvidia-smi >/dev/null 2>&1; then
  echo "nvidia-smi existe, pero no puede comunicarse con el controlador NVIDIA." >&2
  exit 1
fi

echo "GPU anfitriona:"
nvidia-smi --query-gpu=index,name,driver_version,memory.total --format=csv,noheader

gpu_index="${MENTOX_CUDA_DEVICE:-0}"
gpu_memory_mib="$(nvidia-smi --id="${gpu_index}" --query-gpu=memory.total --format=csv,noheader,nounits | head -n 1 | tr -d ' ')"
if [[ ! "${gpu_memory_mib}" =~ ^[0-9]+$ ]]; then
  echo "No se pudo determinar la VRAM de la GPU ${gpu_index}." >&2
  exit 1
fi

export MENTOX_CUDA_AMP="${MENTOX_CUDA_AMP:-1}"
if (( gpu_memory_mib <= 8192 )); then
  echo "Perfil automático de VRAM baja: precisión mixta (AMP) activada."
else
  echo "Perfil automático estándar: precisión mixta (AMP) activada."
fi

experiment_directory="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${experiment_directory}/run_variant.sh" cuda
