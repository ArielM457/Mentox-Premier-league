#!/usr/bin/env bash
set -euo pipefail
export MENTOX_DEPLOY_SLUG="soccernet-teamspotting"
export MENTOX_DEPLOY_CONTEXT="deploy/azure-soccernet-teamspotting"
export MENTOX_DEPLOY_APP_NAME="${MENTOX_TEAMSPOTTING_APP_NAME:-ca-mentox-teamspotting-dev}"
export MENTOX_DEPLOY_IDENTITY_NAME="${MENTOX_TEAMSPOTTING_IDENTITY_NAME:-id-mentox-teamspotting-dev}"
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/deploy-gpu-model-common.sh"

