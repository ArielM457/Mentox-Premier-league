# Evidencia técnica de DV-US-06

## Identificación

- **Historia:** DV-US-06 · Desplegar recursos en una cuenta propia.
- **Estado:** verificada en Azure mediante DV-US-14.
- **Prioridad:** P0.
- **Última verificación:** 13 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.
- **Requisitos relacionados:** DV-RF-15, DV-RF-16, DV-RNF-04 y DV-RNF-05.

## Objetivo comprobado

> **Actualización de integración:** el 13 de octubre de 2026 la plantilla superó `validate` y `what-if` y se desplegó en `centralus` con estado `Succeeded`. Los recursos y RBAC están documentados de forma anonimizada en [DV-US-14](DV-US-14.md). Las referencias posteriores de este informe a un despliegue pendiente describen el corte local original del 9 de octubre.

Cada integrante dispone de una plantilla Bicep común y comandos documentados para desplegar Event Hubs y Blob Storage en su propia suscripción sin editar `main.bicep` ni guardar credenciales. La plantilla compila localmente y su contrato se comprueba mediante pruebas automatizadas.

No se afirma que los recursos existan todavía en Azure. `validate`, `what-if` y `create` requieren una sesión autenticada, permisos y una suscripción elegida por el integrante.

## Alcance implementado

- Plantilla Bicep con alcance de grupo de recursos.
- Parámetros para prefijo, entorno y región.
- Nombres estables derivados de `projectPrefix` y `uniqueString`.
- Namespace Standard de Azure Event Hubs.
- Event hub `match-events` con dos particiones y un día de retención.
- Grupos de consumidores separados `backend` y `diagnostics`.
- Cuenta `StorageV2` con redundancia local.
- Contenedores privados `matches`, `authorized-videos` y `observations`.
- Autenticación local por claves deshabilitada en Event Hubs y Storage.
- Salidas con nombres y endpoints, sin secretos.
- Archivo de parámetros de ejemplo sin datos personales.
- Guía de inicio de sesión, selección de suscripción, validación, `what-if`, despliegue, consulta de salidas y eliminación explícita.
- Exclusión en Git de archivos locales terminados en `.bicepparam`.
- Pruebas automatizadas del contrato mínimo de infraestructura.

## Fuera del alcance

- No se desplegaron recursos en una suscripción real durante esta verificación.
- No se ejecutaron `az deployment group validate`, `what-if` ni `create` contra Azure.
- No se asignaron roles RBAC porque la identidad depende de cada cuenta.
- No se crearon productores o consumidores del SDK; corresponden a DV-US-07 y DV-US-08.
- No se probó escritura o lectura de Blob Storage; corresponde a DV-US-09.
- No se automatizó la eliminación de recursos.
- No se fijó una región recomendada ni un límite de coste, decisiones que siguen abiertas.

## Entradas y resultados

| Elemento | Descripción |
|---|---|
| Suscripción | Se selecciona explícitamente con Azure CLI y no se guarda en Git |
| Grupo de recursos | Se suministra en cada comando de despliegue |
| `projectPrefix` | Entre 3 y 9 caracteres; se recomiendan letras y números en minúsculas |
| `environmentName` | `dev`, `test` o `demo` |
| `location` | Región del grupo de recursos por defecto o valor suministrado |
| Resultado esperado | Event Hubs, grupos de consumidores, StorageV2 y contenedores privados |
| Salidas | Nombres de recursos, endpoints y nombres de contenedores |

## Recursos declarados

| Tipo | Nombre lógico | Configuración principal |
|---|---|---|
| Event Hubs namespace | Derivado del prefijo, entorno y sufijo | Standard, capacidad 1, TLS 1.2, sin autenticación local |
| Event hub | `match-events` | Dos particiones, retención de un día |
| Consumer group | `backend` | Consumo del estado y analítica |
| Consumer group | `diagnostics` | Pruebas y diagnóstico aislados |
| Storage account | Derivado del prefijo y sufijo | StorageV2, Standard_LRS, HTTPS, TLS 1.2, sin claves compartidas |
| Blob container | `matches` | Privado; partidos sintéticos |
| Blob container | `authorized-videos` | Privado; solo vídeos autorizados |
| Blob container | `observations` | Privado; observaciones experimentales |

