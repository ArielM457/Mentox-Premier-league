# Evidencia DV-US-30 · Desplegar el primer detector en una GPU de Azure

## Estado

**Implementada y verificada en Azure con GPU T4.**  
**Última revisión:** 25 de octubre de 2026.

La imagen, la API y el script están desplegados en `northcentralus`. La aplicación procesó un fotograma autorizado en una Tesla T4 y volvió a escala cero después de la prueba.

El 25 de octubre de 2026 se ejecutó el script contra la suscripción `Azure for Students` y `westus3`. Azure confirmó que la región anuncia `Consumption-GPU-NC8as-T4`, pero rechazó la creación inicial del ACR mediante `RequestDisallowedByAzure`: la política de la suscripción no permite desplegar en esa región. El script se detuvo antes de construir la imagen o crear recursos del modelo.

## Alcance implementado

- Un solo peso: `football-player-detection.pt`.
- API FastAPI con Python 3.12 y una réplica Uvicorn.
- Inicio obligatorio con CUDA y calentamiento previo.
- Inferencia FP16 protegida por un bloqueo para no saturar la única GPU.
- Imágenes JPEG, PNG o WebP de hasta 15 MiB.
- Respuesta con clase, confianza, caja normalizada y duración.
- Autorización temporal mediante `X-API-Key` almacenada como secreto de Container Apps.
- Imagen privada en ACR sin usuario administrador.
- Identidad administrada con `AcrPull`.
- Perfil `Consumption-GPU-NC8as-T4`, 8 vCPU, 56 GiB, mínimo cero y máximo uno.

## Fuera del alcance

- Procesamiento de vídeo completo o transmisión por segmentos.
- Detector especializado del balón, puntos clave del campo, TeamSpotting y GameState.
- Integración del endpoint con el backend oficial.
- Autenticación Microsoft Entra y redes privadas de producción.
- Confirmación de cuota, región, costo o latencia en Azure.

## Archivos

| Archivo | Propósito |
|---|---|
| `deploy/azure-roboflow-player/app.py` | API de salud y predicción sobre una imagen |
| `deploy/azure-roboflow-player/Dockerfile` | Imagen CUDA no root con Python 3.12 y peso verificado |
| `deploy/azure-roboflow-player/requirements.txt` | Dependencias fijadas de la API |
| `deploy/azure-roboflow-player/README.md` | Operación, seguridad, encendido y apagado |
| `infra/azure/deploy-roboflow-player.sh` | Preflight, ACR, identidad, perfil GPU y Container App |

## Decisiones

1. Se comienza con el detector general porque entrega el primer valor espacial y permite medir la T4 sin mezclar consumos.
2. El contenedor permanece con un solo modelo hasta disponer de latencia, VRAM máxima y costo de esta referencia.
3. El modelo se carga al iniciar la réplica y se calienta con una imagen vacía para retirar ese costo de la primera medición funcional.
4. Se limita la concurrencia dentro del proceso porque una T4 es un recurso compartido por todas las solicitudes de la réplica.
5. La imagen se construye en ACR para no exigir Docker local.
6. El script no continúa sin una aceptación explícita de las condiciones de los componentes y pesos.

## Matriz de criterios

| Criterio | Implementación | Comprobación |
|---|---|---|
| Un peso con integridad | Descarga fijada y SHA-256 esperado en Dockerfile | Construcción real aprobada; imagen publicada con digest registrado |
| Carga única y calentamiento | `lifespan`, `YOLO(...)` y predicción de calentamiento | `/health/ready` confirmó carga en Tesla T4 |
| Entrada y salida acotadas | Tipo MIME, 15 MiB, decodificación y cajas normalizadas | Revisión y compilación local |
| Secreto fuera de Git | `MENTOX_MODEL_API_KEY` y secreto `model-api-key` | Búsqueda de secretos y sintaxis Bash |
| ACR privado e identidad | Admin deshabilitado, identidad y rol `AcrPull` | Imagen extraída y aplicación iniciada en Azure |
| Escalado controlado | Valores predeterminados 0–1 | Confirmado mínimo 0, máximo 1 y réplica `NotRunning` tras la prueba |
| Preflight | Cuenta, proveedores, perfil regional y variables obligatorias | Ejecución sin despliegue hasta las validaciones locales |

## Comandos de verificación local

```bash
bash -n infra/azure/deploy-roboflow-player.sh
python3.12 -m py_compile deploy/azure-roboflow-player/app.py
docker build --check \
  --file deploy/azure-roboflow-player/Dockerfile \
  deploy/azure-roboflow-player
git diff --check
```

