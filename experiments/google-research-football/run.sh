#!/usr/bin/env bash
set -euo pipefail

experiment_directory="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
output_directory="${experiment_directory}/output"
image_name="mentox/google-research-football:3d9e754"

mkdir -p "${output_directory}"

sudo docker build \
  --build-arg GRF_COMMIT=3d9e754720a95621bba6475c4d3b0d56fe919014 \
  --tag "${image_name}" \
  "${experiment_directory}"

sudo docker run --rm \
  --user "$(id -u):$(id -g)" \
  --volume "${output_directory}:/output" \
  "${image_name}"

echo "Video: ${output_directory}/grf-dv-us-17.mp4"
echo "Manifiesto: ${output_directory}/grf-dv-us-17.manifest.json"
