# Roboflow Sports para DV-US-19

Este experimento ejecuta una revisión fijada del ejemplo oficial de fútbol sobre el MP4 sintético de DV-US-17. Está aislado en Docker y no añade Ultralytics, PyTorch ni Roboflow Sports al backend.

## Fijación

- Roboflow Sports: commit `42c80c06b6b65a7f89455b89fe31cdf4c38ba227`.
- Python: 3.12.
- Ultralytics: 8.4.177.
- Supervision: 0.30.9.
- PyTorch: 2.14.1, variante CPU o CUDA.
- Torchvision: 0.29.1, variante CPU o CUDA.
- Modelos: `football-player-detection.pt`, `football-ball-detection.pt` y
  `football-pitch-detection.pt`, descargados mediante los identificadores del
  `setup.sh` oficial.
- Dispositivo: selección automática, CPU explícita o NVIDIA CUDA explícita.
- Seguimiento: ByteTrack mediante `bytetrack.yaml`.

## Licencias y límite de uso

El repositorio `roboflow/sports` declara MIT. Su ejemplo de fútbol documenta Ultralytics/YOLOv8 como AGPL-3.0. El repositorio descarga el peso desde Google Drive, pero no declara de forma inequívoca una licencia separada para ese archivo.

Por esta razón el peso queda dentro de la imagen Docker, no se confirma en Git y no se redistribuye. El resultado solo puede clasificarse como `candidate` o `rejected` para revisión; esta ejecución no autoriza integración o distribución.

## Ejecución

Selección automática:

```bash
bash experiments/roboflow-sports/run.sh
```

CPU explícita:

```bash
bash experiments/roboflow-sports/run-cpu.sh
```

GPU NVIDIA explícita:

```bash
bash experiments/roboflow-sports/run-gpu.sh
```

El lanzador consulta la VRAM automáticamente. Con 8 GB o menos aplica un perfil
conservador de 640 px, puntos del campo cada 10 cuadros y FP16. Una persona con
una GPU de 6 GB puede ejecutar directamente `run.sh` o `run-real.sh`, sin
exportar variables adicionales.

La variante GPU requiere controlador NVIDIA y NVIDIA Container Toolkit. Usa por defecto el índice oficial de PyTorch para CUDA 13.0. Si el controlador necesita otra variante compatible, se puede indicar, por ejemplo:

```bash
MENTOX_CUDA_INDEX_URL=https://download.pytorch.org/whl/cu128 \
bash experiments/roboflow-sports/run-gpu.sh
```

Antes de la primera ejecución GPU se puede comprobar el acceso desde Docker:

```bash
sudo docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi
```

La suite completa se ejecuta con `player`, `ball` y `pitch`. Se puede elegir una
GPU concreta, cambiar el índice CUDA o reducir temporalmente el conjunto:

```bash
MENTOX_CUDA_DEVICE=0 \
MENTOX_CUDA_INDEX_URL=https://download.pytorch.org/whl/cu128 \
bash experiments/roboflow-sports/run-gpu.sh

MENTOX_VISION_MODELS=player,ball bash experiments/roboflow-sports/run-gpu.sh
```

El detector general procesa todos los cuadros y usa ByteTrack. El detector
especializado del balón también procesa todos los cuadros. El modelo del campo
produce puntos clave cada cinco cuadros en el perfil estándar y cada diez en el
perfil de VRAM baja; el intervalo se configura con `MENTOX_PITCH_STRIDE`. CUDA usa media precisión por defecto y se
puede desactivar con `MENTOX_CUDA_HALF=0`.

Los datasets enlazados en el README de Roboflow no son modelos instalables. La
demostración oficial aporta estos tres pesos. La clasificación por equipos usa
una etapa adicional con SigLIP, UMAP y KMeans ajustada con recortes del propio
vídeo; no identifica nombres ni dorsales y no forma parte todavía de esta suite.

Si se solicita CUDA y PyTorch no ve la GPU dentro del contenedor, el proceso falla de forma explícita; nunca cambia silenciosamente a CPU.

La primera construcción de cada variante descarga PyTorch, las dependencias y el peso. CPU y CUDA usan imágenes distintas. Puede tardar varios minutos y ocupar varios gigabytes en la caché de Docker.

Resultados fuera de Git:

```text
experiments/roboflow-sports/output/roboflow-sports-predictions.json
experiments/roboflow-sports/output/roboflow-sports-evaluation-input.json
experiments/roboflow-sports/output/roboflow-sports-evaluation-report.json
experiments/roboflow-sports/output/roboflow-sports-annotated.mp4
```

## Interpretación

El vídeo de Google Research Football usa números y letras sobre fondo negro, no personas fotografiadas. Se espera una fuerte desviación de dominio. Cero detecciones o una calidad baja constituyen un resultado válido y deben producir `rejected`, nunca ajustarse u ocultarse para aparentar éxito.

La evaluación cuantitativa usa únicamente la clase `ball` en los cuadros manualmente anotados 50, 150 y 250. Las detecciones de jugadores y sus `track_id` se conservan en la salida cruda para inspección, pero no reciben una métrica espacial porque DV-US-17 no contiene cajas manuales de todos los jugadores.
