# Evidencia técnica de DV-US-19

## Identificación

- **Historia:** DV-US-19 · Ejecutar Roboflow Sports sobre la muestra.
- **Estado:** verificada localmente como experimento; resultado `rejected` para integración.
- **Prioridad:** P2.
- **Última actualización:** 13 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.
- **Eleva:** parte espacial de DV-US-11.

## Objetivo

Ejecutar detección y seguimiento reales sobre el MP4 sintético permitido de DV-US-17, exportar las observaciones como `actual_model` y compararlas con las tres cajas manuales del balón sin afectar el backend ni el frontend oficial.

## Fuente fijada

| Elemento | Valor |
|---|---|
| Repositorio | `https://github.com/roboflow/sports` |
| Commit | `42c80c06b6b65a7f89455b89fe31cdf4c38ba227` |
| Fecha del commit | 27 de mayo de 2025 |
| Licencia de `sports` | MIT |
| Ultralytics | 8.4.177, AGPL-3.0-or-later |
| Supervision | 0.30.9 |
| PyTorch / Torchvision | 2.14.1 / 0.29.1, CPU |
| Python | 3.12 |
| Peso | `football-player-detection.pt` del `setup.sh` oficial |
| Licencia del peso | No declarada inequívocamente en el repositorio oficial |

El peso no se redistribuye ni se guarda en el repositorio. La ausencia de una licencia explícita impide aprobarlo automáticamente para distribución o producción, aunque se ejecute con fines de evaluación técnica.

## Hardware observado

- CPU: Intel Core i5-1135G7, 4 núcleos y 8 hilos.
- Memoria: 15 GiB totales, aproximadamente 1,5 GiB disponibles durante la inspección.
- GPU NVIDIA: no detectada.
- Docker: 27.0.3.
- Disco disponible: aproximadamente 49 GiB.

La inferencia se limita a CPU, 300 cuadros, tamaño 640 y confianza 0,10. La memoria disponible es un riesgo operativo; el contenedor evita contaminar el entorno principal.

## Archivos preparados

| Archivo | Función |
|---|---|
| `experiments/roboflow-sports/Dockerfile` | Entorno y peso aislados |
| `experiments/roboflow-sports/run_inference.py` | Inferencia, ByteTrack, salida cruda y entrada del evaluador |
| `experiments/roboflow-sports/run.sh` | Selección automática entre CPU y CUDA |
| `experiments/roboflow-sports/run-cpu.sh` | Ejecución forzada con PyTorch CPU |
| `experiments/roboflow-sports/run-gpu.sh` | Ejecución forzada con GPU NVIDIA |
| `experiments/roboflow-sports/run_variant.sh` | Construcción, inferencia y evaluación compartidas |
| `experiments/roboflow-sports/README.md` | Uso, licencias y límites |
| `.gitignore` | Excluir predicciones y vídeo anotado |

## Parámetros

| Parámetro | Valor |
|---|---:|
| Dispositivo | `cpu` o `cuda`, registrado en cada ejecución |
| `imgsz` | 640 |
| Confianza mínima | 0,10 |
| Tracker | `bytetrack.yaml` |
| IoU de evaluación | 0,50 |
| Tolerancia temporal | 100 ms |
| Cuadros con referencia manual | 50, 150 y 250 |

El ejemplo oficial usa `imgsz=1280` para detección de jugadores. Se redujo a 640 para admitir CPU o una GPU modesta con la misma configuración. Esta diferencia queda explícita y limita la comparabilidad con la demostración oficial.

## Selección de dispositivo

- `run.sh` usa CUDA solo cuando `nvidia-smi` responde; en cualquier otro equipo usa CPU.
- `run-cpu.sh` instala PyTorch desde el índice CPU y registra `device=cpu`.
- `run-gpu.sh` instala PyTorch desde un índice CUDA, concede `--gpus all` al contenedor y registra versión CUDA y nombre de GPU.
- La variante GPU requiere NVIDIA Container Toolkit además del controlador.
- Una solicitud CUDA sin GPU visible produce un error explícito.
- `MENTOX_CUDA_INDEX_URL` permite elegir otro índice oficial compatible, como `cu128`; el valor predeterminado es `cu130`.

## Licencias consultadas

