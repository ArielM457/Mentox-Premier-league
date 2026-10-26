#!/usr/bin/env bash
# Operación segura de SoccerNet TeamSpotting para Ariel: deploy/start/status/stop.
set -euo pipefail

resource_group="${MENTOX_AZURE_RESOURCE_GROUP:-rg-mentox-dev}"
app_name="${MENTOX_TEAMSPOTTING_APP_NAME:-ca-mentox-teamspotting-dev}"
action="${1:-}"

die() { echo "Error: $*" >&2; exit 1; }
command -v az >/dev/null 2>&1 || die "Falta Azure CLI."
command -v curl >/dev/null 2>&1 || die "Falta curl."

endpoint() {
  local fqdn
  fqdn="$(az containerapp show --resource-group "${resource_group}" --name "${app_name}" \
    --query properties.configuration.ingress.fqdn --output tsv)"
  printf 'https://%s' "${fqdn}"
}

case "${action}" in
  deploy)
    : "${MENTOX_MODEL_API_KEY:?Exporte MENTOX_MODEL_API_KEY antes de desplegar}"
    export MENTOX_MIN_REPLICAS=0
    export MENTOX_MAX_REPLICAS=1
    "$(dirname "${BASH_SOURCE[0]}")/deploy-soccernet-teamspotting.sh"
    echo "Desplegado en escala cero. Ejecute: bash infra/azure/teamspotting-ariel.sh start"
    ;;
  start)
    az containerapp revision set-mode --resource-group "${resource_group}" \
      --name "${app_name}" --mode single --output none
    az containerapp update --resource-group "${resource_group}" --name "${app_name}" \
      --min-replicas 1 --max-replicas 1 --output none
    model_endpoint="$(endpoint)"
    echo "Esperando el arranque del modelo en ${model_endpoint} ..."
    for attempt in $(seq 1 30); do
      if curl --silent --show-error --fail --connect-timeout 10 --max-time 30 \
        "${model_endpoint}/health/ready"; then
        echo
        echo "TeamSpotting está listo. Ya puede iniciar la reproducción."
        echo "Al terminar: bash infra/azure/teamspotting-ariel.sh stop"
        exit 0
      fi
      echo "Intento ${attempt}/30: el modelo sigue iniciando; se reintentará en 10 s."
      sleep 10
    done
    die "El modelo no quedó listo. Revise las revisiones y logs antes de reproducir."
    ;;
  status)
    az containerapp revision list --resource-group "${resource_group}" --name "${app_name}" \
      --query "[].{revision:name,activa:properties.active,salud:properties.healthState,estado:properties.runningState,replicas:properties.replicas}" \
      --output table
    ;;
  stop)
    az containerapp update --resource-group "${resource_group}" --name "${app_name}" \
      --min-replicas 0 --max-replicas 1 --output none
    echo "Escala mínima configurada en cero. Azure retirará la réplica cuando quede inactiva."
    ;;
  *)
    die "Uso: bash infra/azure/teamspotting-ariel.sh {deploy|start|status|stop}"
    ;;
esac
