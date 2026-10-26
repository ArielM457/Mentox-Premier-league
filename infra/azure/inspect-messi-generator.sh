#!/usr/bin/env bash
set -euo pipefail

resource_group="${MENTOX_AZURE_RESOURCE_GROUP:-rg-mentox-dev}"
job_name="${MENTOX_MESSI_JOB_NAME:-job-mentox-messi-dev}"
if [[ -n "${MENTOX_STORAGE_ACCOUNT:-}" ]]; then
  storage_account="${MENTOX_STORAGE_ACCOUNT}"
else
  mapfile -t storage_accounts < <(az storage account list --resource-group "${resource_group}" --query '[].name' --output tsv)
  [[ "${#storage_accounts[@]}" == "1" ]] || {
    echo "Error: exporte MENTOX_STORAGE_ACCOUNT; hay ${#storage_accounts[@]} cuentas en ${resource_group}." >&2
    exit 1
  }
  storage_account="${storage_accounts[0]}"
fi
container_name="${MENTOX_BLOB_CONTAINER:-synthetic-videos}"

echo "Ejecuciones del Job"
az containerapp job execution list --resource-group "${resource_group}" --name "${job_name}" \
  --query '[].{nombre:name,estado:properties.status,inicio:properties.startTime,fin:properties.endTime}' --output table

echo "Artefactos guardados"
if ! az storage blob list --account-name "${storage_account}" --container-name "${container_name}" \
  --auth-mode login --prefix messi/ --query '[].{nombre:name,bytes:properties.contentLength}' --output table; then
  echo "No se pudieron listar blobs con el usuario actual." >&2
  echo "El Job usa otra identidad; solicite Storage Blob Data Reader para inspeccionar el contenedor." >&2
fi