- `roboflow/sports` declara MIT en `LICENSE` y `setup.py`.
- El README de fútbol separa `sports`/Supervision bajo MIT y Ultralytics YOLOv8 bajo AGPL-3.0.
- El `setup.sh` oficial descarga tres pesos y cinco vídeos desde Google Drive.
- Este experimento descarga solo el peso combinado de jugadores y no descarga ninguno de los vídeos externos.
- La procedencia del conjunto de entrenamiento se asocia al DFL Bundesliga Data Shootout, pero el repositorio no establece de forma suficiente una licencia independiente del archivo `.pt`.

## Context7 y documentación vigente

Context7 confirmó la instalación desde el repositorio, los modos `PLAYER_DETECTION`, `BALL_DETECTION`, `PLAYER_TRACKING` y las rutas de los pesos. La documentación vigente de Ultralytics confirma `model.track`, persistencia entre cuadros, ByteTrack y acceso a cajas, confianza, clase e identificador de seguimiento.

## Cobertura actual

| Criterio | Estado |
|---|---|
| Commit, versiones, peso, clases, dispositivo y parámetros | Preparado |
| Licencias de código, dependencia y peso | Revisadas; peso con licencia no declarada |
| Predicciones `actual_model` | 6 exportadas |
| Calidad, tiempo, falsos positivos y omisiones | Medidos |
| Revisión visual de un falso positivo y una omisión | Realizada en el vídeo anotado |
| Decisión `candidate` o `rejected` | `rejected` |

## Ejecución pendiente

### Primer intento de construcción

La selección automática eligió CPU correctamente. Docker completó las capas de Python 3.12, PyTorch CPU, Ultralytics, Supervision y el checkout del commit fijado. La construcción se detuvo al descargar el peso porque `gdown==6.4.2` ya no reconoce la opción heredada `--id`:

```text
gdown: error: unrecognized arguments: --id
```

Context7 confirmó que gdown 6 recibe la URL o el identificador como argumento posicional. Se corrigió el Dockerfile para usar el identificador posicional y `--output`. Las capas pesadas quedaron disponibles en la caché de Docker. No se ejecutó inferencia ni se generaron predicciones durante este intento.

### Segundo intento de construcción y ejecución

La reconstrucción reutilizó las capas anteriores, descargó el peso correctamente y creó la imagen CPU `mentox/roboflow-sports:42c80c0-cpu`. La inferencia todavía no comenzó: Ultralytics no pudo abrir el peso porque `gdown` lo había creado dentro de la imagen con permisos privados del usuario `root`:

```text
PermissionError: [Errno 13] Permission denied: '/models/football-player-detection.pt'
```

El contenedor se ejecuta deliberadamente con el UID y GID de la persona que invoca el script. Esto permite escribir las salidas en el directorio montado sin dejarlas como propiedad de `root`, pero también exige que los archivos internos necesarios sean legibles por ese usuario arbitrario.

Se conservó esa medida y se añadió `chmod 0444` al peso después de descargarlo. El modelo queda inmutable durante la ejecución y legible por cualquier UID del contenedor. La documentación vigente de Docker consultada mediante Context7 confirma el uso de permisos octales para preparar archivos consumidos por usuarios distintos dentro de una imagen.

El aviso de Ultralytics sobre su directorio de configuración no causó la interrupción: la biblioteca eligió automáticamente un directorio alternativo en `/tmp`. En este intento no se generaron predicciones ni vídeo anotado.

### Tercer intento de ejecución

El peso quedó accesible y `model.track` comenzó a preparar ByteTrack. La ejecución se detuvo porque `lap`, dependencia usada para la asignación de detecciones a trayectorias, no estaba instalada:

```text
ModuleNotFoundError: No module named 'lap'
```

Ultralytics intentó instalar automáticamente `lap>=0.5.12`, pero el contenedor se ejecuta sin privilegios y no puede escribir en los paquetes globales ni en `/.local`. Este comportamiento dinámico tampoco sería reproducible. Se añadió `lap==0.5.13` a la construcción de la imagen, versión compatible con Python 3.12 que el propio intento de instalación resolvió. Context7 confirmó que la invocación de seguimiento con ByteTrack se realiza mediante `model.track(..., tracker="bytetrack.yaml")`; la dependencia queda ahora preparada antes de la ejecución.

No se generaron predicciones ni vídeo anotado durante este intento. La historia continúa en progreso hasta completar y evaluar la inferencia.

## Ejecución completa

El cuarto intento terminó correctamente y procesó los 300 cuadros del vídeo sintético en CPU. Generó las predicciones crudas, la entrada del evaluador, el informe de evaluación y el vídeo anotado.

### Resultados de inferencia

