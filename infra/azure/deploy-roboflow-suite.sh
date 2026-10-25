#!/usr/bin/env bash
set -euo pipefail
export MENTOX_DEPLOY_SLUG="roboflow-suite"
export MENTOX_DEPLOY_CONTEXT="deploy/azure-roboflow-suite"
export MENTOX_DEPLOY_APP_NAME="${MENTOX_ROBOFLOW_APP_NAME:-ca-mentox-roboflow-dev}"
export MENTOX_DEPLOY_IDENTITY_NAME="${MENTOX_ROBOFLOW_IDENTITY_NAME:-id-mentox-roboflow-dev}"
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/deploy-gpu-model-common.sh"

