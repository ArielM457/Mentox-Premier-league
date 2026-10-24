# Evidencia técnica de DV-US-14

## Identificación

- **Historia:** DV-US-14 · Desplegar y autorizar el entorno real.
- **Estado:** verificada en integración.
- **Prioridad:** P0.
- **Última verificación:** 13 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.
- **Eleva:** DV-US-06.

## Objetivo comprobado

Se comprobó la suscripción Azure for Students, se creó el grupo de recursos de desarrollo, se registró el proveedor de Event Hubs y se identificó la política que restringe las regiones. La plantilla Bicep usó `centralus`, superó `validate` y `what-if`, y después se desplegó en modo incremental.

Azure confirmó el namespace de Event Hubs, el event hub, los dos grupos de consumidores, la cuenta StorageV2 y los tres contenedores. Un principal de servicio temporal recibió únicamente `Azure Event Hubs Data Owner` sobre el namespace y `Storage Blob Data Contributor` sobre la cuenta de almacenamiento. No se registran su identificador, secreto ni datos personales.

## Diagnóstico de la región

La primera validación usó `eastus` y Azure respondió `RequestDisallowedByAzure` para Event Hubs y Storage. Azure MCP confirmó una asignación de política denominada `Allowed resource deployment regions` y una consulta de solo lectura mostró estas regiones permitidas:

- `northcentralus`;
- `chilecentral`;
- `canadacentral`;
- `eastus2`;
- `centralus`.

La lista global del proveedor no era suficiente porque mostraba regiones técnicamente compatibles, pero no las restricciones particulares de la suscripción.

Se eligió `centralus` porque admite ambos recursos y el precio público consultado para una unidad de Event Hubs Standard fue USD 0,03 por hora, igual que `eastus2` y menor que `chilecentral`. La cifra es una referencia pública, no una factura ni una garantía del cargo aplicado al crédito estudiantil.

## Entradas

| Elemento | Valor registrado |
|---|---|
| Suscripción | Azure for Students, activa; identificador omitido |
| Grupo de recursos | `rg-mentox-dev` |
| Región de los recursos | `centralus` |
| Prefijo | `damon` |
| Entorno | `dev` |
| Parámetros | `infra/azure/dev.bicepparam`, ignorado por Git |

## Resultados

### Compilación local

- `main.bicep` compiló correctamente.
- `dev.bicepparam` compiló correctamente.
- `git diff --check` terminó sin errores.

### Validación de Azure

- Estado: `Succeeded`.
- Región evaluada para Event Hubs: `centralus`.
- Región evaluada para Storage: `centralus`.
- Recursos validados: namespace, event hub, dos grupos de consumidores, cuenta StorageV2, servicio Blob y tres contenedores.
- Errores: ninguno.

### Previsualización `what-if`

- Estado: `Succeeded`.
- Cambios previstos: nueve creaciones.
- Modificaciones previstas: ninguna.
- Eliminaciones previstas: ninguna.
- Event Hubs: Standard, capacidad 1, autenticación local deshabilitada y TLS 1.2.
- Storage: `Standard_LRS`, acceso público a blobs deshabilitado, claves compartidas deshabilitadas, OAuth predeterminado, HTTPS y TLS 1.2.
- Contenedores privados: `matches`, `authorized-videos` y `observations`.

### Despliegue

- Nombre: `mentox-data-vision`.
- Estado: `Succeeded`.
- Modo: incremental.
- Duración informada por Azure: 43,688 segundos.
- Recursos de salida: nueve.
- Event Hub: `match-events`.
- Grupos consumidores: `backend` y `diagnostics`.
- Contenedores privados: `matches`, `authorized-videos` y `observations`.
- Error: ninguno.

Azure MCP confirmó posteriormente que el namespace y la cuenta de almacenamiento permanecían en `centralus`.

### Autorización

