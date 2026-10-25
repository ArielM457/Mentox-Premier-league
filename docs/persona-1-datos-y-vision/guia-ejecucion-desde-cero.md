# Guía para ejecutar Mentox desde cero en Ubuntu

Esta guía está dirigida a una persona que tiene VS Code, pero todavía no conoce
Git, Python, Docker ni la terminal. Permite preparar una computadora NVIDIA,
ejecutar los modelos y abrir la interfaz técnica de Mentox.

La persona que recibe el ZIP para aportar su GPU debe probar **solo los
modelos**. Para esa tarea debe completar las secciones 3 a 9, omitir la sección
10 porque ya recibió el ZIP, continuar con las secciones 11 a 14, después la
sección 19 y finalmente la sección 22. Puede omitir fusión, interfaz y Azure de
las secciones 15 a 18, 20 y 21.

La guía supone **Ubuntu 22.04 o 24.04 de 64 bits**. No copie estos comandos en
Windows o macOS: esos sistemas necesitan instrucciones diferentes.

## 1. Qué se ejecutará

El recorrido completo hace lo siguiente:

1. Roboflow localiza participantes, balón y puntos clave del campo.
2. SoccerNet TeamSpotting propone acciones como pases, conducciones y tiros.
3. Mentox relaciona observaciones compatibles sin convertirlas automáticamente en hechos.
4. La interfaz reproduce el vídeo y muestra las observaciones al pulsar **Play**.

SoccerNet GameState se prueba por separado. Todavía no aparece en la interfaz
porque su salida necesita un adaptador adicional.

El proyecto conserva dos vídeos de prueba diferentes:

- El vídeo sintético de Google Research Football se usó en las primeras
  comprobaciones controladas.
- El vídeo `2e57b9_0.mp4` del ejemplo oficial de Roboflow Sports se usa en los
  comandos `run-real.sh` de esta guía. Es la muestra real autorizada sobre la
  que ya se probaron Roboflow y TeamSpotting.

## 2. Requisitos de la computadora

Se recomienda:

- Ubuntu 22.04 o 24.04.
- 16 GB de RAM como mínimo; 32 GB recomendados.
- GPU NVIDIA con 6 GB de VRAM para Roboflow y TeamSpotting; 12 GB o más se
  recomiendan para GameState.
- Al menos 60 GB libres en disco.
- Internet estable, VS Code y acceso autorizado al repositorio.
- Una copia autorizada del vídeo de prueba.

La primera ejecución puede tardar bastante porque descarga imágenes Docker,
dependencias y pesos. Las siguientes ejecuciones reutilizan la caché.

## 3. Primero: extraer el ZIP y entrar al proyecto

1. Guarde `Mentox-Premier-league.zip` en **Descargas**.
2. Pulse el archivo con el botón derecho y seleccione **Extraer aquí**.
3. Abra VS Code y seleccione **Archivo → Abrir carpeta**.
4. Abra la carpeta extraída `Mentox-Premier-league` o
   `Mentox-Premier-league-main`.
5. Seleccione **Terminal → Nueva terminal**.

En la terminal, entre directamente a la carpeta que corresponda:

```bash
cd "$HOME/Descargas/Mentox-Premier-league"
```

Si la carpeta termina en `-main`, utilice:

```bash
cd "$HOME/Descargas/Mentox-Premier-league-main"
```

Compruebe que está en el lugar correcto:

```bash
pwd
test -f compose.integration.yml && echo "Carpeta correcta"
```

Debe aparecer `Carpeta correcta`. Todos los comandos de las siguientes
secciones deben ejecutarse desde ese directorio. No ejecute archivos directamente
dentro del ZIP sin extraerlos.

## 4. Abrir una terminal en VS Code

1. Abra VS Code.
2. Seleccione **Terminal → New Terminal** o **Nueva terminal**.
3. Copie cada bloque de esta guía en la terminal y pulse **Enter**.

Si aparece `[sudo] password`, escriba la contraseña de Ubuntu. No se verá en la
pantalla mientras escribe; es normal.

