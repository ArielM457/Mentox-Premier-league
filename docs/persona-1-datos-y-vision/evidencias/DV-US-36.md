# DV-US-36 · Preparar SoccerNet GameState como servicio GPU

## Estado

**Retirado de la demo por decisión del usuario el 27 de octubre de 2026.**
La aplicación Azure `ca-mentox-gamestate-dev` fue eliminada y se verificó su
ausencia. Se conservan el código y los resultados de investigación. Roboflow,
TeamSpotting, Blob Storage, las colas y el worker no se modificaron durante
el retiro. [Operación y nueva dirección acordada](gamestate-retiro-20261027.md).

Última validación GPU del 27 de octubre: **ejecución completa aprobada, calidad
analítica sobre MESSI insuficiente**. El MP4 de 180 segundos terminó sin errores
en unos 27 minutos, pero solo entregó 4 detecciones, ninguna posición calibrada
y ninguna métrica disponible. El servicio quedó con cero réplicas. Véase
[la evidencia final de despliegue y calidad](gamestate-parche-validacion-20261027-7uTJjl/README.md).
El fallo anterior de calibración se conserva en
[la primera prueba del MP4](gamestate-validacion-20261027-JoY84d/README.md).
Los apartados siguientes conservan la evolución previa del despliegue.

Revisión posterior: [auditoría del 27 de octubre](../revision-integracion-modelos-20261027.md).
Contiene las correcciones de despliegue e integración, 101 pruebas locales
aprobadas y las limitaciones que todavía necesitan una inferencia real.

Servicio construido, publicado y desplegado en Azure Container Apps con escala
`0-1`. La integración automática con el backend y la pantalla Partido está
verificada localmente. La inferencia real de GameState sobre el MP4 sigue
pendiente hasta encender la réplica y ejecutar la prueba conjunta.

## Objetivo y alcance

La solicitud del equipo es desplegar SoccerNet GameState en una suscripción con
GPU distinta de la usada por Roboflow y TeamSpotting. El servicio recibe un MP4
sintético o autorizado y produce observaciones de tracking, rol, equipo, dorsal
y posición. No resuelve automáticamente un dorsal como identidad nominal.

Entrada:

- MP4 de hasta 240 segundos y 256 MiB;
- clave privada por `X-API-Key`;
- una réplica Azure Container Apps con Tesla T4.

Salida:

- identificador de análisis y estado consultable;
- JSONL compatible con el adaptador GameState existente;
- log descargable para diagnóstico.

## Decisiones

1. La inferencia es asíncrona para no depender de la duración máxima de una
   solicitud HTTP.
2. Una sola inferencia usa la GPU a la vez mediante un bloqueo de proceso.
3. La aplicación se despliega con escala `0-1`; el operador debe encenderla
   antes de analizar y apagarla al terminar.
4. Los resultados son efímeros en esta primera versión y deben descargarse
   antes del apagado.
5. El health check comprueba CUDA, el ejecutor y un manifiesto de pesos. Los
   pesos se incorporan durante la construcción y no durante la inferencia.
6. La salida conserva dorsal y `track_id` como observaciones; no fabrica
   `player_id`.

## Archivos

| Archivo | Responsabilidad |
|---|---|
| `deploy/azure-soccernet-gamestate/Dockerfile` | Entorno fijado de GameState y API |
| `deploy/azure-soccernet-gamestate/preload_models.py` | Descarga, valida y registra los siete pesos durante el build |
| `deploy/azure-soccernet-gamestate/app.py` | Carga, trabajo asíncrono, estado y descarga |
| `deploy/azure-soccernet-gamestate/run_analysis.sh` | Pipeline TrackLab para MP4 |
| `deploy/azure-soccernet-gamestate/export_tracker_state.py` | Estado TrackLab a JSONL auditable |
| `infra/azure/deploy-soccernet-gamestate.sh` | Parámetros del despliegue GPU común |
| `infra/azure/gamestate-operator.sh` | Deploy, encendido, estado y escala cero |
| `deploy/azure-soccernet-gamestate/README.md` | Operación para otra suscripción |
| `apps/backend/src/match_intelligence/application/gamestate_analysis.py` | Cliente asíncrono, sondeo, descarga y muestreo |
| `apps/backend/src/match_intelligence/adapters/http/integration_router.py` | Preparación conjunta de los tres modelos |
| `apps/frontend/src/components/match/LiveExperiencePanels.jsx` | Estado, tracks, dorsales y evidencia sincronizada |

