#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

resource_group="${MENTOX_AZURE_RESOURCE_GROUP:-rg-mentox-dev}"
location="${MENTOX_AZURE_LOCATION:-northcentralus}"
environment_name="${MENTOX_CONTAINERAPPS_ENVIRONMENT:-cae-mentox-vision-dev}"
container_app_name="${MENTOX_PLAYER_APP_NAME:-ca-mentox-player-dev}"
identity_name="${MENTOX_PLAYER_IDENTITY_NAME:-id-mentox-player-dev}"
workload_profile_name="${MENTOX_GPU_PROFILE_NAME:-NC8as-T4}"
workload_profile_type="Consumption-GPU-NC8as-T4"
image_repository="mentox/roboflow-player"
min_replicas="${MENTOX_MIN_REPLICAS:-0}"
max_replicas="${MENTOX_MAX_REPLICAS:-1}"
ingress="${MENTOX_MODEL_INGRESS:-external}"
image_build_mode="${MENTOX_IMAGE_BUILD_MODE:-acr}"

die() {
  echo "Error: $*" >&2
  exit 1
}

for command_name in az git openssl; do
  command -v "${command_name}" >/dev/null 2>&1 || die "Falta el comando ${command_name}."
done

[[ "${MENTOX_ACCEPT_MODEL_LICENSES:-0}" == "1" ]] || die \
  "Revise deploy/azure-roboflow-player/README.md y exporte MENTOX_ACCEPT_MODEL_LICENSES=1."
[[ -n "${MENTOX_MODEL_API_KEY:-}" ]] || die \
  "Exporte MENTOX_MODEL_API_KEY con un valor generado por: openssl rand -hex 32"
[[ "${#MENTOX_MODEL_API_KEY}" -ge 32 ]] || die "MENTOX_MODEL_API_KEY debe tener al menos 32 caracteres."
[[ "${min_replicas}" =~ ^[01]$ ]] || die "MENTOX_MIN_REPLICAS debe ser 0 o 1."
[[ "${max_replicas}" == "1" ]] || die "Esta primera versión limita MENTOX_MAX_REPLICAS a 1."
[[ "${ingress}" == "external" || "${ingress}" == "internal" ]] || die \
  "MENTOX_MODEL_INGRESS debe ser external o internal."
[[ "${image_build_mode}" == "acr" || "${image_build_mode}" == "local" || "${image_build_mode}" == "existing" ]] || die \
  "MENTOX_IMAGE_BUILD_MODE debe ser acr, local o existing."

az account show --query '{subscription:name,state:state,tenant:tenantId}' --output table
[[ "$(az account show --query state --output tsv)" == "Enabled" ]] || die "La suscripción activa no está habilitada."

az extension add --name containerapp --upgrade --yes >/dev/null
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.ContainerRegistry --wait
az provider register --namespace Microsoft.ManagedIdentity --wait
az provider register --namespace Microsoft.OperationalInsights --wait

supported_profile="$(az containerapp env workload-profile list-supported \
  --location "${location}" \
  --query "[?name=='${workload_profile_type}'].name | [0]" \
  --output tsv)"
[[ "${supported_profile}" == "${workload_profile_type}" ]] || die \
  "${workload_profile_type} no está disponible en ${location} para esta consulta. Pruebe otra región y confirme cuota."

if ! az group show --name "${resource_group}" >/dev/null 2>&1; then
  az group create --name "${resource_group}" --location "${location}" --output none
fi

suffix="$(printf '%s' "$(az account show --query id --output tsv):${resource_group}" | sha256sum | cut -c1-8)"
acr_name="${MENTOX_ACR_NAME:-mentox${suffix}}"
image_tag="$(git -C "${repository_root}" rev-parse --short=12 HEAD)"

if ! az acr show --resource-group "${resource_group}" --name "${acr_name}" >/dev/null 2>&1; then
  az acr create \
    --resource-group "${resource_group}" \
    --name "${acr_name}" \
    --location "${location}" \
    --sku Basic \
    --admin-enabled false \
    --output none
fi

login_server="$(az acr show --resource-group "${resource_group}" --name "${acr_name}" --query loginServer --output tsv)"
image="${login_server}/${image_repository}:${image_tag}"

if [[ "${image_build_mode}" == "acr" ]]; then
  az acr build \
    --registry "${acr_name}" \
    --image "${image_repository}:${image_tag}" \
    --file "${repository_root}/deploy/azure-roboflow-player/Dockerfile" \
    "${repository_root}/deploy/azure-roboflow-player"
elif [[ "${image_build_mode}" == "local" ]]; then
  command -v docker >/dev/null 2>&1 || die "Falta Docker para MENTOX_IMAGE_BUILD_MODE=local."
  command -v sudo >/dev/null 2>&1 || die "Falta sudo para ejecutar Docker local en este equipo."

  docker_config_dir="$(mktemp -d /tmp/mentox-docker-config.XXXXXX)"
  cleanup_docker_auth() {
    sudo docker --config "${docker_config_dir}" logout "${login_server}" >/dev/null 2>&1 || true
    sudo rm -rf -- "${docker_config_dir}"
  }
  trap cleanup_docker_auth EXIT

  acr_access_token="$(az acr login --name "${acr_name}" --expose-token --query accessToken --output tsv)"
  printf '%s' "${acr_access_token}" | sudo docker --config "${docker_config_dir}" login \
    "${login_server}" \
    --username 00000000-0000-0000-0000-000000000000 \
    --password-stdin >/dev/null
  unset acr_access_token

  sudo docker --config "${docker_config_dir}" build \
    --tag "${image}" \
    --file "${repository_root}/deploy/azure-roboflow-player/Dockerfile" \
    "${repository_root}/deploy/azure-roboflow-player"
  sudo docker --config "${docker_config_dir}" push "${image}"

  cleanup_docker_auth
  trap - EXIT
