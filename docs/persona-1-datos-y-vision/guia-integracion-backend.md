# Guía de prueba integral del backend

Esta guía ejecuta en orden el video autorizado, Roboflow Sports, SoccerNet
TeamSpotting, la fusión experimental, la API FastAPI, las pruebas y el paquete
de evidencia. No inicia ni modifica el frontend.

## Alcance real

El procedimiento comprueba el pipeline por lotes de extremo a extremo. Los
modelos procesan primero el archivo completo y después el backend expone sus
resultados sincronizados. Esto no demuestra todavía inferencia sobre una señal
en vivo. Azure es opcional y se ejecuta solo si el operador suministra sus
variables en la terminal.

GameState permanece como experimento independiente. Su salida `.pklz` aún no
tiene un adaptador hacia `VisionObservation`, por lo que no forma parte de esta
aceptación.

## Requisitos

- Linux o WSL 2.
- Docker con acceso a la GPU NVIDIA cuando se use CUDA.
- Python 3.12 administrado por `uv`.
- `ffprobe`.
- El código extraído y el video autorizado colocado en
  `experiments/authorized-video/input/2e57b9_0.mp4`.

Desde la raíz del proyecto, compruebe:

```bash
docker --version
uv --version
ffprobe -version
nvidia-smi
```

## Ejecución completa sin Azure

```bash
cd /ruta/donde/extrajo/Mentox-Premier-league

set -o pipefail
bash experiments/run-backend-integration.sh 2>&1 | \
  tee experiments/evidence-logs/backend-integration-complete.log
```

El lanzador detecta automáticamente GPU o CPU. En la computadora con RTX 3060
de 6 GB, Roboflow usa el perfil reducido configurado y TeamSpotting utiliza
precisión mixta.

La ejecución puede tardar porque construye las imágenes la primera vez. No
cierre la terminal. Un resultado correcto termina con:

```text
Integración de backend terminada correctamente.
```

## Qué ejecuta

1. Verifica metadatos y SHA-256 del video.
2. Ejecuta los tres pesos espaciales de Roboflow Sports.
3. Ejecuta SoccerNet TeamSpotting.
4. Recalcula la fusión usando exclusivamente los JSON recién producidos.
5. Comprueba las huellas de los artefactos y el fallo externo controlado.
6. Ejecuta toda la suite del backend con Python 3.12.
7. Inicia FastAPI temporalmente y consulta `/status` y `/timeline` por HTTP.
8. Genera un paquete de evidencia sin copiar el video ni secretos.

El backend debe informar `match_events_published: 0`. Las detecciones, acciones
y asociaciones visuales continúan siendo observaciones o candidatos, no hechos
deportivos confirmados.

## Revalidar sin repetir los modelos

Esta opción sirve solo cuando los JSON actuales ya fueron generados sobre el
mismo video y se desea comprobar nuevamente fusión, pruebas y API:

```bash
MENTOX_SKIP_MODELS=1 \
bash experiments/run-backend-integration.sh
```

La validación de SHA-256 impide aceptar un informe de fusión perteneciente a
otros archivos.

## Incluir Azure

Configure las credenciales únicamente en la terminal. No las escriba en un
archivo ni las incluya en las evidencias.

```bash
export EVENT_HUB_FULLY_QUALIFIED_NAMESPACE="<namespace>.servicebus.windows.net"
export EVENT_HUB_NAME="match-events"
export EVENT_HUB_CONSUMER_GROUP="diagnostics"
export VISION_EVENT_HUB_NAME="vision-observations"
export VISION_EVENT_HUB_CONSUMER_GROUP="diagnostics"
export AZURE_BLOB_SERVICE_ENDPOINT="https://<storage>.blob.core.windows.net/"
export AZURE_TENANT_ID="<tenant-id>"
export AZURE_CLIENT_ID="<client-id>"
export AZURE_CLIENT_SECRET="<secreto>"

MENTOX_RUN_AZURE=1 \
bash experiments/run-backend-integration.sh

unset AZURE_CLIENT_SECRET
```

Además del flujo local, esta variante prueba `match-events`,
`vision-observations` y Blob Storage. Una prueba de visión publica una
observación y su duplicado, pero nunca crea un `MatchEvent`.

## Probar otro video autorizado

No hace falta usar un video mayor para comprobar el encadenamiento. Si después
se desea evaluar estabilidad o rendimiento, el archivo puede cambiarse sin
editar los scripts:

```bash
MENTOX_INPUT_VIDEO="/ruta/video-autorizado.mp4" \
MENTOX_ROBOFLOW_ANNOTATIONS="/ruta/anotaciones-espaciales.csv" \
MENTOX_SOCCERNET_ANNOTATIONS="/ruta/anotaciones-temporales.csv" \
MENTOX_MEDIA_ID="muestra-autorizada-02" \
MENTOX_PERMISSION_BASIS="written_permission" \
MENTOX_PERMISSION_REFERENCE="referencia-interna-sin-secretos" \
bash experiments/run-backend-integration.sh
```

Las anotaciones deben corresponder al nuevo video. Usar las del clip de 30
segundos con otro material produciría una evaluación inválida. El video no se
incluye en el paquete final.

## Resultados que debe enviar el operador

El lanzador crea un archivo en:

```text
evidencias-generadas/mentox-modelos-<fecha>.tar.gz
```

Ese archivo incluye:

- entorno y GPU;
- logs de ambos modelos;
- JSON de predicciones;
- informe de fusión recalculado;
- aceptación del backend;
- respuesta real de los endpoints HTTP;
- pruebas locales;
- resultados de Azure, cuando se habilitaron;
- manifiesto SHA-256 con rutas relativas.

No incluye el MP4 ni las credenciales. El operador debe enviar el `.tar.gz` y
el texto final de la terminal al responsable del proyecto.

## Criterio de aprobación

La prueba se considera aprobada cuando:

- ambos modelos terminan sin excepción;
- los tres documentos comparten el SHA-256 del video;
- la fusión registra las huellas de sus dos entradas;
- toda la suite del backend aprueba;
- FastAPI responde `ready` y la consulta temporal funciona;
- ningún candidato visual se publica como `MatchEvent`;
- el paquete de evidencia se genera sin video ni secretos.

Una cantidad alta de detecciones no demuestra precisión. Calidad, recobrado y
F1 requieren anotaciones manuales representativas y se informan por separado.
