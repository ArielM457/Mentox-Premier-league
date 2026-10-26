# Evidencia DV-US-32 · Generar un catálogo de partidos sintéticos con MESSI

## Estado

**Implementada y desplegada; prueba corta GPU verificada, lote de 30 pendiente.**
**Última revisión:** 25 de octubre de 2026.

Se preparó un Azure Container Apps Job para generar 30 vídeos tácticos sintéticos
con MESSI en una T4. No se afirma que el lote exista en Storage hasta ejecutar el
Job y conservar su manifiesto final.

El 25 de octubre de 2026 la imagen terminó de construirse y se publicó en ACR:

- imagen: `mentox7f7e6e99.azurecr.io/mentox/messi-generator:967b260bd6ca`;
- digest: `sha256:d299e786f0e88c61e64857b57ebb05a6504f974f6de82bb85396017a2ce92a5a`;
- Job: `job-mentox-messi-dev`;
- ejecución: `job-mentox-messi-dev-ggp9kmp`;
- inicio: `2026-10-25T22:29:40Z`;
- estado inicial observado: `Running`;
- recursos observados: 8 CPU y 56 GiB sobre el perfil T4.

La consulta de logs confirmó que JAX detectó `Tesla T4`, pero la ejecución falló
antes de generar el primer vídeo. `DefaultAzureCredential` no pudo seleccionar la
identidad administrada asignada al Job y terminó con `ClientAuthenticationError`
al consultar Blob Storage.

Se corrigió el despliegue para inyectar el `clientId` de la identidad como
`AZURE_CLIENT_ID`. El generador ahora selecciona explícitamente
`ManagedIdentityCredential(client_id=...)` cuando esa variable existe y conserva
`DefaultAzureCredential` como alternativa para ejecución local. La documentación
vigente de Azure Identity confirma que el client ID identifica una identidad
administrada asignada por el usuario. El lote no se considera generado hasta
repetir la ejecución y comprobar `Succeeded` y los 30 manifiestos.

La ejecución corregida `job-mentox-messi-dev-7r9bygm` comenzó a las
`2026-10-25T22:36:08Z`. La réplica quedó lista sin reinicios, JAX volvió a informar
`Tesla T4`, la autenticación contra Storage superó el punto que había fallado y el
generador registró `[1/30] generando messi-001`. El lote continúa en curso y aún
no se marca como verificado.

La réplica terminó después con `SIGSEGV` (`returncode -11`) durante el rollout de
`messi-001`, antes de escribir el primer MP4. La configuración usaba control a
15 Hz y render a 10 FPS. En MESSI esa diferencia activa `collect_substeps=True`
y conserva los subpasos físicos dentro del `lax.scan`; esta ruta aumenta de forma
importante el estado compilado y retenido en GPU. Se igualaron ambos valores a
15 FPS para utilizar la trayectoria de control directa y se prohibió esa diferencia
en el generador de Azure. Esta es una causa inferida del código y debe confirmarse
con una ejecución corta; no se presenta todavía como corrección verificada.

También se añadió `filelock==3.20.0` para habilitar correctamente el límite de la
caché persistente de compilación de JAX. La advertencia de caché no fue la causa
directa del `SIGSEGV`.

La prueba corta posterior usó un partido de 10 segundos, 150 pasos y frecuencias
iguales de 15 Hz/FPS. Volvió a terminar con `SIGSEGV` durante el mismo rollout.
Azure informó `ProcessExited`, no `OOMKilled`; por tanto, igualar las frecuencias
redujo la ruta de datos, pero no corrigió la causa principal.

La imagen usaba simultáneamente `nvidia/cuda:12.8.1` y `jax[cuda12]`. Esta última
instalación ya incorpora bibliotecas CUDA mediante paquetes de Python. La guía
oficial de JAX recomienda esa variante incluida y advierte que rutas del entorno
pueden hacer que se carguen bibliotecas distintas. La siguiente revisión usa
`python:3.12-slim`, deja las bibliotecas CUDA bajo control de la instalación fijada
de JAX, habilita `PYTHONFAULTHANDLER` y registra las versiones efectivas antes del
rollout. Esta corrección requiere otra prueba corta y todavía no está verificada.