## Verificación local

```bash
bash -n infra/azure/deploy-soccernet-gamestate.sh \
  infra/azure/gamestate-operator.sh \
  deploy/azure-soccernet-gamestate/run_analysis.sh

python3.12 -m py_compile \
  deploy/azure-soccernet-gamestate/app.py \
  deploy/azure-soccernet-gamestate/export_tracker_state.py

UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest deploy/azure-soccernet-gamestate/test_contract.py \
    apps/backend/tests/test_gamestate_analysis.py -q

cd apps/frontend
npm run build
npm run lint
```

Resultado de la integración del 26 de octubre de 2026:

- 10 pruebas de GameState, TeamSpotting y captura en vivo aprobadas;
- frontend compilado correctamente;
- lint sin errores nuevos; permanecen tres advertencias preexistentes;
- GameState se prepara junto con Roboflow y TeamSpotting antes de Play;
- la reproducción usa la duración real del MP4;
- la UI recupera observaciones por ventana temporal y no depende únicamente
  del búfer WebSocket;
- dorsal y `track_id` se muestran como observación, no como identidad nominal.

## Evidencia de despliegue Azure

- suscripción: `Azure for Students` (`7d45d958-156a-4278-9935-755ba5a395ca`);
- grupo: `rg-prime-moment-dev`;
- imagen: `mentox138f2e77.azurecr.io/mentox/soccernet-gamestate:cd13e6c039a2`;
- digest: `sha256:b49c0be7ac6dad15e10546c5ce112c2ae6872aec6e902038ef6e8153d8e6a8a7`;
- aplicación: `ca-mentox-gamestate-dev`;
- endpoint: `https://ca-mentox-gamestate-dev.yellowdune-bc941df0.northcentralus.azurecontainerapps.io`;
- estado final del despliegue: preparado en escala cero.

## Evidencia pendiente en Azure

- revisión saludable sobre `NC8as-T4`;
- respuesta de `/health/ready` con Tesla T4;
- análisis exitoso de un MP4 permitido;
- JSONL con tracks y, cuando existan, equipo, dorsal y posición;
- medición de duración y memoria;
- réplica retirada después de configurar `min-replicas=0`.

## Incidencia de arranque del 26 de octubre de 2026

La primera imagen desplegada entró en reinicio continuo antes de abrir el
puerto HTTP. Los logs de consola de la revisión
`ca-mentox-gamestate-dev--loctm46` mostraron:

```text
TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
```

La causa fue una anotación `str | None` evaluada por FastAPI dentro de una
imagen basada en Python 3.9. Se reemplazó por `Optional[str]` y se añadió una
prueba de contrato que impide reintroducir esa incompatibilidad. Esta
corrección queda verificada en el código; la nueva imagen aún debe construirse,
publicarse y validarse en Azure antes de considerar saludable el servicio.

## Limitaciones

- El pipeline completo todavía no fue ejecutado contra la réplica Azure.
- La calidad sobre el render MESSI no está medida.
- El almacenamiento efímero no es adecuado para producción.
- Los resultados se mantienen en memoria para la demo; reiniciar el backend
  exige preparar nuevamente los modelos.
- La nueva imagen optimizada todavía debe construirse y validarse en Azure.

## Optimización de pesos del 27 de octubre de 2026

La revisión desplegada descargó pesos al procesar el primer video. El log
confirmó descargas para calibración, ReID y OCR, entre ellas `SV_kp`,
`SV_lines`, `hrnetv2_w32_imagenet_pretrained.pth` y los checkpoints de MMOCR.
Esto no era una instalación repetida de Python: era inicialización tardía de
modelos sobre un sistema de archivos efímero.