## Comando reproducible de despliegue

```bash
export MENTOX_AZURE_RESOURCE_GROUP="rg-mentox-dev"
export MENTOX_AZURE_LOCATION="northcentralus"
export MENTOX_MODEL_API_KEY="$(openssl rand -hex 32)"
export MENTOX_ACCEPT_MODEL_LICENSES=1
export MENTOX_IMAGE_BUILD_MODE=local

bash infra/azure/deploy-roboflow-player.sh
```

## Versiones fijadas

- Python 3.12.
- CUDA 12.8.1 y cuDNN runtime.
- PyTorch 2.7.1 y Torchvision 0.22.1, índice CUDA 12.8.
- Ultralytics 8.4.177.
- FastAPI 0.115.6.
- Uvicorn 0.34.0.
- Azure CLI y extensión Container Apps: se actualizan y comprueban en el entorno del operador.

## Documentación vigente consultada

- Azure Container Apps serverless GPU: perfil de consumo, escala a cero, facturación por segundo y requisito de cuota.
- Azure Container Apps GPU image generation: adición de perfil T4 y recursos de 8 vCPU y 56 GiB.
- Azure Container Registry con identidad administrada: rol `AcrPull` en registros sin ABAC.
- PyTorch 2.7: compatibilidad con Python 3.12 y variante CUDA 12.8.
- Context7 confirmó la sintaxis vigente de `az containerapp create`, `az containerapp env workload-profile add` y `list-supported`.
- Azure MCP confirmó la suscripción activa `Azure for Students`; su consulta genérica de cuota no expuso un contador T4 utilizable, por lo que la autorización final solo puede confirmarse al crear el entorno o mediante una concesión de cuota en Azure.
- Azure CLI `2.88.0` con extensión `containerapp 1.3.0b5` confirmó `Consumption-GPU-NC8as-T4` en `westus3`. La extensión disponible es preliminar.

## Limitaciones y riesgos

- Una región compatible puede seguir rechazando el despliegue por cuota o política de Azure for Students.
- La política `sys.regionrestriction` permite `northcentralus`, `chilecentral`, `canadacentral`, `eastus2` y `centralus`. Al cruzarlas con los perfiles publicados por Container Apps, `northcentralus` y `canadacentral` anuncian `Consumption-GPU-NC8as-T4`. Se seleccionó `northcentralus` como valor predeterminado; esto no garantiza que Azure for Students conceda cuota.
- Escalar a cero introduce arranque en frío por imagen, CUDA y peso.
- Incluir otro modelo puede aumentar VRAM y latencia aunque todavía quede memoria libre.
- La clave de API es suficiente para la demostración, no para producción pública.
- La licencia separada del peso no está declarada claramente en el repositorio oficial; debe revisarse antes de redistribuir la imagen.
- El SHA-256 corresponde al peso usado en la evidencia local; una descarga distinta detendrá deliberadamente la construcción.

## Intento real de despliegue del 25 de octubre de 2026

1. Suscripción activa: `Azure for Students`, estado `Enabled`.
2. Azure CLI confirmó el perfil `Consumption-GPU-NC8as-T4` en `westus3`.
3. El despliegue se detuvo al intentar crear el ACR privado `mentox7f7e6e99`.
4. Código: `RequestDisallowedByAzure`.
5. Causa: política de regiones permitidas de la suscripción.
6. Verificación posterior: no existen el ACR, la identidad `id-mentox-player-dev`, el entorno `cae-mentox-vision-dev` ni la aplicación `ca-mentox-player-dev`.
7. Resultado económico: el intento no dejó recursos nuevos facturables.

El rechazo de `westus3` quedó resuelto al seleccionar una región que cumple simultáneamente la política de la suscripción y la disponibilidad del perfil T4.

Una revisión posterior de la asignación `sys.regionrestriction` encontró dos regiones que cumplen ambos requisitos: `northcentralus` y `canadacentral`. Se eligió `northcentralus` y Azure aceptó la creación del perfil T4.

El primer intento en `northcentralus` también fue rechazado antes de crear recursos porque ACR e identidad no declaraban ubicación y heredaban `eastus` del grupo `rg-mentox-dev`. Como `eastus` no está permitida por `sys.regionrestriction`, se corrigió el script para enviar `--location "${location}"` explícitamente al crear ambos recursos.