else
  existing_tag="$(az acr repository show-tags \
    --name "${acr_name}" \
    --repository "${image_repository}" \
    --query "[?@=='${image_tag}'] | [0]" \
    --output tsv)"
  [[ "${existing_tag}" == "${image_tag}" ]] || die \
    "No existe ${image_repository}:${image_tag} en ${acr_name}; use el modo local o acr."
fi

if ! az identity show --resource-group "${resource_group}" --name "${identity_name}" >/dev/null 2>&1; then
  az identity create \
    --resource-group "${resource_group}" \
    --name "${identity_name}" \
    --location "${location}" \
    --output none
fi
identity_id="$(az identity show --resource-group "${resource_group}" --name "${identity_name}" --query id --output tsv)"
principal_id="$(az identity show --resource-group "${resource_group}" --name "${identity_name}" --query principalId --output tsv)"
acr_id="$(az acr show --resource-group "${resource_group}" --name "${acr_name}" --query id --output tsv)"

if [[ "$(az role assignment list --assignee-object-id "${principal_id}" --scope "${acr_id}" --role AcrPull --query 'length(@)' --output tsv)" == "0" ]]; then
  az role assignment create \
    --assignee-object-id "${principal_id}" \
    --assignee-principal-type ServicePrincipal \
    --role AcrPull \
    --scope "${acr_id}" \
    --output none
fi

if ! az containerapp env show --resource-group "${resource_group}" --name "${environment_name}" >/dev/null 2>&1; then
  az containerapp env create \
    --resource-group "${resource_group}" \
    --name "${environment_name}" \
    --location "${location}" \
    --environment-mode WorkloadProfiles \
    --logs-destination none \
    --output none
fi

if ! az containerapp env workload-profile show \
  --resource-group "${resource_group}" \
  --name "${environment_name}" \
  --workload-profile-name "${workload_profile_name}" >/dev/null 2>&1; then
  az containerapp env workload-profile add \
    --resource-group "${resource_group}" \
    --name "${environment_name}" \
    --workload-profile-name "${workload_profile_name}" \
    --workload-profile-type "${workload_profile_type}" \
    --output none
fi

if az containerapp show --resource-group "${resource_group}" --name "${container_app_name}" >/dev/null 2>&1; then
  az containerapp identity assign \
    --resource-group "${resource_group}" \
    --name "${container_app_name}" \
    --user-assigned "${identity_id}" \
    --output none
  az containerapp registry set \
    --resource-group "${resource_group}" \
    --name "${container_app_name}" \
    --server "${login_server}" \
    --identity "${identity_id}" \
    --output none
  az containerapp secret set \
    --resource-group "${resource_group}" \
    --name "${container_app_name}" \
    --secrets model-api-key="${MENTOX_MODEL_API_KEY}" \
    --output none
  az containerapp update \
    --resource-group "${resource_group}" \
    --name "${container_app_name}" \
    --image "${image}" \
    --cpu 8 \
    --memory 56Gi \
    --min-replicas "${min_replicas}" \
    --max-replicas "${max_replicas}" \
    --set-env-vars MENTOX_MODEL_API_KEY=secretref:model-api-key \
    --output none
else
  az containerapp create \
    --resource-group "${resource_group}" \
    --name "${container_app_name}" \
    --environment "${environment_name}" \
    --image "${image}" \
    --user-assigned "${identity_id}" \
    --registry-server "${login_server}" \
    --registry-identity "${identity_id}" \
    --workload-profile-name "${workload_profile_name}" \
    --cpu 8 \
    --memory 56Gi \
    --ingress "${ingress}" \
    --target-port 8000 \
    --transport auto \
    --min-replicas "${min_replicas}" \
    --max-replicas "${max_replicas}" \
    --secrets model-api-key="${MENTOX_MODEL_API_KEY}" \
    --env-vars MENTOX_MODEL_API_KEY=secretref:model-api-key \
    --output none
fi

fqdn="$(az containerapp show \
  --resource-group "${resource_group}" \
  --name "${container_app_name}" \
  --query properties.configuration.ingress.fqdn \
  --output tsv)"

echo "Despliegue preparado."
echo "Aplicación: ${container_app_name}"
echo "Imagen: ${image}"
echo "Réplicas: ${min_replicas}-${max_replicas}"
if [[ -n "${fqdn}" ]]; then
  echo "Endpoint: https://${fqdn}"
  echo "Prueba de disponibilidad: curl https://${fqdn}/health/ready"
  echo "La predicción requiere el encabezado X-API-Key; no copie la clave en Git."
else
  echo "El ingreso es interno; consuma el modelo desde otro servicio del entorno."
fi