- Identidad: principal de servicio temporal para la integración del equipo; nombre e identificadores sensibles omitidos de la evidencia.
- Event Hubs: `Azure Event Hubs Data Owner`, limitado al namespace.
- Storage: `Storage Blob Data Contributor`, limitado a la cuenta.
- Comprobación: ambas asignaciones aparecieron mediante `az role assignment list --all` y mediante Azure MCP.
- Credencial: secreto temporal con vencimiento definido; valor no guardado en Git, documentos ni salidas conservadas.

## Archivos involucrados

| Archivo | Uso |
|---|---|
| `infra/azure/main.bicep` | Plantilla validada sin cambios estructurales |
| `infra/azure/dev.bicepparam` | Parámetros locales con `centralus`; fuera de Git |
| `.codex/config.toml` | Azure MCP habilitado para diagnóstico del proyecto |
| `docs/persona-1-datos-y-vision/evidencias/DV-US-14.md` | Evidencia parcial y anonimizada |

## Comandos reproducibles

```bash
az provider register --namespace Microsoft.EventHub --wait

az policy assignment show \
  --name sys.regionrestriction \
  --query parameters \
  --output json

az deployment group validate \
  --resource-group "rg-mentox-dev" \
  --template-file infra/azure/main.bicep \
  --parameters infra/azure/dev.bicepparam

az deployment group what-if \
  --resource-group "rg-mentox-dev" \
  --template-file infra/azure/main.bicep \
  --parameters infra/azure/dev.bicepparam

az deployment group create \
  --name "mentox-data-vision" \
  --resource-group "rg-mentox-dev" \
  --template-file infra/azure/main.bicep \
  --parameters infra/azure/dev.bicepparam

az role assignment list \
  --assignee-object-id "<object-id-omitido>" \
  --all \
  --query "[].{rol:roleDefinitionName,alcance:scope}" \
  --output table
```

No se incluyen salidas completas porque contienen identificadores de suscripción y correlación.

## Versiones

| Componente | Versión |
|---|---|
| Azure CLI | 2.88.0 |
| Bicep CLI | 0.48.1 |
| Azure MCP Server | 3.0.0-beta.50 |
| Python | 3.12.13 |
| uv | 0.11.32 |
| Suite posterior | 135 pruebas aprobadas en 0,67 s |

## Criterios de aceptación

| Criterio | Evidencia | Estado |
|---|---|---|
| Comprobar cuenta y suscripción antes de desplegar | Suscripción activa y predeterminada | Cumplido |
| Ejecutar `validate` y `what-if` antes de `create` | Ambas operaciones terminaron en `Succeeded` | Cumplido |
| Crear Event Hubs, Storage y contenedores | Despliegue `Succeeded`; nueve recursos de salida y comprobación posterior | Cumplido |
| Asignar roles de Event Hubs y Blob Storage | Dos roles de datos limitados a sus recursos y confirmados por CLI y Azure MCP | Cumplido |
| Registrar resultados sin secretos ni datos personales | Evidencia resumida; se omiten suscripción, principal, secreto y correlaciones | Cumplido |
| Registrar región, versiones, costo y eliminación | Región, versiones, precio de referencia y eliminación explícita documentados | Cumplido |

## Limitaciones y siguientes pasos

- La política regional sigue activa y debe respetarse; no se intentará eludirla.
- Event Hubs Standard genera cargos mientras el namespace exista. Una unidad a USD 0,03 por hora equivale aproximadamente a USD 21,90 por 730 horas, antes de eventos facturables y otros consumos.
- El namespace Standard genera costo mientras exista, aunque no reciba eventos; el equipo debe revisar el crédito y eliminar el entorno cuando deje de necesitarlo.
- El secreto compartido es una decisión temporal del equipo. Debe distribuirse mediante un canal seguro, rotarse si se expone y revocarse al terminar la integración. Para un backend desplegado se debe preferir identidad administrada.
- DV-US-15 y DV-US-16 conservan por separado las pruebas reales de transporte y almacenamiento; no se confunden con la mera creación de infraestructura.
