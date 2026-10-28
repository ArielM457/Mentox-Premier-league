# SoccerNet GameState en Azure GPU

## Retirado de la demo MESSI

El 27 de octubre de 2026 el usuario decidió no usar GameState en la demo.
La aplicación `ca-mentox-gamestate-dev` fue eliminada de Azure. Este paquete
se conserva como investigación; las instrucciones siguientes son históricas
y no deben ejecutarse para el flujo actual sin una nueva decisión de despliegue.
La demo se orienta a Roboflow, TeamSpotting y datos del mismo partido simulado,
con procedencia separada. [Evidencia del retiro](../../docs/persona-1-datos-y-vision/evidencias/gamestate-retiro-20261027.md).

Este paquete despliega el baseline de SoccerNet Game State Reconstruction como
un servicio experimental de The Prime Moment. Recibe un MP4 sintético o
autorizado y produce observaciones JSONL con seguimiento, rol, equipo, dorsal,
caja de imagen y posición calibrada cuando el modelo puede obtenerlas.

## Condiciones y límites

- `SoccerNet/sn-gamestate` está fijado al commit
  `1c958345067218297d221e45e1a6405f975f83e0` y usa GPL-3.0.
- TrackLab está fijado a la versión 1.3.24.
- Los pesos y datos descargados por el pipeline conservan sus propias
  condiciones. Revise y acepte las condiciones oficiales antes del despliegue.
- No incluya videos reales sin autorización ni datos de la Premier League.
- Un dorsal es una observación estimada. No se convierte automáticamente en
  el nombre de un jugador.
- La prueba T4 completa del 27 de octubre terminó sin errores sobre un MP4 MESSI
  de 180 segundos, pero produjo solo 4 detecciones y ninguna posición calibrada.
  Su calidad no permite seguimiento ni métricas fiables en ese vídeo. Véase la
  [evidencia de ejecución y calidad](../../docs/persona-1-datos-y-vision/evidencias/gamestate-parche-validacion-20261027-7uTJjl/README.md).
- Que el contenedor se construya o termine un análisis no demuestra precisión.

## Por qué la API es asíncrona

GameState ejecuta detección, ReID, tracking, calibración, clasificación de
equipo y OCR. Un análisis puede tardar más que el límite de una solicitud HTTP.
La API crea un trabajo dentro de la única réplica y devuelve inmediatamente un
`analysis_id`. Después se consulta el estado y se descarga el JSONL.

Solo se procesa un video a la vez. Los resultados viven en el disco efímero de
la réplica; descárguelos antes de apagarla. Una versión posterior podrá guardar
los artefactos en Blob Storage mediante identidad administrada.

Mientras exista un análisis pendiente, otra carga devuelve HTTP 429. El estado
`running` se asigna al adquirir el bloqueo, no al ponerse en espera. El proceso
tiene un límite de 3600 segundos; al excederlo se termina el grupo de procesos y
se registra `failed`. El límite se configura durante el despliegue mediante
`MENTOX_GAMESTATE_ANALYSIS_TIMEOUT_SECONDS`.

Debe mantenerse `min-replicas=1` durante todo el análisis asíncrono. La actividad
de un proceso en segundo plano no garantiza que el escalador HTTP mantenga la
réplica. El comando `start` establece ese mínimo; `stop` se utiliza después de
descargar los resultados.

## Desplegar en otra suscripción

Inicie sesión y seleccione expresamente la suscripción:

```bash
az login
az account list --output table
az account set --subscription "<id-o-nombre-de-la-suscripción>"
az account show --query "{nombre:name,id:id,tenant:tenantId}" --output table
```

Prepare una clave nueva, no reutilice ni publique las claves de otros modelos:

```bash
cd /ruta/Mentox-Premier-league

export MENTOX_AZURE_RESOURCE_GROUP="rg-prime-moment-dev"
export MENTOX_AZURE_LOCATION="northcentralus"
export MENTOX_AZURE_SUBSCRIPTION_ID="$(az account show --query id --output tsv)"
export MENTOX_MODEL_API_KEY="$(openssl rand -hex 32)"
export MENTOX_ACCEPT_MODEL_LICENSES=1
export MENTOX_IMAGE_BUILD_MODE=local

bash infra/azure/gamestate-operator.sh deploy
```

La construcción es grande y puede tardar. Durante el `docker build` se
descargan y validan los siete pesos que usa el pipeline: YOLO, dos de ReID,
dos de calibración y dos de OCR. Por eso la primera construcción tarda más y
la imagen ocupa más espacio, pero una réplica nueva ya no necesita descargar
pesos al recibir su primer video. Necesita cuota
`Consumption-GPU-NC8as-T4` en la región elegida. El script crea la aplicación
con `min-replicas=0` y `max-replicas=1`.

`MENTOX_AZURE_SUBSCRIPTION_ID` fija la suscripción en cada operación del
despliegue, aunque otra terminal cambie la cuenta global durante la construcción.
El script usa Docker directamente si el usuario tiene acceso; recurre a `sudo`
cuando no lo tiene. Antes de publicar la imagen local de GameState comprueba
que la API importe correctamente y que los siete pesos estén presentes.

## Encender y comprobar

```bash
bash infra/azure/gamestate-operator.sh start

export GAMESTATE_ENDPOINT="$(bash infra/azure/gamestate-operator.sh endpoint)"
curl --fail-with-body "${GAMESTATE_ENDPOINT}/health/ready"
```

La imagen incorpora los pesos para evitar su descarga al procesar vídeos. La
primera inferencia todavía inicializa modelos y CUDA. El endpoint de salud
solo responde `ready` cuando CUDA, el ejecutor y
el manifiesto de siete pesos precargados están disponibles.

