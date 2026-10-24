#!/usr/bin/env bash
set -euo pipefail

experiment_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(cd "${experiment_root}/.." && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
evidence_root="${repository_root}/evidencias-generadas"
bundle_directory="${evidence_root}/mentox-modelos-${timestamp}"
archive_path="${evidence_root}/mentox-modelos-${timestamp}.tar.gz"

mkdir -p "${bundle_directory}/resultados" "${bundle_directory}/logs"

{
  echo "Fecha UTC: $(date -u --iso-8601=seconds)"
  echo "Sistema: $(uname -a)"
  echo
  echo "NVIDIA:"
  if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=index,name,driver_version,memory.total \
      --format=csv,noheader
  else
    echo "nvidia-smi no disponible"
  fi
  echo
  echo "Docker:"
  sudo docker version --format 'Cliente={{.Client.Version}} Servidor={{.Server.Version}}' 2>&1 || true
  sudo docker compose version 2>&1 || true
  echo
  echo "uv:"
  uv --version 2>&1 || true
  echo
  echo "Vídeo autorizado (solo huella; el archivo no se copia):"
  if [[ -f "${repository_root}/experiments/authorized-video/input/2e57b9_0.mp4" ]]; then
    sha256sum "${repository_root}/experiments/authorized-video/input/2e57b9_0.mp4"
  else
    echo "No encontrado"
  fi
} > "${bundle_directory}/entorno.txt"

copy_if_present() {
  local source_path="$1"
  local destination_name="$2"
  if [[ -f "${source_path}" ]]; then
    cp "${source_path}" "${bundle_directory}/resultados/${destination_name}"
  fi
}

copy_if_present \
  "${repository_root}/experiments/roboflow-sports/output-real/roboflow-sports-predictions.json" \
  "roboflow-sports-predictions.json"
copy_if_present \
  "${repository_root}/experiments/roboflow-sports/output-real/roboflow-sports-evaluation-input.json" \
  "roboflow-sports-evaluation-input.json"
copy_if_present \
  "${repository_root}/experiments/soccernet-teamspotting/output-real/soccernet-predictions.json" \
  "soccernet-predictions.json"
copy_if_present \
  "${repository_root}/experiments/soccernet-teamspotting/output-real/soccernet-evaluation-input.json" \
  "soccernet-evaluation-input.json"
copy_if_present \
  "${repository_root}/experiments/fusion-calibration/output/dv-us-21-report.json" \
  "dv-us-21-report.json"
copy_if_present \
  "${repository_root}/experiments/evidence-logs/backend-integration-acceptance.json" \
  "backend-integration-acceptance.json"
copy_if_present \
  "${repository_root}/experiments/evidence-logs/backend-integration-api.json" \
  "backend-integration-api.json"
if [[ -d "${repository_root}/experiments/evidence-logs" ]]; then
  find "${repository_root}/experiments/evidence-logs" -maxdepth 1 -type f \
    \( -name '*.log' -o -name '*.json' \) \
    -exec cp {} "${bundle_directory}/logs/" \;
fi

if [[ -f "${repository_root}/experiments/soccernet-gamestate/output/sn-gamestate.pklz" ]]; then
  sha256sum "${repository_root}/experiments/soccernet-gamestate/output/sn-gamestate.pklz" \
    > "${bundle_directory}/resultados/sn-gamestate.sha256.txt"
fi

(
  cd "${bundle_directory}"
  find . -type f ! -name 'sha256sum.txt' -print0 \
    | sort -z \
    | xargs -0 sha256sum \
    > sha256sum.txt
)

tar -czf "${archive_path}" -C "${evidence_root}" "$(basename "${bundle_directory}")"

echo "Evidencia preparada:"
echo "${archive_path}"
echo
echo "Envíe ese archivo al responsable. No contiene el vídeo original ni secretos."
