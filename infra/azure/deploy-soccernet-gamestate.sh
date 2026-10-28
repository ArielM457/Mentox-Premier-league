#!/usr/bin/env bash
set -euo pipefail
export MENTOX_DEPLOY_SLUG="soccernet-gamestate"
export MENTOX_DEPLOY_CONTEXT="deploy/azure-soccernet-gamestate"
export MENTOX_DEPLOY_APP_NAME="${MENTOX_GAMESTATE_APP_NAME:-ca-mentox-gamestate-dev}"
export MENTOX_DEPLOY_IDENTITY_NAME="${MENTOX_GAMESTATE_IDENTITY_NAME:-id-mentox-gamestate-dev}"
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/deploy-gpu-model-common.sh"

