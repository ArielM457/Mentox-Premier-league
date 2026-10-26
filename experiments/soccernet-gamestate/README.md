# SoccerNet Game State Reconstruction en GPU

Este experimento ejecuta el baseline oficial de `SoccerNet/sn-gamestate` sobre
una secuencia pública de validación o un MP4 sintético/autorizado. TrackLab
1.3.24 incluye `ExternalVideo`; el lanzador selecciona ese dataset cuando se
define `MENTOX_GAMESTATE_VIDEO_PATH` y exporta el estado a JSONL auditable.

## Fuente fijada

- Repositorio: `https://github.com/SoccerNet/sn-gamestate`.
- Commit: `1c958345067218297d221e45e1a6405f975f83e0`.
- TrackLab: 1.3.24.
- Python: 3.9, exigido por el proyecto oficial.
- PyTorch/Torchvision: 1.13.1/0.14.1 con CUDA 11.7.
- Licencia del repositorio: GPL-3.0.
- Dataset mínimo: SoccerNet GSR público, versión 1.3 o posterior.

El experimento está separado del backend Python 3.12. Los datasets, pesos,
estados y vídeos generados se montan como volúmenes y quedan fuera de Git.

TrackLab descarga automáticamente SoccerNet GameState y los pesos del baseline
en la primera ejecución. No hay que incluirlos en el ZIP. Quedan persistidos en:

```text
experiments/soccernet-gamestate/data/SoccerNetGS/
experiments/soccernet-gamestate/models/
```

La estructura esperada del dataset es `train/`, `valid/`, `test/` y
`challenge/`; el smoke usa una secuencia de `valid`. La versión oficial vigente
documentada por el proyecto es 1.3. Si el proveedor solicita autenticación o
aceptación de condiciones, el operador debe usar su propia cuenta autorizada y
nunca compartir el token.

## Prerrequisitos

```bash
nvidia-smi
sudo docker run --rm --gpus all \
  nvidia/cuda:11.7.1-base-ubuntu22.04 nvidia-smi
```

Se recomienda una GPU con al menos 12 GB de VRAM y suficiente disco para el
dataset, modelos y cachés. Si detecta 8 GB o menos, el lanzador reduce el smoke
automáticamente de 250 a 100 cuadros. Esto reduce el trabajo total, pero no
garantiza que el pipeline oficial completo quepa en 6 GB; GameState continúa
siendo una prueba experimental separada. La primera ejecución puede descargar
varios GB. Para 8 GB o menos, el script también reduce automáticamente los
lotes oficiales: detección y dorsal a 1, ReID y tracking a 8, y calibración a 1.

## Ejecución

Smoke inicial automático de 100 cuadros con 6-8 GB, o 250 cuadros con más VRAM:

```bash
cd /home/university/league/Mentox-Premier-league
bash experiments/soccernet-gamestate/run.sh
```

Otra GPU o más cuadros:

```bash
MENTOX_CUDA_DEVICE=1 \
MENTOX_GAMESTATE_FRAME_LIMIT=750 \
bash experiments/soccernet-gamestate/run-gpu.sh
```

MP4 propio, sintético o autorizado:

```bash
MENTOX_GAMESTATE_VIDEO_PATH="/ruta/partido.mp4" \
MENTOX_GAMESTATE_FRAME_LIMIT=250 \
bash experiments/soccernet-gamestate/run-gpu.sh
```

Los resultados quedan en:

```text
experiments/soccernet-gamestate/output/sn-gamestate.pklz
experiments/soccernet-gamestate/output/gamestate-observations.jsonl
experiments/soccernet-gamestate/output/run/
```

Normalice el JSONL para el backend Python 3.12:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/adapt_soccernet_gamestate.py \
  --input experiments/soccernet-gamestate/output/gamestate-observations.jsonl \
  --observations-output experiments/soccernet-gamestate/output/vision-observations.jsonl \
  --tracking-output experiments/soccernet-gamestate/output/tracking-frames.jsonl \
  --match-id messi-001 \
  --fps 15
```

## Límite actual

El soporte MP4 y el exportador están implementados, pero todavía requieren una
ejecución completa con GPU, pesos y un vídeo del proyecto. El modo MP4 evita
crear anotaciones SoccerNet ficticias; utiliza el adaptador `ExternalVideo`
incluido en TrackLab 1.3.24. La calidad con el render sintético de MESSI sigue
pendiente de medición.

No se presenta un dorsal como identidad nominal. Aunque el modelo proponga
equipo y dorsal, `player_id` seguirá vacío hasta asociarlo con evidencia externa.
