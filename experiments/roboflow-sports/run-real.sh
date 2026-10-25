#!/usr/bin/env bash
set -euo pipefail

experiment_directory="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(cd "${experiment_directory}/../.." && pwd)"

export MENTOX_INPUT_VIDEO="${MENTOX_INPUT_VIDEO:-${repository_root}/experiments/authorized-video/input/2e57b9_0.mp4}"
export MENTOX_INPUT_ANNOTATIONS="${MENTOX_ROBOFLOW_ANNOTATIONS:-${MENTOX_INPUT_ANNOTATIONS:-${repository_root}/experiments/authorized-video/annotations/roboflow-spatial.csv}}"
export MENTOX_OUTPUT_DIRECTORY="${MENTOX_OUTPUT_DIRECTORY:-${experiment_directory}/output-real}"
export MENTOX_MEDIA_ID="${MENTOX_MEDIA_ID:-roboflow-demo-2e57b9-0}"
export MENTOX_PERMISSION_BASIS="${MENTOX_PERMISSION_BASIS:-source_terms}"
export MENTOX_PERMISSION_REFERENCE="${MENTOX_PERMISSION_REFERENCE:-https://github.com/roboflow/sports/blob/main/examples/soccer/setup.sh}"
export MENTOX_SKIP_EVALUATION="${MENTOX_SKIP_EVALUATION:-1}"

exec bash "${experiment_directory}/run.sh"