La prueba `messi-preflight-clean-cuda-20261025` verificó la corrección con la
imagen `bb033679830f` y la ejecución `job-mentox-messi-dev-d7zcqww`. JAX detectó
una Tesla T4 con `jax`, `jaxlib`, `jax-cuda12-plugin` y `jax-cuda12-pjrt` 0.4.38,
sin `LD_LIBRARY_PATH` del sistema. El rollout de 150 pasos terminó en 250,5
segundos, incluida la primera compilación JIT; el render de 150 fotogramas tardó
0,9 segundos. Se produjeron y cargaron correctamente:

- un MP4 sintético de 10 segundos;
- 28 eventos en `events.jsonl`;
- 11 cuadros en `tracking.jsonl` con stride 15;
- `metadata.jsonl` y `manifest.json`;
- el manifiesto del lote.

La salida final fue `[1/1] messi-001 completo` y
`{"status":"complete","batch_id":"messi-preflight-clean-cuda-20261025","matches":1}`.
Esta comprobación aprueba la ruta técnica corta, pero no verifica todavía la
duración, costo ni estabilidad del lote de 30 vídeos de tres minutos.

## Decisión

El generador no es un servicio permanente. El Job inicia una réplica T4, procesa
el lote de forma secuencial, sube los artefactos y termina. La aplicación reproducirá
los MP4 ya creados y no invocará MESSI durante la sesión del espectador.

El valor predeterminado es un partido completo comprimido en 180 segundos. Esta
decisión permite producir un catálogo de prueba sin almacenar 2.700 minutos de
vídeo. La duración es configurable, pero un MP4 de 90 minutos por partido debe
evaluarse por separado.

## Archivos

| Archivo | Propósito |
|---|---|
| `deploy/azure-messi-generator/Dockerfile` | Imagen CUDA/JAX y MESSI fijado |
| `deploy/azure-messi-generator/generate_batch.py` | Generación, manifiestos, hashes y carga |
| `deploy/azure-messi-generator/requirements.txt` | Azure Identity y Blob Storage fijados |
| `deploy/azure-messi-generator/test_generate_batch.py` | Configuración, estilos y requisito CUDA |
| `deploy/azure-messi-generator/README.md` | Alcance, artefactos y operación |
| `infra/azure/deploy-messi-generator.sh` | ACR, identidad, RBAC, Job T4 y arranque opcional |
| `infra/azure/inspect-messi-generator.sh` | Estado de ejecuciones y artefactos |
| `infra/azure/delete-messi-generator-job.sh` | Eliminación limitada al Job después de verificar |

## Configuración predeterminada

- MESSI commit `b04b15c59d36c1e4f44e02d0886b2d0d7261f689`.
- Python 3.12.
- JAX 0.4.38 con CUDA 12.
- Perfil `Consumption-GPU-NC8as-T4`: 8 vCPU, 56 GiB y Tesla T4.
- 30 partidos.
- 180 segundos de vídeo por partido.
- Simulación y renderizado a 15 Hz/FPS para evitar la captura de subpasos físicos.
- Tracking persistido cada 15 pasos.
- Renderizado táctico `light`.
- Timeout del Job: 86.400 segundos.
- Una réplica y un reintento.

## Estructura en Blob Storage

```text
synthetic-videos/messi/<batch-id>/
├── batch-manifest.json
├── messi-001/
│   ├── match.mp4
│   ├── events.jsonl
│   ├── tracking.jsonl
│   ├── metadata.jsonl
│   └── manifest.json
└── messi-030/
```

Cada manifiesto conserva semilla, estilos, tiempos, revisión de MESSI, procedencia
sintética, tamaño y SHA-256. El manifiesto remoto sirve también como punto de
reanudación.

## Seguridad y costos

- ACR mantiene la imagen privada y sin usuario administrador.
- Una identidad administrada recibe solamente `AcrPull` y
  `Storage Blob Data Contributor` en los recursos necesarios.
- El contenedor `synthetic-videos` no permite acceso público.
- No hay ingreso HTTP ni secreto de Storage dentro de la imagen.
- El Job deja de consumir GPU cuando termina; eliminar el recurso del Job es una
  acción posterior y explícita.
- Los artefactos son sintéticos y no incluyen vídeo real de la Premier League.

## Verificación local realizada

```bash
bash -n infra/azure/deploy-messi-generator.sh
bash -n infra/azure/inspect-messi-generator.sh
bash -n infra/azure/delete-messi-generator-job.sh
python3.12 -m py_compile deploy/azure-messi-generator/generate_batch.py
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python -m unittest deploy/azure-messi-generator/test_generate_batch.py
git diff --check
```