Se auditó el commit fijado de SoccerNet GameState y TrackLab 1.3.24. El
pipeline activo requiere siete artefactos:

1. `yolo11m.pt` para detección de personas;
2. dos pesos de ReID;
3. `SV_kp` y `SV_lines` para cancha y calibración;
4. dos pesos MMOCR para detectar y leer dorsales.

El nuevo `preload_models.py` descarga esos artefactos durante `docker build`,
valida los dos MD5 publicados por SoccerNet, calcula SHA-256 y genera
`/models/preloaded-models.json`. La API falla al arrancar si falta el
manifiesto o si un archivo no coincide en tamaño. `/health/ready` informa la
lista precargada.

Verificación local de código, sin descargar los pesos ni construir la imagen:

```bash
python -m py_compile \
  deploy/azure-soccernet-gamestate/preload_models.py \
  deploy/azure-soccernet-gamestate/app.py

pytest deploy/azure-soccernet-gamestate/test_contract.py -q
```

Resultado esperado: contrato aprobado y siete nombres presentes. Falta una
construcción completa, publicación y análisis en Azure para medir la mejora.

## Enriquecimiento analítico del 27 de octubre de 2026

El resultado JSONL de GameState ahora se convierte en `TrackingFrame v1` con
el tiempo exacto calculado desde `frame_index / fps`. Cuando el partido existe
en el registro del backend, esos cuadros reemplazan el tracking simulado de la
sesión y alimentan `tracking@1` para calcular:

- distancia recorrida por jugador;
- distancia a alta intensidad;
- velocidad máxima;
- sprints;
- ancho, profundidad y compactación por equipo.

La identidad nominal utiliza una asociación reproducible y conservadora. Por
cada `track_id` se cuentan lecturas de dorsal con confianza mínima de 0,50. Se
confirma `player_id` únicamente con al menos tres votos, 70 % de acuerdo y una
sola coincidencia de equipo y dorsal en la plantilla del partido. La evidencia
de votos queda incluida en la observación; los casos sin plantilla, con dorsal
duplicado o con votos inconsistentes permanecen como `unconfirmed`.

TeamSpotting normaliza sus clases a candidatos de `pass`, `shot`, `tackle` y
`restart`, pero conserva `player_id`, receptor y equipo vacíos porque el modelo
temporal no entrega actor. No se publican como hechos confirmados.

La API incorpora `GET /api/v1/integration/live/analytics` para consultar las
métricas, su evidencia y los valores no disponibles. La velocidad del balón y
del tiro permanece no disponible: el detector Roboflow actual entrega una
detección independiente por fotograma y no una trayectoria calibrada del balón.

Verificación local:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest -q \
    apps/backend/tests/test_soccernet_gamestate_adapter.py \
    apps/backend/tests/test_gamestate_analysis.py \
    apps/backend/tests/test_teamspotting_analysis.py \
    apps/backend/tests/test_integrated_pipeline_api.py