`ready` no demuestra que un MP4 haya terminado de procesarse ni que todos los
modelos estén residentes en VRAM. El ejecutor de TrackLab se inicializa por
análisis. La nueva imagen requiere una inferencia GPU completa para verificar
que no aparece ninguna descarga adicional y medir su duración.

## Corrección de calibración de keypoints

La prueba GPU del 27 de octubre falló con `KeyError: 0` en
`sn_gamestate/calibration/nbjw_calib.py`. El código original buscaba la etiqueta
cero en cada lote de pandas en lugar de seleccionar la primera fila.

El Dockerfile ejecuta `patch_calibration.py` durante la construcción y cambia
el acceso a:

```python
predictions = metadatas["keypoints"].iloc[0]
```

El parche reconoce el código esperado del commit fijado, permite ejecutarse
de nuevo y detiene el build si el origen cambia o contiene coincidencias
ambiguas. No renumera fotogramas ni inventa keypoints. Se aplica después de
la precarga de pesos para conservar esa capa de caché cuando Docker la tenga
disponible.

La corrección está probada localmente, incluida la expresión del método real
con pandas 2.3.3 de la imagen. Su incorporación requiere construir una imagen
nueva y verificar una inferencia completa. Para incluirla en un despliegue use:

```bash
unset MENTOX_IMAGE_TAG
export MENTOX_IMAGE_BUILD_MODE=local
bash infra/azure/gamestate-operator.sh deploy
```

Conserve la clave, suscripción y grupo de GameState ya configurados según las
instrucciones anteriores. `MENTOX_IMAGE_BUILD_MODE=existing` no construye el
parche: reutilizar una imagen antigua conserva el error. El despliegue del
operador mantiene mínimo cero; encienda el servicio solo para repetir la
prueba y vuelva a apagarlo al terminar.

## Render de diagnóstico

El render anotado interno está desactivado por defecto porque el backend
consume el JSONL. Para conservar ese MP4 de diagnóstico, exporte
`MENTOX_GAMESTATE_SAVE_VISUALIZATION=true` antes de desplegar.

El ejecutor configura `visualization.save_videos`, el argumento que consume
TrackLab 1.3.24. `visualization.cfg.save_videos` no desactiva su callback y no
debe utilizarse como sustituto. Las pruebas de `test_runner.py` comprueban los
argumentos del script tanto con render activado como desactivado.

El parche de build también conserva las columnas `video_id` e `image_id` en
la tabla inicial vacía de TrackLab. Un vídeo sin detecciones debe terminar con
cero observaciones, no con un error de columna ni con resultados inventados.
El manejo vacío se probó en T4 con un clip de 2 segundos; esto no verifica la
calidad del modelo sobre un partido completo.

## Asociar nombres en el backend

El tracking funciona sin nombres. Para asociar una pista a la plantilla hay que
comprobar primero que los equipos y jugadores de los metadatos son los del MP4.
La plantilla sintética de demostración no se considera esa comprobación.

En la terminal que inicia el backend, establezca el mapeo verificado y active
la resolución nominal únicamente cuando corresponda:

```bash
export SOCCERNET_GAMESTATE_TEAM_BY_SIDE='{"left":"<team-id-verificado-izquierda>","right":"<team-id-verificado-derecha>"}'
export SOCCERNET_GAMESTATE_ROSTER_VERIFIED=true
```

Sin estas condiciones, se conserva `track_id`, dorsal observado y posición;
`player_id` permanece vacío. Los votos duplicados del mismo cuadro no cuentan
como evidencia independiente y dos pistas simultáneas no pueden reclamar el
mismo jugador. La calibración actual requiere un campo de 105 × 68 metros.

## Analizar un MP4

```bash
curl --fail-with-body \
  --header "X-API-Key: ${MENTOX_MODEL_API_KEY}" \
  --form "video=@/ruta/video-sintetico-o-autorizado.mp4" \
  "${GAMESTATE_ENDPOINT}/v1/analyses"
```

Guarde el `analysis_id` devuelto y consulte su estado:

```bash
export GAMESTATE_ANALYSIS_ID="<analysis_id>"

curl --fail-with-body \
  --header "X-API-Key: ${MENTOX_MODEL_API_KEY}" \
  "${GAMESTATE_ENDPOINT}/v1/analyses/${GAMESTATE_ANALYSIS_ID}"
```

Cuando el estado sea `succeeded`, descargue el resultado y el log:

```bash
curl --fail-with-body \
  --header "X-API-Key: ${MENTOX_MODEL_API_KEY}" \
  --output gamestate-observations.jsonl \
  "${GAMESTATE_ENDPOINT}/v1/analyses/${GAMESTATE_ANALYSIS_ID}/result"

curl --fail-with-body \
  --header "X-API-Key: ${MENTOX_MODEL_API_KEY}" \
  --output gamestate-analysis.log \
  "${GAMESTATE_ENDPOINT}/v1/analyses/${GAMESTATE_ANALYSIS_ID}/log"
```

## Apagar y entregar la integración

```bash
bash infra/azure/gamestate-operator.sh stop
bash infra/azure/gamestate-operator.sh status
```

La persona que despliegue debe compartir por un canal privado:

- `GAMESTATE_ENDPOINT`;
- la clave usada como `MENTOX_MODEL_API_KEY`;
- grupo de recursos y nombre `ca-mentox-gamestate-dev`;
- salida de `/health/ready`;
- un JSONL y log de una inferencia autorizada;
- confirmación de que volvió a escala cero.

No debe compartir credenciales de Azure, sesiones CLI, contraseñas, claves de
Storage ni secretos de identidad administrada.

