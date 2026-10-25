#!/usr/bin/env bash
set -euo pipefail

experiment_directory="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
  echo "GPU NVIDIA detectada; se usará CUDA."
  exec bash "${experiment_directory}/run-gpu.sh"
fi

echo "GPU NVIDIA no detectada; se usará CPU."
exec bash "${experiment_directory}/run-cpu.sh"