## Cambios técnicos

| Archivo | Cambio | Motivo |
|---|---|---|
| `infra/azure/main.bicep` | Recursos, parámetros, seguridad y salidas | Implementar la infraestructura reproducible |
| `infra/azure/dev.bicepparam.example` | Parámetros de ejemplo | Permitir configurar un despliegue sin editar la plantilla |
| `infra/azure/README.md` | Flujo completo de Azure CLI | Permitir que otro integrante repita la operación |
| `apps/backend/tests/test_azure_infrastructure.py` | Siete pruebas de contrato | Detectar pérdidas de recursos, comandos o controles de seguridad |
| `.gitignore` | Ignora `infra/azure/*.bicepparam` | Evitar confirmar parámetros locales por accidente |
| `docs/persona-1-datos-y-vision/historias-de-usuario.md` | Estado y enlace | Mantener la trazabilidad del backlog |
| `docs/persona-1-datos-y-vision/evidencias/README.md` | Registro de DV-US-06 | Mostrar el estado real de verificación |

## Decisiones técnicas

### Nombres deterministas

`uniqueString(subscription().id, resourceGroup().id, projectPrefix)` genera el mismo sufijo para la misma combinación de suscripción, grupo y prefijo. El prefijo hace reconocible el despliegue y el sufijo reduce colisiones en recursos con nombres globales. Dos integrantes pueden cambiar el prefijo mediante parámetros sin editar `main.bicep`.

La cuenta de Storage concatena `st`, un prefijo normalizado y el sufijo de 13 caracteres. El límite de nueve caracteres del prefijo mantiene el nombre dentro del máximo de 24 caracteres de Storage.

### Autenticación sin secretos compartidos

Event Hubs usa `disableLocalAuth: true` y Storage usa `allowSharedKeyAccess: false` con `defaultToOAuthAuthentication: true`. Las historias posteriores deberán usar Azure CLI, identidad administrada u otra identidad de Microsoft Entra con RBAC.

La plantilla no llama `listKeys`, no genera cadenas de conexión y no expone claves en sus salidas.

### Acceso de red

El acceso público de red permanece habilitado para permitir el desarrollo desde cuentas individuales. Esto no significa acceso anónimo: Blob no permite acceso público y ambos servicios requieren identidad. Una red privada o reglas de firewall quedan para un entorno compartido cuando se conozca su topología.

### Roles fuera de la plantilla

No se asignan roles automáticamente porque el principal cambia por cuenta. La guía identifica `Azure Event Hubs Data Owner` y `Storage Blob Data Contributor` como roles de integración posteriores. Cada asignación debe tener una identidad y alcance revisados.

### Eliminación separada

La eliminación aparece como una operación manual, explícita y destructiva. No forma parte de pruebas ni despliegues normales.

## Documentación consultada

Context7 se consultó antes de implementar:

- Biblioteca `/websites/learn_microsoft_en-us_azure_azure-resource-manager_bicep` para `uniqueString`, parámetros y nombres estables.
- Biblioteca `/websites/learn_microsoft_en-us_cli_azure` para `az deployment group validate`, `what-if`, creación de grupos y eliminación explícita.

Context7 no devolvió el esquema específico de Event Hubs. Esa parte se contrastó con la referencia oficial Microsoft Learn de `Microsoft.EventHub/namespaces/eventhubs/consumerGroups@2024-01-01` y la referencia de `Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01`.

La consulta de documentación no reemplaza la compilación local ni una futura prueba en Azure.

## Cobertura de criterios de aceptación

| Criterio | Implementación | Evidencia | Estado |
|---|---|---|---|
| Iniciar sesión y seleccionar explícitamente la suscripción | Guía con `az login`, `az account list`, `set` y `show` | Revisión automatizada de la guía | Documentado; ejecución pendiente |
| Previsualizar antes de desplegar | Comando `az deployment group what-if` | `test_documentation_requires_validate_what_if_and_explicit_subscription` | Documentado; ejecución pendiente |
| Suministrar grupo, región y prefijo sin editar la plantilla | Grupo en CLI; región y prefijo parametrizados | Compilación Bicep, archivo de ejemplo y prueba de nombres | Cumplido localmente |
| Crear Event Hubs y Blob Storage | Recursos declarados con tipos y versiones explícitas | Compilación Bicep y pruebas de recursos | Implementado; despliegue pendiente |
| Dos prefijos no producen nombres incompatibles | Prefijo parametrizado y sufijo determinista | Prueba estática y procedimiento documentado | Diseñado; prueba Azure pendiente |
| No guardar credenciales personales | Sin claves, conexiones o IDs personales; parámetros locales ignorados | Prueba de secretos y revisión del repositorio | Cumplido localmente |

