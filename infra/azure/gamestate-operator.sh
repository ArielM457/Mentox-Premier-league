#!/usr/bin/env bash
# Despliegue y operación segura de SoccerNet GameState en una suscripción separada.
set -euo pipefail

resource_group="${MENTOX_AZURE_RESOURCE_GROUP:-rg-mentox-dev}"
app_name="${MENTOX_GAMESTATE_APP_NAME:-ca-mentox-gamestate-dev}"
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
    "$(dirname "${BASH_SOURCE[0]}")/deploy-soccernet-gamestate.sh"
    echo "GameState quedó desplegado en escala cero."
    echo "Para encenderlo: bash infra/azure/gamestate-operator.sh start"
    ;;
  start)
    az containerapp revision set-mode --resource-group "${resource_group}" \
      --name "${app_name}" --mode single --output none
    az containerapp update --resource-group "${resource_group}" --name "${app_name}" \
      --min-replicas 1 --max-replicas 1 --output none
    model_endpoint="$(endpoint)"
    echo "Esperando GameState en ${model_endpoint} ..."
    for attempt in $(seq 1 45); do
      if curl --silent --show-error --fail --connect-timeout 10 --max-time 30 \
        "${model_endpoint}/health/ready"; then
        echo
        echo "GameState está listo para recibir un análisis."
        echo "Al finalizar: bash infra/azure/gamestate-operator.sh stop"
        exit 0
      fi
      echo "Intento ${attempt}/45: arranque en curso; nuevo intento en 10 s."
      sleep 10
    done
    die "GameState no quedó listo. Ejecute status y revise los logs de la revisión."
    ;;
  status)
    az containerapp revision list --resource-group "${resource_group}" --name "${app_name}" \
      --query "[].{revision:name,activa:properties.active,salud:properties.healthState,estado:properties.runningState,replicas:properties.replicas}" \
      --output table
    ;;
  stop)
    az containerapp update --resource-group "${resource_group}" --name "${app_name}" \
      --min-replicas 0 --max-replicas 1 --output none
    echo "Escala mínima configurada en cero. Espere a que Azure retire la réplica."
    ;;
  endpoint)
    endpoint
    echo
    ;;
  *)
    die "Uso: bash infra/azure/gamestate-operator.sh {deploy|start|status|stop|endpoint}"
    ;;
esac

