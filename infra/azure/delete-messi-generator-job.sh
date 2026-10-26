#!/usr/bin/env bash
set -euo pipefail

resource_group="${MENTOX_AZURE_RESOURCE_GROUP:-rg-mentox-dev}"
job_name="${MENTOX_MESSI_JOB_NAME:-job-mentox-messi-dev}"

[[ "${MENTOX_CONFIRM_DELETE_JOB:-0}" == "1" ]] || {
  echo "No se eliminó nada. Revise el recurso y exporte MENTOX_CONFIRM_DELETE_JOB=1." >&2
  exit 1
}

az containerapp job show --resource-group "${resource_group}" --name "${job_name}" \
  --query '{nombre:name,grupo:resourceGroup,estado:properties.provisioningState}' --output table

az containerapp job delete --resource-group "${resource_group}" --name "${job_name}" --yes

echo "Job eliminado: ${job_name}"
echo "Los MP4 y manifiestos permanecen en Blob Storage."
echo "ACR, identidad, entorno y perfil T4 compartido no fueron eliminados."