```

Resultado: 15 pruebas aprobadas. Esta prueba verifica contratos y cálculo
local; todavía falta repetir el análisis completo con el contenedor Azure y
revisar visualmente la estabilidad de posiciones, dorsales e identidades.

## Correcciones de la revisión general

La revisión añadió timeout y terminación de procesos al servicio, rechazo de
cargas simultáneas, validación del manifiesto completo y render anotado
desactivado por defecto. El backend protege la preparación de cancelaciones del
cliente, reanuda un `analysis_id` tras un timeout de sondeo y conserva errores y
fases por modelo. Se comprueba que TeamSpotting y GameState hayan recibido el
mismo contenido mediante SHA-256.

La resolución nominal exige ahora un mapeo explícito mediante
`SOCCERNET_GAMESTATE_TEAM_BY_SIDE` y
`SOCCERNET_GAMESTATE_ROSTER_VERIFIED=true`. Los votos proceden de cuadros
distintos y no se aceptan pistas simultáneas que reclamen la misma identidad.
Sin esos parámetros, las métricas por pista siguen disponibles cuando existen
posiciones calibradas; no se inventan nombres ni equipos de plantilla.

Se corrigieron ventanas de velocidad que cruzaban pérdidas de seguimiento y
la captura después de un salto de reproducción. La UI dejó de anticipar
observaciones futuras y de vincular un dorsal a una acción solo por proximidad
temporal. El consumidor de Event Hubs comienza desde su hora de creación para
no omitir publicaciones durante la conexión.

La verificación reproducible y los archivos de prueba se detallan en la
auditoría enlazada. Los nuevos cambios del contenedor requieren reconstrucción
y prueba GPU; no se desplegaron durante esta revisión.

## Despliegue posterior autorizado · 27 de octubre de 2026

Después de la revisión, se ejecutó el despliegue solicitado únicamente en la
suscripción separada de GameState:

- suscripción: `7d45d958-156a-4278-9935-755ba5a395ca`;
- grupo: `rg-prime-moment-dev`;
- aplicación: `ca-mentox-gamestate-dev`;
- imagen: `mentox138f2e77.azurecr.io/mentox/soccernet-gamestate:37e20cf190c4`;
- digest ACR: `sha256:aa220fc7cef893879ffa2c0bfecc57f83982c48511ea10997549b16c902c9d05`;
- revisión: `ca-mentox-gamestate-dev--0000004`;
- estado de aprovisionamiento: `Succeeded`;
- revisión saludable, modo `Single`, tráfico 100 % a `0000004`;
- escala configurada: mínimo 0, máximo 1;
- comprobación final de réplicas: lista vacía.

Se reutilizó el secreto `model-api-key` existente sin mostrarlo ni rotarlo. Las
operaciones de Azure del script ahora fijan la suscripción por llamada mediante
`MENTOX_AZURE_SUBSCRIPTION_ID`, para evitar que un cambio de cuenta en otra
terminal afecte el despliegue. Docker se ejecutó con el usuario actual; el
script conserva `sudo` como alternativa cuando sea necesario.

Comando de operación utilizado, con la clave recuperada solo en memoria:

```bash
export MENTOX_AZURE_SUBSCRIPTION_ID=7d45d958-156a-4278-9935-755ba5a395ca
export MENTOX_AZURE_RESOURCE_GROUP=rg-prime-moment-dev
export MENTOX_AZURE_LOCATION=northcentralus
export MENTOX_ACR_NAME=mentox138f2e77
export MENTOX_ACCEPT_MODEL_LICENSES=1
export MENTOX_IMAGE_BUILD_MODE=local
bash infra/azure/gamestate-operator.sh deploy
```

La construcción descargó y validó los siete pesos. La fase de precarga tardó
1662,8 segundos. Antes de publicar se ejecutó la imagen local, sin red ni GPU,
con su usuario de servicio: importó la API en Python 3.9 y comprobó los siete
archivos del manifiesto. El comando terminó correctamente.

Configuración aplicada al contenedor:

```text
MENTOX_MAX_VIDEO_SECONDS=240
MENTOX_GAMESTATE_ANALYSIS_TIMEOUT_SECONDS=3600
MENTOX_GAMESTATE_SAVE_VISUALIZATION=false
```

La comprobación HTTP externa de `/health/ready` agotó 30 segundos durante la
escala desde cero. La consulta posterior de réplicas devolvió `[]`. No se dejó
una réplica encendida ni se envió un MP4. La calidad, duración de inferencia y
ausencia de descargas adicionales durante el pipeline siguen pendientes de la
prueba GPU con el servicio encendido. No se modificaron Roboflow, colas ni el
worker de la otra suscripción.

## Validación real GPU posterior · 27 de octubre de 2026

Se encendió únicamente GameState y se envió el MP4 sintético MESSI de 180
segundos, 2700 fotogramas y 1920 × 1080. Se utilizó el adaptador de producción
mediante `apps/backend/scripts/validate_gamestate_remote.py`, sustituyendo solo
la descarga Blob por lectura del archivo local. El transporte de esta prueba
fue en memoria, sin publicar en Event Hubs ni activar Roboflow o TeamSpotting.

El servicio aceptó la credencial, reconoció Tesla T4 e informó sus siete pesos.
El log muestra cargas locales/caché y no transferencias ni instalaciones
nuevas. Se observaron instantáneas de 94–95 % de utilización GPU y 3857 MiB
ocupados, no un perfil promedio.

El análisis `6dcc306a4fa34eb69a510940a8132fdd` falló tras 1538,092 segundos de
pipeline (25 minutos y 38 segundos). El error está en
`sn_gamestate/calibration/nbjw_calib.py:179`:

```python
predictions = metadatas["keypoints"][0]
```

Con índices de lote que no contienen la etiqueta cero, pandas 2.3.3 lanza
`KeyError: 0`. La reproducción mínima dentro de la imagen, sin red ni GPU,
confirma el error y que `.iloc[0]` selecciona correctamente la primera
posición. Ese cambio todavía debe aplicarse de forma reproducible durante
el build y probarse con el pipeline: no se parcheó ni redesplegó el servicio
durante esta validación.

El ejecutor terminó con código 1. No se obtuvieron observaciones finales,
tracking calibrado, dorsales ni métricas verificadas. El tiempo registrado
no representa una inferencia completa ni permite prometer rendimiento en
tiempo real. Los datos de referencia del simulador no se usaron como entrada
ni sustituyeron resultados ausentes.

Logs completos, hash de entrada, estado remoto, diagnóstico GPU, reproducción
de pandas e instrucciones se conservan en la carpeta de evidencia enlazada
al principio. Al finalizar se restauró escala `0-1`; la retirada efectiva se
registra por separado en esa carpeta.

## Corrección local del fallo de calibración · 27 de octubre de 2026

Tras la validación fallida, el usuario autorizó incorporar la corrección.
Se añadió `deploy/azure-soccernet-gamestate/patch_calibration.py`. El Dockerfile
lo ejecuta sobre el checkout de SoccerNet y sustituye únicamente el acceso a
la primera fila de keypoints por `.iloc[0]`. Conserva los identificadores y el
resto del pipeline. La construcción se detiene si el código esperado falta,
aparece repetido o mezcla la expresión original y la corregida. El parche es
idempotente y comprueba la sintaxis antes de escribir el archivo.

La capa del parche queda después de `preload_models.py` para no invalidar
innecesariamente la caché de pesos. No se cambiaron dependencias, modelos,
pesos, contratos, backend ni frontend. La documentación de indexación de pandas
se consultó mediante Context7.

Archivos del cambio:

- `deploy/azure-soccernet-gamestate/patch_calibration.py`;
- `deploy/azure-soccernet-gamestate/test_calibration_patch.py`;
- `deploy/azure-soccernet-gamestate/Dockerfile`;
- `deploy/azure-soccernet-gamestate/README.md`.

Verificación del paquete local:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 --with python-multipart==0.0.20 \
  pytest -q deploy/azure-soccernet-gamestate
```