## 5. Instalar herramientas básicas

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git curl ca-certificates gnupg ffmpeg jq build-essential unzip
```

Compruebe:

```bash
git --version
curl --version
ffmpeg -version
```

Los tres comandos deben mostrar una versión.

## 6. Instalar el controlador NVIDIA

1. Abra **Software & Updates** o **Software y actualizaciones**.
2. Entre en **Additional Drivers** o **Controladores adicionales**.
3. Seleccione el controlador NVIDIA marcado como recomendado.
4. Pulse **Apply Changes** y reinicie la computadora.

Después del reinicio:

```bash
nvidia-smi
```

Debe aparecer una tabla con nombre de GPU, memoria y controlador. Si falla, no
continúe con los modelos GPU hasta corregir el controlador.

## 7. Instalar Docker Engine y Compose

Los modelos usan contenedores para evitar conflictos entre Python y PyTorch.

Añada el repositorio oficial:

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

Ejecute el bloque completo:

```bash
. /etc/os-release
docker_codename="${UBUNTU_CODENAME:-$VERSION_CODENAME}"
docker_architecture="$(dpkg --print-architecture)"

echo "Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${docker_codename}
Components: stable
Architectures: ${docker_architecture}
Signed-By: /etc/apt/keyrings/docker.asc" | \
  sudo tee /etc/apt/sources.list.d/docker.sources
```

Instale y compruebe:

```bash
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin

sudo systemctl status docker --no-pager
sudo docker run --rm hello-world
sudo docker compose version
```

`hello-world` debe mostrar un mensaje de instalación correcta.

## 8. Instalar NVIDIA Container Toolkit

El controlador permite que Ubuntu use la GPU. Este toolkit permite que Docker
también pueda verla.

```bash
sudo apt-get update
sudo apt-get install -y --no-install-recommends ca-certificates curl gnupg2

curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor \
  -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L \
  https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Compruebe Docker con GPU:

```bash
sudo docker run --rm --gpus all \
  nvidia/cuda:12.4.1-base-ubuntu22.04 \
  nvidia-smi
```

Debe aparecer una tabla similar a la de `nvidia-smi` fuera de Docker.

## 9. Instalar uv y Python 3.12

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Cierre y vuelva a abrir la terminal de VS Code. Después:

```bash
uv --version
uv python install 3.12
uv python list
```

La lista debe contener Python 3.12. No es necesario crear manualmente un entorno
virtual: `uv` lo administra.

## 10. Alternativa: descargar el proyecto con Git

Esta alternativa solo se necesita si no recibió el ZIP:

```bash
mkdir -p "$HOME/league"
cd "$HOME/league"
git clone https://github.com/ArielM457/Mentox-Premier-league.git
cd Mentox-Premier-league
code .
```

Si GitHub solicita autenticación, la cuenta necesita acceso al repositorio. Use
el inicio de sesión de GitHub de VS Code o un token autorizado; no use la
contraseña normal de GitHub. Si `code` no existe, abra VS Code manualmente y
seleccione **File → Open Folder**.

Si utilizó Git, abra una terminal nueva y compruebe:

```bash
pwd
git status
```

`pwd` debe terminar en `/Mentox-Premier-league`.

## 11. Instalar y probar el backend

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv sync --project apps/backend --python 3.12 --extra dev

UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest apps/backend/tests -q
```

Todas las pruebas deben aprobar. Un resultado parecido a `161 passed` es
correcto; el número puede aumentar en versiones futuras.

## 12. Colocar el vídeo autorizado

El vídeo no está en Git. Un responsable debe entregarlo por un canal autorizado.
No descargue ni comparta partidos de la Premier League sin permiso.

El archivo utilizado actualmente se llama `2e57b9_0.mp4` y corresponde al vídeo
de demostración usado por el ejemplo oficial de Roboflow Sports. No es el vídeo
sintético de Google Research Football. Cree la carpeta:

```bash
mkdir -p experiments/authorized-video/input
```

Copie el archivo con el explorador de VS Code a:

```text
experiments/authorized-video/input/2e57b9_0.mp4
```

Compruebe:

```bash
ls -lh experiments/authorized-video/input/2e57b9_0.mp4

ffprobe -v error \
  -show_entries format=duration,size \
  -show_entries stream=codec_name,width,height,r_frame_rate \
  -of json \
  experiments/authorized-video/input/2e57b9_0.mp4
```

La muestra conocida dura 30 segundos, usa H.264, mide 1920 × 1080 y tiene 25
cuadros por segundo.

## 13. Ejecutar Roboflow con GPU

```bash
mkdir -p experiments/evidence-logs
set -o pipefail
bash experiments/roboflow-sports/run-real.sh 2>&1 | \
  tee experiments/evidence-logs/roboflow-gpu.log
