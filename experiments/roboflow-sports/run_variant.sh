#!/usr/bin/env bash
set -euo pipefail

variant="${1:-}"
if [[ "${variant}" != "cpu" && "${variant}" != "cuda" ]]; then
  echo "Uso: $0 cpu|cuda" >&2
  exit 2
fi

experiment_directory="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(cd "${experiment_directory}/../.." && pwd)"
output_directory="${MENTOX_OUTPUT_DIRECTORY:-${experiment_directory}/output}"
input_video="${MENTOX_INPUT_VIDEO:-${repository_root}/experiments/google-research-football/output/grf-dv-us-17.mp4}"
input_annotations="${MENTOX_INPUT_ANNOTATIONS:-${repository_root}/experiments/google-research-football/annotations/grf-dv-us-17.csv}"
media_id="${MENTOX_MEDIA_ID:-grf-dv-us-17}"
permission_basis="${MENTOX_PERMISSION_BASIS:-project_generated}"
permission_reference="${MENTOX_PERMISSION_REFERENCE:-docs/persona-1-datos-y-vision/evidencias/DV-US-17.md}"

if [[ ! -f "${input_video}" ]]; then
  echo "Falta el vídeo de entrada: ${input_video}" >&2
  exit 1
fi
if [[ ! -f "${input_annotations}" ]]; then
  echo "Faltan las anotaciones de entrada: ${input_annotations}" >&2
  exit 1
fi

if [[ "${variant}" == "cuda" ]]; then
  torch_index_url="${MENTOX_CUDA_INDEX_URL:-https://download.pytorch.org/whl/cu130}"
  image_name="mentox/roboflow-sports:42c80c0-cuda"
  gpu_arguments=(--gpus all)
else
  torch_index_url="https://download.pytorch.org/whl/cpu"
  image_name="mentox/roboflow-sports:42c80c0-cpu"
  gpu_arguments=()
fi

mkdir -p "${output_directory}"

sudo docker build \
  --build-arg SPORTS_COMMIT=42c80c06b6b65a7f89455b89fe31cdf4c38ba227 \
  --build-arg TORCH_INDEX_URL="${torch_index_url}" \
  --tag "${image_name}" \
  "${experiment_directory}"

sudo docker run --rm \
  "${gpu_arguments[@]}" \
  --user "$(id -u):$(id -g)" \
  --env MENTOX_VISION_DEVICE="${variant}" \
  --env MENTOX_VIDEO_PATH=/input/video.mp4 \
  --env MENTOX_ANNOTATIONS_PATH=/input/annotations.csv \
  --env MENTOX_MEDIA_ID="${media_id}" \
  --env MENTOX_PERMISSION_BASIS="${permission_basis}" \
  --env MENTOX_PERMISSION_REFERENCE="${permission_reference}" \
  --env MENTOX_LIVE_ENDPOINT="${MENTOX_LIVE_ENDPOINT:-}" \
  --env MENTOX_VISION_MODELS="${MENTOX_VISION_MODELS:-all}" \
  --env MENTOX_PLAYER_IMAGE_SIZE="${MENTOX_PLAYER_IMAGE_SIZE:-1280}" \
  --env MENTOX_BALL_IMAGE_SIZE="${MENTOX_BALL_IMAGE_SIZE:-1280}" \
  --env MENTOX_PITCH_IMAGE_SIZE="${MENTOX_PITCH_IMAGE_SIZE:-1280}" \
  --env MENTOX_PITCH_STRIDE="${MENTOX_PITCH_STRIDE:-5}" \
  --env MENTOX_CUDA_DEVICE="${MENTOX_CUDA_DEVICE:-0}" \
  --env MENTOX_CUDA_HALF="${MENTOX_CUDA_HALF:-1}" \
  --volume "${input_video}:/input/video.mp4:ro" \
  --volume "${input_annotations}:/input/annotations.csv:ro" \
  --volume "${output_directory}:/output" \
  "${image_name}"

if [[ "${MENTOX_SKIP_EVALUATION:-0}" != "1" ]]; then
  UV_CACHE_DIR=/tmp/mentox-uv-cache \
  uv run --project "${repository_root}/apps/backend" --python 3.12 \
    python "${repository_root}/apps/backend/scripts/evaluate_vision_predictions.py" \
    "${output_directory}/roboflow-sports-evaluation-input.json" \
    --output "${output_directory}/roboflow-sports-evaluation-report.json"
else
  echo "Evaluación omitida: faltan anotaciones manuales del vídeo real."
fi

echo "Dispositivo: ${variant}"
echo "Predicciones: ${output_directory}/roboflow-sports-predictions.json"
if [[ "${MENTOX_SKIP_EVALUATION:-0}" != "1" ]]; then
  echo "Informe: ${output_directory}/roboflow-sports-evaluation-report.json"
fi
echo "Vídeo anotado: ${output_directory}/roboflow-sports-annotated.mp4"