Resultado: **19 pruebas aprobadas y 3 omitidas**. Las tres omitidas requieren
pandas y el checkout del contenedor. El entorno restringido no pudo resolver
PyPI para la dependencia de pruebas; la repetición autorizada fuera del sandbox
terminó correctamente.

Se ejecutó además la prueba en la imagen local anterior, con Python 3.9 y
pandas 2.3.3, montando el código corregido en modo lectura y sin red ni GPU:

```bash
docker run --rm --network none --user 10001 \
  --env GAMESTATE_SOURCE_ROOT=/opt/sn-gamestate \
  --mount type=bind,source=/home/university/league/Mentox-Premier-league/deploy/azure-soccernet-gamestate,target=/patch,readonly \
  --entrypoint python \
  mentox138f2e77.azurecr.io/mentox/soccernet-gamestate:37e20cf190c4 \
  /patch/test_calibration_patch.py
```

Resultado: **13 pruebas aprobadas, ninguna omitida**. Se reprodujo el error
original, se verificó la selección posicional con índices cero, no consecutivos,
de texto y con cero en otra posición, y se evaluó la expresión corregida del
método real de SoccerNet sin importar los modelos. También se verificaron
idempotencia, rechazo de fuentes inesperadas e integración en el Dockerfile.
La compilación de Python y `git diff --check` terminaron correctamente.