| Medida | Resultado |
|---|---:|
| Cuadros procesados | 300 |
| Duración del vídeo | 30.000 ms |
| Tiempo de procesamiento | 414.353,463 ms |
| Factor de tiempo real | 13,8118 |
| Predicciones totales | 6 |
| Balones predichos | 4 |
| Jugadores predichos | 2 |
| Predicciones con `track_id` | 0 |
| Balones predichos en cuadros de referencia | 0 |

Las seis salidas conservan `prediction_origin=actual_model`. Sus confianzas estuvieron entre 0,1037 y 0,2202. No se asignó `player_id`, porque ninguna asociación nominal fue demostrada.

### Evaluación contra las anotaciones

| Medida | Resultado |
|---|---:|
| Verdaderos positivos | 0 |
| Falsos positivos evaluables | 0 |
| Omisiones | 3 |
| Precisión | 0,00 |
| Recobrado | 0,00 |
| F1 | 0,00 |

El evaluador solo compara predicciones dentro de 100 ms de los tres cuadros anotados. Por eso no contabiliza como falsos positivos las detecciones que aparecieron fuera de esos instantes; no significa que las seis detecciones crudas sean correctas.

### Revisión visual

- **Falso positivo observado:** en el cuadro 16, a 1,6 segundos, la caja `ball 0.11` aparece sobre el número celeste `6`, no sobre el marcador blanco `B` que representa el balón en el vídeo sintético.
- **Omisión observada:** en el cuadro 50, a 5 segundos, el balón blanco `B` es visible cerca del grupo de jugadores, pero no tiene ninguna caja. Corresponde a `ann-ball-005`, una de las tres omisiones registradas.
- Los cuadros 150 y 250 también muestran el balón de referencia sin detección.
- La salida de los cuadros 178 y 179 etiqueta como `player` una región pequeña sobre los símbolos del simulador, sin continuidad suficiente para producir `track_id`.

La revisión se realizó sobre `roboflow-sports-annotated.mp4`, que contiene 300 cuadros, resolución 800 × 450, 10 fps y duración de 30 segundos.

## Decisión

El informe produjo `rejected` por tres motivos reproducibles:

1. precisión inferior al umbral de 0,50;
2. recobrado inferior al umbral de 0,50;
3. factor de tiempo real superior al máximo de 3,00.

DV-US-19 queda verificada porque se ejecutaron y revisaron todos sus criterios. Esta verificación no aprueba el modelo: con el vídeo sintético, el peso, `imgsz=640`, confianza 0,10 y CPU documentados, Roboflow Sports no debe integrarse en el flujo del producto. El modo sintético permanece operativo sin este modelo.

## Integridad de los artefactos

| Artefacto local excluido de Git | SHA-256 |
|---|---|
| `roboflow-sports-predictions.json` | `9e6efe0ef44041a95a27e3a5fb412a4233372ed5d7c57d985f26ae68a92d00be` |
| `roboflow-sports-evaluation-input.json` | `f57e8011c54d37d7a910a3b3e24aa9a88ceb458cfb2a795abaeb8128d2e14cfa` |
| `roboflow-sports-evaluation-report.json` | `bc160845ac7aca647edd464ebec00724e22bc73a5c41243824e48a8efbfb1676` |
| `roboflow-sports-annotated.mp4` | `6d5a70c6af444aace2e8054191389ec5a137b6d5019a25fd5dba76c03f0370b4` |

Los artefactos se conservan en `experiments/roboflow-sports/output/` y permanecen fuera de Git por tamaño, procedencia del peso y carácter experimental.

## Comando verificado

```bash
cd /home/university/league/Mentox-Premier-league
bash experiments/roboflow-sports/run.sh
```

La ejecución automática seleccionó CPU porque no detectó una GPU NVIDIA.

## Verificaciones adicionales

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_vision_evaluation.py -q

python3 -m json.tool \
  experiments/roboflow-sports/output/roboflow-sports-predictions.json

python3 -m json.tool \
  experiments/roboflow-sports/output/roboflow-sports-evaluation-report.json

git diff --check
```

Resultado: 11 pruebas del evaluador aprobadas en 0,09 segundos; ambos JSON válidos y ninguna advertencia de espacios en el diff.

```bash
# Automático
bash experiments/roboflow-sports/run.sh

# CPU explícita
bash experiments/roboflow-sports/run-cpu.sh

# GPU NVIDIA explícita
bash experiments/roboflow-sports/run-gpu.sh
```

No se marcará la historia como verificada hasta conservar las salidas, revisar el vídeo anotado, ejecutar el evaluador y documentar la decisión real.
