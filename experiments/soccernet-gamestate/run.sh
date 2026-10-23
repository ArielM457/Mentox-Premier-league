#!/usr/bin/env bash
set -euo pipefail

experiment_directory="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${experiment_directory}/run-gpu.sh"