```

El script detecta la VRAM. Con una GPU de 6 GB selecciona automáticamente 640
px, FP16 y procesa los puntos del campo cada 10 cuadros. No hace falta copiar
variables adicionales.

No cierre la terminal durante la primera construcción. Al terminar:

```bash
ls -lh experiments/roboflow-sports/output-real/
```

Deben existir:

```text
roboflow-sports-predictions.json
roboflow-sports-evaluation-input.json
roboflow-sports-annotated.mp4
```

Abra el vídeo anotado:

```bash
xdg-open experiments/roboflow-sports/output-real/roboflow-sports-annotated.mp4
```

Si aun así aparece `CUDA out of memory`, cierre programas que usen la GPU y
repita el mismo comando. Como último recurso, ejecute solo jugadores y balón:

```bash
MENTOX_CUDA_DEVICE=0 \
MENTOX_VISION_MODELS=player,ball \
bash experiments/roboflow-sports/run-real.sh
```

## 14. Ejecutar TeamSpotting con GPU

```bash
set -o pipefail
bash experiments/soccernet-teamspotting/run-real.sh 2>&1 | \
  tee experiments/evidence-logs/teamspotting-gpu.log
```

El script activa precisión mixta automáticamente para reducir el uso de VRAM.

Compruebe:

```bash
ls -lh experiments/soccernet-teamspotting/output-real/
jq '.predictions | length' \
  experiments/soccernet-teamspotting/output-real/soccernet-predictions.json
```

Debe existir `soccernet-predictions.json`. El conteo no significa que todas las
acciones sean correctas; siguen siendo observaciones experimentales.

Si hay errores numéricos, repita sin precisión mixta:

```bash
MENTOX_CUDA_DEVICE=0 MENTOX_CUDA_AMP=0 \
bash experiments/soccernet-teamspotting/run-real.sh
```

## 15. Calcular candidatos de fusión

Esta sección no corresponde a la persona encargada únicamente de probar los
modelos. El responsable de la integración la ejecutará después con los JSON
recibidos.

Después de Roboflow y TeamSpotting:

```bash
set -o pipefail
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/calibrate_observation_fusion.py \
  experiments/roboflow-sports/output-real/roboflow-sports-predictions.json \
  experiments/soccernet-teamspotting/output-real/soccernet-predictions.json \
  --output experiments/fusion-calibration/output/dv-us-21-report.json 2>&1 | \
  tee experiments/evidence-logs/fusion.log
```

Compruebe:

```bash
ls -lh experiments/fusion-calibration/output/dv-us-21-report.json
jq '.decision, .selected_result.candidates' \
  experiments/fusion-calibration/output/dv-us-21-report.json
```

La decisión esperada es `experimental_candidates_only`. Un candidato no es un
evento deportivo confirmado.

## 16. Abrir backend e interfaz técnica

Esta sección no corresponde a la prueba de modelos en la computadora GPU.

```bash
sudo docker compose -f compose.integration.yml up --build
```

Espere hasta ver mensajes similares a:

```text
Application startup complete
Uvicorn running on http://0.0.0.0:8018
```

No cierre esa terminal. Abra en el navegador:

```text
http://127.0.0.1:8018
```

Si no abre, use otra terminal:

```bash
sudo docker compose -f compose.integration.yml ps
sudo docker compose -f compose.integration.yml logs --tail=100
```

## 17. Verificar la interfaz

Esta sección no corresponde a la prueba de modelos en la computadora GPU.

1. Confirme que el backend aparece conectado.
2. Antes de pulsar **Play**, el canal debe estar vacío.
3. Pulse **Play**.
4. Deben aparecer gradualmente observaciones de Roboflow y SoccerNet.
5. Pulse **Pause** y confirme que dejan de aparecer observaciones futuras.
6. Avance el vídeo; el historial no debe mostrarse como nuevo.
7. Pulse **Reiniciar**; tiempo, cursor y panel deben volver a cero.
8. Exporte el registro JSON si necesita conservar evidencia.

La UI reproduce observaciones calculadas previamente. No ejecuta nuevamente los
modelos durante la reproducción.

## 18. Detener el proyecto

Esta sección solo se utiliza si se abrió la interfaz con Compose.

En la terminal de Compose pulse `Ctrl+C`. Después:

```bash
sudo docker compose -f compose.integration.yml down
```

Esto detiene el servicio, pero conserva imágenes, modelos y resultados locales.

## 19. Ejecutar SoccerNet GameState

GameState se prueba aparte y todavía no alimenta la UI. Compruebe CUDA 11.7:

El dataset SoccerNet GSR y los pesos no vienen dentro del ZIP. Según la guía
oficial, TrackLab los descarga automáticamente durante la primera ejecución y
los conserva en `experiments/soccernet-gamestate/data/SoccerNetGS/` y
`experiments/soccernet-gamestate/models/`. Por eso la carpeta puede estar vacía
antes de comenzar. Se necesita internet y varios GB libres. Si aparece una
solicitud de acceso, utilice solamente una cuenta autorizada y no comparta su
token.

```bash
sudo docker run --rm --gpus all \
  nvidia/cuda:11.7.1-base-ubuntu22.04 \
  nvidia-smi