Se inspeccionó la revisión fijada de MESSI y se verificaron sus opciones públicas
`--compressed-match`, `--render-fps`, `--state-stride`, `--out` y la producción de
`events.jsonl`, `tracking.jsonl` y `metadata.jsonl` junto al MP4.

Después de corregir la selección de identidad se repitieron `bash -n`, las cinco
pruebas unitarias con Python 3.12 y `git diff --check`; todos terminaron
correctamente.

## Verificación Azure pendiente

```bash
cd /home/university/league/Mentox-Premier-league
export MENTOX_IMAGE_BUILD_MODE=local
export MENTOX_MATCH_COUNT=30
export MENTOX_START_JOB=0
sudo -v
bash infra/azure/deploy-messi-generator.sh
```

Después de revisar la salida:

```bash
az containerapp job start \
  --resource-group rg-mentox-dev \
  --name job-mentox-messi-dev

bash infra/azure/inspect-messi-generator.sh
```

Antes de marcar la historia como verificada se debe comprobar:

1. que JAX informa un dispositivo CUDA/T4;
2. que la ejecución termina en `Succeeded`;
3. que existen 30 MP4 y 30 manifiestos completos;
4. que los hashes coinciden al descargar una muestra;
5. que un MP4 puede reproducirse mediante una URL SAS de solo lectura;
6. que una segunda ejecución omite los partidos ya completos.

### Primer intento de construcción

El primer intento real del 25 de octubre de 2026 se detuvo en la capa de
dependencias. `jaxmarl==0.0.7` incorporó `brax==0.10.3`, que a su vez necesitó
construir `pytinyrenderer==0.0.14`. La imagen no contenía el compilador
`x86_64-linux-gnu-g++`, por lo que Docker terminó con código 1 antes de publicar
la imagen o crear el Job.

Corrección aplicada: se añadió `build-essential` a la imagen. No se eliminó
`jaxmarl` porque MESSI importa `MultiAgentEnv` y `spaces` directamente desde esa
biblioteca. El fallo no inició una T4, no generó vídeos y no dejó un Job parcial.
También se mantendrá vigente la autorización de `sudo` durante construcciones
largas y la autenticación temporal de Docker se limpiará sin una segunda solicitud
de contraseña.

El segundo intento avanzó hasta compilar `pytinyrenderer`, pero Python 3.12 no
dispone de un wheel publicado para este paquete. La compilación encontró `g++` y
se detuvo porque faltaba `Python.h`. Se añadió `python3.12-dev`, que proporciona
los encabezados requeridos. También se corrigió el orden de limpieza: Docker creó
el directorio `buildx` como root, por lo que ahora se elimina con `sudo` antes de
detener el proceso que mantiene vigente la autorización.

### Primera ejecución del Job

La imagen se publicó y la ejecución `job-mentox-messi-dev-ggp9kmp` inició en la
T4. Los logs confirmaron CUDA 12.8.1 y el dispositivo `Tesla T4`. La ejecución se
detuvo antes de producir `messi-001` porque la credencial predeterminada no logró
seleccionar la identidad administrada del Job. No se publicó un manifiesto final
ni se considera completo ningún partido. Se añadió la selección explícita descrita
en la sección inicial; queda pendiente desplegar esa revisión y ejecutar nuevamente.

Después de conservar la evidencia, la eliminación explícita se limita al Job:

```bash
export MENTOX_CONFIRM_DELETE_JOB=1
bash infra/azure/delete-messi-generator-job.sh
```

## Limitaciones

- MESSI está en estado alpha y su contrato puede cambiar; por eso se fijó un commit.
- El render táctico no representa una transmisión televisiva y no valida por sí solo
  la calidad de Roboflow o SoccerNet sobre vídeo real.
- La GPU acelera la simulación JAX, pero la codificación MP4 también consume CPU.
- El tiempo y tamaño reales del lote deben medirse en Azure antes de aumentar la
  duración o la resolución.
- La adaptación de `events.jsonl` al contrato `MatchEvent 1.0` y la incorporación
  del catálogo al frontend quedan para una historia posterior.

## Documentación vigente consultada

- MESSI 0.1.0: motor JAX, `lax.scan`, ejecución CPU/GPU, render MP4 y exportación
  de repetición.
- JAX: instalación CUDA 12, caché persistente de compilación y administración de
  memoria.
- Azure Container Apps Jobs: trabajos manuales finitos y reintentables.
- Azure Blob Storage: Block Blobs para transmisión y autorización mediante identidad.
