#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
resource_group="${MENTOX_AZURE_RESOURCE_GROUP:-rg-mentox-dev}"
location="${MENTOX_AZURE_LOCATION:-northcentralus}"
environment="${MENTOX_CONTAINERAPPS_ENVIRONMENT:-cae-mentox-vision-dev}"
acr_name="${MENTOX_ACR_NAME:-mentox7f7e6e99}"
identity_name="${MENTOX_WORKER_IDENTITY_NAME:-id-mentox-agent-worker-dev}"
job_name="${MENTOX_WORKER_JOB_NAME:-job-mentox-agent-worker-dev}"
service_bus_namespace="${MENTOX_SERVICE_BUS_NAMESPACE:-sb-damon-dev-hxwjzbiyupwqc}"
queue_name="${IMPORTANT_EVENTS_QUEUE_NAME:-important-events}"
image_repository="mentox/important-event-worker"
image_tag="${MENTOX_IMAGE_TAG:-$(date -u +%Y%m%d%H%M%S)}"
build_mode="${MENTOX_IMAGE_BUILD_MODE:-acr}"

for command_name in az sha256sum; do
  command -v "${command_name}" >/dev/null 2>&1 || { echo "Falta ${command_name}." >&2; exit 1; }
done

az account show --query '{subscription:name,state:state,tenant:tenantId}' --output table
az extension add --name containerapp --upgrade --yes >/dev/null
for provider in Microsoft.App Microsoft.ContainerRegistry Microsoft.ManagedIdentity Microsoft.ServiceBus; do
  az provider register --namespace "${provider}" --wait
done

login_server="$(az acr show --resource-group "${resource_group}" --name "${acr_name}" --query loginServer --output tsv)"
image="${login_server}/${image_repository}:${image_tag}"

if [[ "${build_mode}" == "acr" ]]; then
  az acr build --registry "${acr_name}" --image "${image_repository}:${image_tag}" \
    --file "${repo_root}/apps/backend/Dockerfile.worker" "${repo_root}/apps/backend"
elif [[ "${build_mode}" == "local" ]]; then
  command -v sudo >/dev/null 2>&1 || { echo "Falta sudo para Docker local." >&2; exit 1; }
  docker_config_dir="$(mktemp -d /tmp/mentox-worker-docker.XXXXXX)"
  cleanup() {
    sudo docker --config "${docker_config_dir}" logout "${login_server}" >/dev/null 2>&1 || true
    sudo rm -rf -- "${docker_config_dir}"
  }
  trap cleanup EXIT
  acr_token="$(az acr login --name "${acr_name}" --expose-token --query accessToken --output tsv)"
  printf '%s' "${acr_token}" | sudo docker --config "${docker_config_dir}" login \
    "${login_server}" --username 00000000-0000-0000-0000-000000000000 --password-stdin >/dev/null
  unset acr_token
  sudo docker --config "${docker_config_dir}" build --tag "${image}" \
    --file "${repo_root}/apps/backend/Dockerfile.worker" "${repo_root}/apps/backend"
  sudo docker --config "${docker_config_dir}" push "${image}"
  cleanup
  trap - EXIT
elif [[ "${build_mode}" == "existing" ]]; then
  existing="$(az acr repository show-tags --name "${acr_name}" --repository "${image_repository}" \
    --query "[?@=='${image_tag}'] | [0]" --output tsv)"
  [[ "${existing}" == "${image_tag}" ]] || { echo "No existe la imagen ${image}." >&2; exit 1; }
else
  echo "MENTOX_IMAGE_BUILD_MODE debe ser acr, local o existing." >&2
  exit 1
fi

if ! az identity show --resource-group "${resource_group}" --name "${identity_name}" >/dev/null 2>&1; then
  az identity create --resource-group "${resource_group}" --name "${identity_name}" \
    --location "${location}" --output none
fi

identity_id="$(az identity show --resource-group "${resource_group}" --name "${identity_name}" --query id --output tsv)"
principal_id="$(az identity show --resource-group "${resource_group}" --name "${identity_name}" --query principalId --output tsv)"
client_id="$(az identity show --resource-group "${resource_group}" --name "${identity_name}" --query clientId --output tsv)"
acr_id="$(az acr show --resource-group "${resource_group}" --name "${acr_name}" --query id --output tsv)"
service_bus_id="$(az servicebus namespace show --resource-group "${resource_group}" --name "${service_bus_namespace}" --query id --output tsv)"

if [[ "$(az role assignment list --assignee-object-id "${principal_id}" --scope "${acr_id}" --role AcrPull --query 'length(@)' --output tsv)" == "0" ]]; then
  az role assignment create --assignee-object-id "${principal_id}" --assignee-principal-type ServicePrincipal \
    --role AcrPull --scope "${acr_id}" --output none
fi
if [[ "$(az role assignment list --assignee-object-id "${principal_id}" --scope "${service_bus_id}" --role 'Azure Service Bus Data Receiver' --query 'length(@)' --output tsv)" == "0" ]]; then
  az role assignment create --assignee-object-id "${principal_id}" --assignee-principal-type ServicePrincipal \
    --role 'Azure Service Bus Data Receiver' --scope "${service_bus_id}" --output none
fi

if az containerapp job show --resource-group "${resource_group}" --name "${job_name}" >/dev/null 2>&1; then
  echo "El job ${job_name} ya existe; elimínelo explícitamente antes de recrearlo con otra topología." >&2
  exit 1
fi

az containerapp job create \
  --resource-group "${resource_group}" \
  --name "${job_name}" \
  --environment "${environment}" \
  --trigger-type Event \
  --replica-timeout 300 \
  --replica-retry-limit 2 \
  --replica-completion-count 1 \
  --parallelism 1 \
  --polling-interval 30 \
  --min-executions 0 \
  --max-executions 1 \
  --scale-rule-name important-events \
  --scale-rule-type azure-servicebus \
  --scale-rule-metadata "queueName=${queue_name}" "namespace=${service_bus_namespace}" "messageCount=1" \
  --scale-rule-identity "${identity_id}" \
  --image "${image}" \
  --cpu 0.5 \
  --memory 1Gi \
  --mi-user-assigned "${identity_id}" \
  --registry-server "${login_server}" \
  --registry-identity "${identity_id}" \
  --env-vars \
    "AZURE_CLIENT_ID=${client_id}" \
    "SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE=${service_bus_namespace}.servicebus.windows.net" \
    "IMPORTANT_EVENTS_QUEUE_NAME=${queue_name}" \
  --tags project=mentox-premier-league product=the-prime-moment workload=agent-worker environment=dev \
  --output none

echo "Worker desplegado: ${job_name}"
echo "Imagen: ${image}"
echo "Escala: 0-1 ejecuciones; CPU 0.5, memoria 1 GiB"