## Pruebas automatizadas

| Prueba | Comportamiento comprobado |
|---|---|
| `test_azure_infrastructure_files_are_present` | Plantilla, parámetros y guía disponibles |
| `test_template_declares_required_event_hubs_resources` | Namespace, hub y dos consumidores declarados |
| `test_template_declares_private_storage_and_required_containers` | StorageV2 y tres contenedores privados |
| `test_names_are_derived_from_prefix_and_deterministic_suffix` | Nombres parametrizados sin ID guardado |
| `test_template_does_not_emit_or_enable_shared_secrets` | Autenticación local deshabilitada y ausencia de secretos |
| `test_template_exposes_names_and_endpoints_without_secrets` | Salidas necesarias para configurar la aplicación |
| `test_documentation_requires_validate_what_if_and_explicit_subscription` | Flujo operativo completo en la guía |

## Reproducción local

Desde la raíz del repositorio:

```bash
AZURE_CONFIG_DIR=/tmp/mentox-azure-cli az bicep install
AZURE_CONFIG_DIR=/tmp/mentox-azure-cli \
DOTNET_BUNDLE_EXTRACT_BASE_DIR=/tmp/mentox-dotnet-bundle \
az bicep build \
  --file infra/azure/main.bicep \
  --outfile /tmp/mentox-main.json

UV_CACHE_DIR=/tmp/mentox-uv-cache uv run \
  --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_azure_infrastructure.py -q

UV_CACHE_DIR=/tmp/mentox-uv-cache uv run \
  --project apps/backend --python 3.12 \
  pytest apps/backend/tests -q
```

## Reproducción con Azure

Los comandos completos están en `infra/azure/README.md`. La secuencia pendiente es:

```text
az login
az account set
az group create
az deployment group validate
az deployment group what-if
az deployment group create
az deployment group show
```

Los resultados deben guardarse sin tokens, IDs personales, claves ni cadenas de conexión.

## Entorno verificado

| Componente | Versión |
|---|---|
| Azure CLI | 2.88.0 |
| Bicep CLI | 0.48.1 |
| Python | 3.12.13 |
| pytest | 9.1.1 |
| API Event Hubs | 2024-01-01 |
| API Storage | 2025-06-01 |
| Suscripción Azure | No utilizada |

## Resultado

Compilación local:

```text
Bicep CLI version 0.48.1
Compilación de infra/azure/main.bicep finalizada sin errores ni advertencias.
```

Pruebas específicas:

```text
.......                                                                  [100%]
7 passed in 0.02s
```

Suite completa:

```text
..................................................                       [100%]
50 passed in 0.30s
```

## Limitaciones y riesgos

- No existe evidencia de despliegue en Azure ni de dos prefijos reales.
- La disponibilidad de tipos, cuotas y regiones se comprobará con `validate` y `what-if` en cada suscripción.
- Event Hubs y Storage pueden generar costes aunque no reciban tráfico.
- El acceso público de red está habilitado para desarrollo y debe revisarse antes de un entorno compartido.
- Las asignaciones RBAC no están automatizadas.
- `Standard_LRS`, una unidad de Event Hubs, dos particiones y un día de retención son valores iniciales de bajo alcance, no una estimación de producción.
- La región recomendada y los límites de coste continúan pendientes.
- La eliminación del grupo de recursos es irreversible.

## Dependencias y siguientes pasos

- Un integrante debe autenticarse, seleccionar su suscripción y ejecutar `validate`, `what-if` y `create`.
- La prueba debe repetirse con otro prefijo o cuenta sin editar `main.bicep`.
- DV-US-07 añadirá productor, consumidor y evidencia de Event Hubs.
- DV-US-08 conectará la selección entre memoria y Azure.
- DV-US-09 comprobará escritura y recuperación en los tres contenedores.