Después de corregir la ubicación, Azure creó el ACR privado en `northcentralus`, pero `az acr build` no encontró `Dockerfile` porque la opción `--file` usaba una ruta relativa al directorio de ejecución. Se corrigió a la ruta absoluta dentro de `deploy/azure-roboflow-player/`. El siguiente intento reutiliza el mismo ACR.

Con la ruta corregida, Azure for Students rechazó la construcción remota mediante `TasksOperationsNotAllowed`. Se agregó `MENTOX_IMAGE_BUILD_MODE=local`: obtiene un token temporal con `az acr login --expose-token`, utiliza una configuración Docker efímera, construye y sube con `sudo docker`, cierra la sesión del registro y elimina la configuración temporal. No se almacena el token en el repositorio.

La primera construcción local descargó las imágenes base, pero Ubuntu 24.04 rechazó `uv pip install --system` por PEP 668 (`externally managed`). Siguiendo la documentación vigente de `uv`, el Dockerfile ahora crea `/opt/venv`, instala las dependencias en ese entorno sin `--system` y ejecuta Uvicorn con su intérprete. También se corrigió la limpieza de la configuración efímera con `sudo rm`, porque Docker había creado `buildx` como `root`.

La segunda construcción alcanzó la descarga de PyTorch CUDA, pero `uv` agotó su tiempo de lectura predeterminado de 30 segundos al extraer `nvidia-cusolver-cu12`. Se aumentó `UV_HTTP_TIMEOUT` a 300 segundos, se habilitó una caché BuildKit para `uv` y se separaron PyTorch, dependencias de la API y descarga del peso en capas distintas. Esto conserva las capas completadas si una etapa posterior falla.

La tercera construcción local terminó y publicó `mentox/roboflow-player:da1950640b77` en el ACR privado con digest `sha256:1102767ab24b3e1afdeab1c98725d6e206f4e7124b6ccca20b81e70105268bba`. El proceso se detuvo antes de crear el entorno porque la suscripción no tenía registrado `Microsoft.OperationalInsights`, requerido por los registros predeterminados de Container Apps. Se agregó su registro obligatorio al preflight.

`Microsoft.OperationalInsights` quedó `Registered`. Se agregó el modo `MENTOX_IMAGE_BUILD_MODE=existing`, que verifica la etiqueta del commit en ACR y permite reanudar el aprovisionamiento sin reconstruir ni volver a subir la imagen.

Azure CLI `containerapp 1.3.0b5` creó el entorno con perfil `Consumption` en modo Express pese a recibir `--enable-workload-profiles`; Express rechazó T4 mediante `ExpressEnvironmentFeatureNotSupported`. La ayuda vigente de la CLI indica `--environment-mode WorkloadProfiles`. El script ahora usa ese parámetro y `--logs-destination none` para evitar crear y facturar un espacio de Log Analytics en esta prueba.

## Verificación real en GPU del 25 de octubre de 2026

- Región: `northcentralus`.
- Entorno: `cae-mentox-vision-dev`, modo `WorkloadProfiles`.
- Perfil: `NC8as-T4`, tipo `Consumption-GPU-NC8as-T4`.
- Aplicación: `ca-mentox-player-dev`.
- Imagen: `mentox7f7e6e99.azurecr.io/mentox/roboflow-player:da1950640b77`.
- Digest: `sha256:1102767ab24b3e1afdeab1c98725d6e206f4e7124b6ccca20b81e70105268bba`.
- Dispositivo informado por PyTorch: `Tesla T4`.
- Entrada autorizada: fotograma 1920 × 1080 extraído en el segundo 10 de `2e57b9_0.mp4`.
- Inferencia: `115.705 ms`.
- Resultado: 21 detecciones; 18 jugadores, 2 árbitros y 1 balón.
- Confianza del balón: `0.65478515625`.
- Salud: `/health/ready` respondió `ready`.
- Seguridad: `/v1/predict` rechazó una clave anterior con HTTP 401 y aceptó la clave aplicada tras reiniciar la revisión.
- Escala posterior: mínimo `0`, máximo `1`; la réplica de la revisión `ca-mentox-player-dev--0000004` quedó `NotRunning`.
- Log Analytics: deshabilitado para esta prueba; el workspace autogenerado durante el intento Express fue eliminado.

## Evidencia necesaria para verificar en Azure

1. Salida de región y perfil soportado.
2. Identificador de imagen en ACR sin secretos.
3. Revisión activa y réplica GPU lista.
4. Respuesta de `/health/ready`.
5. Predicción sobre un fotograma autorizado.
6. Nombre de GPU, latencia, VRAM máxima y costo observado.
7. Confirmación de mínimo cero después de la prueba.