Estas pruebas validan el parche, no una inferencia completa. No se construyó
una imagen nueva, no se publicó en ACR, no se redesplegó Azure ni se encendió
la GPU en este cambio. La imagen desplegada todavía contiene el error original.
Para aplicarlo se requiere construir con `MENTOX_IMAGE_BUILD_MODE=local`, sin
reutilizar un tag antiguo, y repetir el MP4 antes de dar DV-US-36 por verificada.

## Despliegue del parche y compatibilidad de TrackLab

El usuario autorizó construir, publicar, desplegar y repetir la inferencia.
Se conservó la suscripción separada y la misma clave existente, recuperada
solo en memoria. La imagen final de esta iteración es
`mentox138f2e77.azurecr.io/mentox/soccernet-gamestate:60da675eaafb`, digest
`sha256:7228f2cd754641eb44b9772fab1583ee1860da613dfcd85b4af93141e18d4ae8`.
Los siete pesos y dependencias se reutilizaron de la caché del build.

La prueba corta identificó dos fallos adicionales cuando el detector no
encuentra objetos. Primero se corrigió el argumento del render a
`visualization.save_videos=false`: el nivel `visualization.cfg` no desactiva
el callback de TrackLab 1.3.24. Después se conservó el esquema vacío
`video_id` / `image_id` en `TrackerState.load` para permitir guardar cero
detecciones. No se captura cualquier excepción como salida vacía ni se añaden
observaciones artificiales.

`patch_calibration.py` aplica ambos parches con coincidencias estrictas. Se
añadieron pruebas de selección posicional y actualizaciones vacías usando
los métodos reales instalados, además de comprobar los argumentos del runner
con render activado y desactivado. Resultado final local: **24 aprobadas y
5 omitidas** en el backend; **18 aprobadas sin omisiones** dentro de la imagen
exacta recién construida, sin red ni GPU. La API y el manifiesto de pesos
también se comprobaron localmente antes del push.

La prueba corta `77755ee192bf4e3badd3475d464ed37a`, de 2 segundos / 30 cuadros,
terminó correctamente en T4: **23,472 segundos de proceso** y 124,745 segundos
del cliente incluyendo arranque. Produjo cero observaciones, cero tracking y
ninguna métrica disponible. Es una comprobación de manejo vacío, no de calidad
de detección ni de calibración.

Después se envió el MP4 original de 180 segundos sin recodificar, análisis
`bed13a88ebaf4110a00e74fce99d881f`. La salida y el estado final se guardan en
la nueva carpeta de evidencia, junto con las tres iteraciones, sus logs,
hashes y la comprobación de apagado. Esta prueba aísla GameState y su adaptador
con transporte en memoria; no valida frontend, Event Hubs ni otros modelos.

La repetición completa terminó con `succeeded`: 1613,559 segundos del pipeline
y 1622,142 segundos totales del cliente. Las 4 observaciones corresponden a solo
3 cuadros de los 2700, tienen 3 pistas y todos sus `bbox_pitch` son nulos. Hay
una lectura de dorsal sin confianza OCR, no una identidad confirmada. El
adaptador no produce tracking calibrado y marca las 11 métricas como no
disponibles. No se utilizaron los datos MESSI para sustituir las salidas.

La ejecución del parche queda verificada sobre ese MP4. No se valida precisión,
seguimiento útil, identificación nominal ni velocidades sobre los renders
actuales. El baseline requiere otra evaluación de dominio antes de presentarse
como extractor fiable de esas capacidades. Se comprobó el apagado: revisión
`0000015`, mínimo 0, máximo 1 y lista de réplicas vacía.
