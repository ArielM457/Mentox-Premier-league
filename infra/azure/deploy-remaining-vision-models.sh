#!/usr/bin/env bash
set -euo pipefail

script_directory="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

[[ -n "${MENTOX_MODEL_API_KEY:-}" ]] || {
  echo "Error: exporte MENTOX_MODEL_API_KEY antes de ejecutar este instalador." >&2
  exit 1
}

echo "1/2 Desplegando Roboflow Sports: jugadores, balón y puntos del campo."
bash "${script_directory}/deploy-roboflow-suite.sh"

echo "2/2 Desplegando SoccerNet TeamSpotting."
bash "${script_directory}/deploy-soccernet-teamspotting.sh"

echo "Modelos desplegables procesados. SoccerNet GameState no se despliega todavía:"
echo "ejecute bash infra/azure/preflight-soccernet-gamestate.sh para ver sus dependencias pendientes."

