#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
video_path="${MENTOX_INPUT_VIDEO:-${repository_root}/experiments/authorized-video/input/2e57b9_0.mp4}"
run_azure="${MENTOX_RUN_AZURE:-0}"
skip_models="${MENTOX_SKIP_MODELS:-0}"
port="${MENTOX_BACKEND_PORT:-8023}"
log_directory="${repository_root}/experiments/evidence-logs"
acceptance_report="${log_directory}/backend-integration-acceptance.json"
api_report="${log_directory}/backend-integration-api.json"
backend_log="${log_directory}/backend-integration-uvicorn.log"

required_commands=(docker ffprobe uv)
for command_name in "${required_commands[@]}"; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Falta el comando requerido: ${command_name}" >&2
    exit 1
  fi
done
if [[ ! -f "${video_path}" ]]; then
  echo "No existe el vídeo autorizado: ${video_path}" >&2
  exit 1
fi

mkdir -p "${log_directory}"
echo "Vídeo de entrada: ${video_path}"
ffprobe -v error -show_entries format=duration,size \
  -show_entries stream=codec_name,width,height,r_frame_rate \
  -of json "${video_path}"
sha256sum "${video_path}"

export MENTOX_INPUT_VIDEO="${video_path}"
export MENTOX_INTEGRATION_VIDEO="${video_path}"
export MENTOX_MEDIA_ID="${MENTOX_MEDIA_ID:-mentox-backend-integration}"
export MENTOX_PERMISSION_BASIS="${MENTOX_PERMISSION_BASIS:-source_terms}"
export MENTOX_PERMISSION_REFERENCE="${MENTOX_PERMISSION_REFERENCE:-https://github.com/roboflow/sports/blob/main/examples/soccer/setup.sh}"
export MENTOX_SKIP_EVALUATION="${MENTOX_SKIP_EVALUATION:-1}"

echo "[1/7] Ejecutando Roboflow Sports"
if [[ "${skip_models}" == "1" ]]; then
  echo "Roboflow omitido; se validará el artefacto existente."
else
  bash "${repository_root}/experiments/roboflow-sports/run-real.sh" \
    2>&1 | tee "${log_directory}/roboflow-integration.log"
fi

echo "[2/7] Ejecutando SoccerNet TeamSpotting"
if [[ "${skip_models}" == "1" ]]; then
  echo "TeamSpotting omitido; se validará el artefacto existente."
else
  bash "${repository_root}/experiments/soccernet-teamspotting/run-real.sh" \
    2>&1 | tee "${log_directory}/teamspotting-integration.log"
fi

echo "[3/7] Recalculando fusión con las salidas recién creadas"
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project "${repository_root}/apps/backend" --python 3.12 \
  python "${repository_root}/apps/backend/scripts/calibrate_observation_fusion.py" \
  "${repository_root}/experiments/roboflow-sports/output-real/roboflow-sports-predictions.json" \
  "${repository_root}/experiments/soccernet-teamspotting/output-real/soccernet-predictions.json" \
  --output "${repository_root}/experiments/fusion-calibration/output/dv-us-21-report.json" \
  2>&1 | tee "${log_directory}/fusion-integration.log"

echo "[4/7] Ejecutando aceptación integrada y validación de huellas"
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project "${repository_root}/apps/backend" --python 3.12 \
  python "${repository_root}/apps/backend/scripts/run_integrated_acceptance.py" \
  --output "${acceptance_report}" \
  2>&1 | tee "${log_directory}/acceptance-integration.log"

echo "[5/7] Ejecutando pruebas del backend"
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project "${repository_root}/apps/backend" --python 3.12 \
  pytest "${repository_root}/apps/backend/tests" -q \
  2>&1 | tee "${log_directory}/backend-tests-integration.log"

echo "[6/7] Iniciando API real y consultando estado y línea temporal"
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project "${repository_root}/apps/backend" --python 3.12 \
  uvicorn match_intelligence.main:app \
  --app-dir "${repository_root}/apps/backend/src" \
  --host 127.0.0.1 --port "${port}" >"${backend_log}" 2>&1 &
backend_pid=$!
cleanup() {
  if kill -0 "${backend_pid}" >/dev/null 2>&1; then
    kill "${backend_pid}"
    wait "${backend_pid}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

MENTOX_BACKEND_URL="http://127.0.0.1:${port}" \
MENTOX_API_REPORT="${api_report}" \
python3 - <<'PY'
import json
import os
from pathlib import Path
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, build_opener

base = os.environ["MENTOX_BACKEND_URL"]
opener = build_opener(ProxyHandler({}))
for _ in range(60):
    try:
        with opener.open(f"{base}/api/v1/integration/status", timeout=2) as response:
            status = json.load(response)
        break
    except URLError:
        time.sleep(0.5)
else:
    raise RuntimeError("El backend no respondió dentro de 30 segundos")

duration_ms = int(status["duration_ms"])
query = urlencode({"start_ms": 0, "end_ms": duration_ms, "spatial_limit": 10})
with opener.open(f"{base}/api/v1/integration/timeline?{query}", timeout=10) as response:
    timeline = json.load(response)
report = {
    "status": status,
    "timeline_summary": {
        "start_ms": timeline["start_ms"],
        "end_ms": timeline["end_ms"],
        "spatial_total": timeline["spatial_total"],
        "temporal_actions": len(timeline["temporal_actions"]),
        "fusion_candidates": len(timeline["fusion_candidates"]),
        "match_events_published": status["fusion"]["match_events_published"],
    },
}
Path(os.environ["MENTOX_API_REPORT"]).write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(report["timeline_summary"], ensure_ascii=False, indent=2))
PY
cleanup
trap - EXIT

echo "[7/7] Azure opcional"
if [[ "${run_azure}" == "1" ]]; then
  required_azure_variables=(
    EVENT_HUB_FULLY_QUALIFIED_NAMESPACE EVENT_HUB_NAME
    EVENT_HUB_CONSUMER_GROUP AZURE_BLOB_SERVICE_ENDPOINT
  )
  for variable_name in "${required_azure_variables[@]}"; do
    if [[ -z "${!variable_name:-}" ]]; then
      echo "Falta ${variable_name} para MENTOX_RUN_AZURE=1" >&2
      exit 1
    fi
  done
  UV_CACHE_DIR=/tmp/mentox-uv-cache \
  uv run --project "${repository_root}/apps/backend" --python 3.12 \
    python "${repository_root}/apps/backend/scripts/event_hubs_smoke.py" \
    2>&1 | tee "${log_directory}/event-hubs-integration.log"
  UV_CACHE_DIR=/tmp/mentox-uv-cache \
  uv run --project "${repository_root}/apps/backend" --python 3.12 \
    python "${repository_root}/apps/backend/scripts/vision_event_hubs_smoke.py" \
    2>&1 | tee "${log_directory}/vision-event-hubs-integration.log"
  UV_CACHE_DIR=/tmp/mentox-uv-cache \
  uv run --project "${repository_root}/apps/backend" --python 3.12 \
    python "${repository_root}/apps/backend/scripts/blob_storage_smoke.py" \
    2>&1 | tee "${log_directory}/blob-storage-integration.log"
else
  echo "Azure omitido. Use MENTOX_RUN_AZURE=1 con las variables configuradas."
fi

bash "${repository_root}/experiments/collect-model-evidence.sh"
echo "Integración de backend terminada correctamente."
echo "Informe de aceptación: ${acceptance_report}"
echo "Informe HTTP: ${api_report}"