```

Ejecute el smoke automático:

```bash
set -o pipefail
bash experiments/soccernet-gamestate/run.sh 2>&1 | \
  tee experiments/evidence-logs/gamestate-gpu.log
```

Con una GPU de 6 GB, el script limita la prueba a 100 cuadros y reduce los lotes
de detección, ReID, tracking, calibración y dorsal. GameState carga varios
módulos y todavía podría quedarse sin memoria; ese resultado no afecta a
Roboflow, TeamSpotting ni a la interfaz integrada.

La primera ejecución puede descargar varios GB. Al terminar:

```bash
ls -lh experiments/soccernet-gamestate/output/
find experiments/soccernet-gamestate/output/run -maxdepth 4 -type f
```

Resultados esperados:

```text
experiments/soccernet-gamestate/output/sn-gamestate.pklz
experiments/soccernet-gamestate/output/run/
```

GameState no aparecerá todavía en `http://127.0.0.1:8018`. Primero debe
comprobarse la salida real y crear el exportador desde `.pklz` hacia JSON.

## 20. Ejecutar la interfaz sin Docker

Esta sección no corresponde a la prueba de modelos en la computadora GPU.

Esta opción requiere el vídeo y las salidas de los modelos:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  uvicorn video_sync_diagnostic.app:app \
  --app-dir experiments \
  --host 127.0.0.1 \
  --port 8018
```

Abra `http://127.0.0.1:8018`. Para detenerla pulse `Ctrl+C`.

## 21. Azure Event Hubs opcional

Esta sección no corresponde a la prueba de modelos en la computadora GPU.

La primera prueba debe usar el transporte local predeterminado. Azure no es
necesario para abrir la UI.

Si el responsable entrega una identidad autorizada, configure las variables
solo en la terminal. Nunca las guarde en Git, capturas o documentos:

```bash
export VISION_OBSERVATION_TRANSPORT=azure_event_hubs
export EVENT_HUB_FULLY_QUALIFIED_NAMESPACE="<namespace>.servicebus.windows.net"
export VISION_EVENT_HUB_NAME="vision-observations"
export VISION_EVENT_HUB_CONSUMER_GROUP="backend"
export AZURE_TENANT_ID="<tenant-id>"
export AZURE_CLIENT_ID="<client-id>"
export AZURE_CLIENT_SECRET="<secreto>"
```

```bash
sudo --preserve-env=VISION_OBSERVATION_TRANSPORT,EVENT_HUB_FULLY_QUALIFIED_NAMESPACE,VISION_EVENT_HUB_NAME,VISION_EVENT_HUB_CONSUMER_GROUP,AZURE_TENANT_ID,AZURE_CLIENT_ID,AZURE_CLIENT_SECRET \
  docker compose -f compose.integration.yml up --build
```

Al terminar:

```bash
unset AZURE_CLIENT_SECRET
```

## 22. Preparar las evidencias para enviarlas

No hace falta subir nada con Git. Al terminar las pruebas, la persona debe
enviarle al responsable los resultados técnicos generados por los modelos.

Luego ejecute desde la raíz del proyecto:

```bash
bash experiments/collect-model-evidence.sh
```

El comando mostrará una ruta parecida a:

```text
evidencias-generadas/mentox-modelos-20261023T220000Z.tar.gz
```

Ese archivo `.tar.gz` es el que debe enviar al responsable. Contiene:

- Nombre, VRAM y controlador de la GPU.
- Versiones de Docker, Compose y `uv`.
- Huella SHA-256 del vídeo, pero no el vídeo.
- Log completo de Roboflow, TeamSpotting y GameState si se ejecutó.
- Predicciones JSON de Roboflow y TeamSpotting.
- Huellas SHA-256 para comprobar que los archivos no cambiaron.

No incluye el vídeo autorizado, el vídeo anotado, pesos de modelos, secretos de
Azure ni tokens. Si una prueba falla, debe ejecutar igualmente el recolector:
el archivo `.log` del error también es una evidencia útil.

Además del `.tar.gz`, la persona debe informar por mensaje:

1. Si cada comando terminó correctamente o con error.
2. Si pudo abrir el vídeo anotado de Roboflow.
3. Qué detectó visualmente Roboflow: jugadores, árbitros, balón y puntos del
   campo; también debe mencionar detecciones claramente incorrectas.
4. Si GameState generó su visualización o falló por memoria.
5. Si observó bloqueos, reinicios o falta de memoria.

Debe adjuntar una captura del vídeo anotado de Roboflow. Si GameState termina,
también debe adjuntar una captura de su visualización. Estas son salidas de los
modelos, no capturas de la interfaz de Mentox. No necesita abrir la UI, ejecutar
Compose, conectarse a Azure ni exportar el registro de sesión.

## 23. Problemas frecuentes

### `uv: command not found`

Cierre y abra la terminal. Si continúa:

```bash
source "$HOME/.local/bin/env"
uv --version
```

### Docker responde `permission denied`

Use `sudo docker ...`, como en esta guía.

### Docker no encuentra la GPU

```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
nvidia-smi
```

Después repita la prueba NVIDIA dentro de Docker.

### La interfaz indica que faltan archivos

```bash
ls experiments/authorized-video/input/2e57b9_0.mp4
ls experiments/roboflow-sports/output-real/roboflow-sports-predictions.json
ls experiments/soccernet-teamspotting/output-real/soccernet-predictions.json
ls experiments/fusion-calibration/output/dv-us-21-report.json
```

Ejecute la sección correspondiente al archivo ausente.

### El puerto 8018 está ocupado

```bash
sudo docker compose -f compose.integration.yml down
sudo ss -ltnp | grep 8018
```

### Aparece `ContainerConfig`

Ese error suele pertenecer a `docker-compose` 1.x. Use Compose v2:

```bash
sudo docker compose version
```

El comando correcto contiene un espacio: `docker compose`.

## 24. Información que nunca debe compartirse

No publique ni confirme en Git:

- Secretos de Azure.
- Tokens de GitHub o Hugging Face.
- Cadenas de conexión.
- Vídeos sin autorización.
- Pesos sin permiso de redistribución.
- Archivos de salida grandes.

La persona que recibió el ZIP no necesita crear commits ni ejecutar `git push`.

## 25. Lista final de comprobación

Para la persona que prueba únicamente los modelos:

- [ ] `nvidia-smi` funciona en Ubuntu.
- [ ] Docker ejecuta `hello-world`.
- [ ] Docker ve la GPU.
- [ ] `uv` y Python 3.12 funcionan.
- [ ] Las pruebas del backend aprueban.
- [ ] El vídeo autorizado está en la ruta exacta.
- [ ] Roboflow produjo JSON y vídeo anotado.
- [ ] TeamSpotting produjo su JSON.
- [ ] GameState se probó por separado si existen recursos suficientes.
- [ ] Se creó y envió el paquete de evidencias `.tar.gz`.
- [ ] Se adjuntó una captura del resultado visual de Roboflow.

Las siguientes comprobaciones corresponden al responsable de la integración,
no a la persona que presta la computadora GPU:

- [ ] La fusión produjo `dv-us-21-report.json`.
- [ ] Compose inicia sin errores.
- [ ] `http://127.0.0.1:8018` abre.
- [ ] No hay observaciones antes de Play.
- [ ] Play, pausa, salto y reinicio funcionan.

## Fuentes oficiales

- Docker: `https://docs.docker.com/engine/install/ubuntu/`
- NVIDIA Container Toolkit: `https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html`
- uv: `https://docs.astral.sh/uv/getting-started/installation/`
- GameState: `https://github.com/SoccerNet/sn-gamestate`
- TeamSpotting: `https://github.com/SoccerNet/sn-teamspotting`
- Roboflow Sports: `https://github.com/roboflow/sports`
