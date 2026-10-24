# Infraestructura Azure de datos e ingesta

Esta carpeta despliega los recursos de DV-US-06 mediante Azure CLI y Bicep. Cada integrante usa su propia suscripción, grupo de recursos, región y prefijo. La plantilla no contiene credenciales ni identificadores personales.

## Recursos

- Namespace Standard de Azure Event Hubs.
- Event hub `match-events` para hechos deportivos confirmados.
- Event hub `vision-observations` para detecciones, acciones y candidatos experimentales.
- Event hub `match-metrics` para actualizaciones reconstruibles y tolerantes a pérdida.
- Cola opcional `important-events` en Service Bus Basic para jugadas que deben reintentarse y conservarse.
- Grupos de consumidores `backend` y `diagnostics` en ambos hubs.
- Cuenta `StorageV2` con redundancia local.
- Contenedores privados `matches`, `authorized-videos` y `observations`.

La autenticación local mediante claves compartidas está deshabilitada. Las aplicaciones deberán usar una identidad de Azure con roles RBAC. La asignación de roles se hará por cuenta o entorno y no forma parte de esta plantilla compartida.

La cola durable está desactivada por defecto para no generar un recurso con costo sin revisión. Para desplegarla, establezca `deployDurableImportantQueue = true`, ejecute `what-if` y confirme la cuota de `Microsoft.ServiceBus` en la región elegida.

## Requisitos

- Azure CLI.
- Bicep CLI administrado mediante Azure CLI.
- Permiso para crear un grupo de recursos y los recursos declarados.

Compruebe las versiones:

```bash
az version
az bicep version
```

Si falta Bicep:

```bash
az bicep install
```

## Parámetros

`projectPrefix` debe contener entre 3 y 9 caracteres en minúsculas. Se recomiendan letras y números. El prefijo permite reconocer al propietario del despliegue; `uniqueString` añade un sufijo determinista según la suscripción, el grupo y el prefijo.

Copie el ejemplo sin sobrescribirlo:

```bash
cp infra/azure/dev.bicepparam.example infra/azure/dev.bicepparam
```

`dev.bicepparam` puede mantenerse fuera de Git si contiene decisiones personales. Nunca escriba tokens, claves o cadenas de conexión en archivos de parámetros.

## Selección explícita de la suscripción

```bash
az login
az account list --output table
az account set --subscription "<suscripcion>"
az account show --query "{name:name,id:id,user:user.name}" --output table
```

El identificador mostrado sirve para confirmar la cuenta activa. No se copia a la plantilla ni se confirma en Git.

## Crear el grupo de recursos

```bash
az group create \
  --name "<grupo>" \
  --location "<region>"
```

La región del grupo se usa de forma predeterminada para los recursos. También puede suministrarse `location` como parámetro del despliegue.

## Validar y previsualizar

La validación comprueba el contrato de Azure Resource Manager sin crear los recursos:

```bash
az deployment group validate \
  --resource-group "<grupo>" \
  --template-file infra/azure/main.bicep \
  --parameters infra/azure/dev.bicepparam
```

Ejecute siempre `what-if` antes de desplegar:

```bash
az deployment group what-if \
  --resource-group "<grupo>" \
  --template-file infra/azure/main.bicep \
  --parameters infra/azure/dev.bicepparam
```

## Desplegar

```bash
az deployment group create \
  --name "mentox-data-vision" \
  --resource-group "<grupo>" \
  --template-file infra/azure/main.bicep \
  --parameters infra/azure/dev.bicepparam
```

Consulte las salidas necesarias para configurar posteriormente la aplicación:

```bash
az deployment group show \
  --name "mentox-data-vision" \
  --resource-group "<grupo>" \
  --query properties.outputs \
  --output json
```

Las salidas incluyen nombres y endpoints, pero no secretos ni cadenas de conexión.

## Probar Event Hubs con identidad de Azure

Después del despliegue y de asignar el rol `Azure Event Hubs Data Owner`, configure solo nombres y endpoints:

```bash
export EVENT_HUB_FULLY_QUALIFIED_NAMESPACE="<namespace>.servicebus.windows.net"
export EVENT_HUB_NAME="match-events"
export EVENT_HUB_CONSUMER_GROUP="diagnostics"
export VISION_OBSERVATION_TRANSPORT="azure_event_hubs"
export VISION_EVENT_HUB_NAME="vision-observations"
export VISION_EVENT_HUB_CONSUMER_GROUP="backend"
```

Para ejecutar el enrutamiento de tres canales desde el backend:

```bash
export ROUTING_TRANSPORT="azure"
export METRICS_EVENT_HUB_NAME="match-metrics"
export SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE="<namespace-service-bus>.servicebus.windows.net"
export IMPORTANT_EVENTS_QUEUE_NAME="important-events"
```

La identidad necesita `Azure Event Hubs Data Sender` en el namespace de Event Hubs y `Azure Service Bus Data Sender` en la cola o namespace de Service Bus. En desarrollo local, omita esas variables: `ROUTING_TRANSPORT=memory` es el valor predeterminado y conserva los mismos tres canales de forma reproducible.

Ejecute la prueba de ida y vuelta de DV-US-07:

```bash
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/event_hubs_smoke.py
```

La prueba inicia un consumidor, publica dos veces el mismo evento sintético y espera un aceptado y un duplicado. La salida incluye duraciones de publicación y latencia de transporte. No imprime tokens ni utiliza cadenas de conexión.

Para añadir únicamente el canal visual a un namespace ya desplegado, sin reconciliar otros recursos:

```bash
az deployment group what-if \
  --resource-group "<grupo>" \
  --template-file infra/azure/vision-observations.bicep \
  --parameters eventHubNamespaceName="<namespace>"

az deployment group create \
  --name "mentox-vision-observations" \
  --resource-group "<grupo>" \
  --template-file infra/azure/vision-observations.bicep \
  --parameters eventHubNamespaceName="<namespace>"
```

Después se comprueba productor, consumidor y deduplicación sin crear `MatchEvent`:

```bash
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/vision_event_hubs_smoke.py
```

## Probar Blob Storage con identidad de Azure

Después del despliegue y de asignar el rol `Storage Blob Data Contributor`, use la salida `blobServiceEndpoint` de la plantilla:

```bash
export AZURE_BLOB_SERVICE_ENDPOINT="https://<storage-account>.blob.core.windows.net"
```

Ejecute la carga y descarga de DV-US-09:

```bash
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/blob_storage_smoke.py
```

La prueba genera un partido sintético nuevo, lo guarda en `matches` con el partido y el origen en el nombre y los metadatos, vuelve a descargarlo y compara su hash SHA-256. No usa datos reales, claves compartidas ni cadenas de conexión. El blob se conserva para permitir la repetición y la revisión de procedencia; elimínelo manualmente cuando la política del entorno lo indique.

## Probar dos prefijos

Para demostrar que dos integrantes no necesitan editar `main.bicep`, cree dos archivos locales a partir del ejemplo y cambie únicamente `projectPrefix`. Use grupos de recursos distintos o nombres de despliegue distintos y ejecute `validate` y `what-if` para ambos.

Los nombres del namespace y de Storage cambian con el prefijo y con el sufijo determinista. Ejecutar nuevamente la misma combinación de suscripción, grupo y prefijo produce los mismos nombres.

## Roles para las historias posteriores

DV-US-07 y DV-US-09 deberán asignar, como mínimo, roles equivalentes a:

- `Azure Event Hubs Data Owner` para publicar y consumir durante la integración.
- `Storage Blob Data Contributor` para escribir y leer artefactos.

La identidad concreta puede ser el usuario autenticado para desarrollo o una identidad administrada para un despliegue compartido. No se incluyen asignaciones automáticas porque el principal y el alcance deben elegirse explícitamente en cada cuenta.

## Eliminación explícita

Eliminar un grupo destruye todos sus recursos. Este comando no forma parte de las pruebas normales y debe ejecutarse solo después de revisar el nombre exacto:

```bash
az group show --name "<grupo>" --output table
az group delete --name "<grupo>"
```

La eliminación no es reversible.

## Límites de la verificación local

Compilar Bicep localmente demuestra que la sintaxis y los tipos son válidos. `validate`, `what-if` y `create` requieren una suscripción autenticada y permisos. La historia no se considera verificada en Azure hasta ejecutar esos comandos y conservar sus resultados sin secretos.

## Recursos de analítica (Persona 2)

`analytics.bicep` añade, en el mismo grupo de recursos y sin modificar `main.bicep`, el event hub `match-insights` con los grupos `narrative`, `experience` y `diagnostics`, y los contenedores privados `analytics` y `models`. Reutiliza el namespace y la cuenta de Storage mediante sus nombres, tomados de las salidas de este despliegue:

```bash
cp infra/azure/analytics.bicepparam.example infra/azure/analytics.bicepparam
az deployment group what-if \
  --resource-group "<grupo>" \
  --template-file infra/azure/analytics.bicep \
  --parameters infra/azure/analytics.bicepparam
```

Los roles, las variables, el procesador continuo y la prueba de humo están en [integración de la analítica con Azure](../../docs/persona-2-estado-y-analitica/integracion-azure.md).
