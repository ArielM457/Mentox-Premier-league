# Evidencia técnica de DV-US-26

## Identificación

- **Historia:** DV-US-26 · Ampliar la percepción espacial de fútbol.
- **Estado:** verificada operativamente mediante inferencia completa en GPU de 6 GB; calidad pendiente de anotación manual.
- **Prioridad:** P1.
- **Última actualización:** 22 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.

## Objetivo y alcance

La suite aislada de Roboflow Sports ejecuta los tres pesos publicados por el
`setup.sh` oficial: detección general de participantes, detección especializada
del balón y puntos clave del campo. El detector general conserva ByteTrack. Las
salidas pueden incorporarse al canal de observaciones, pero no se convierten por
sí solas en `MatchEvent`.

La lista de datasets del README no instala modelos automáticamente. El modelo de
participantes distingue las clases que declare el peso, el detector del balón
produce cajas y el modelo del campo produce keypoints. La clasificación por
equipos con SigLIP, UMAP y KMeans requiere un ajuste por vídeo y queda fuera de
esta historia. OCR de dorsales, reidentificación nominal y segmentación tampoco
se presentan como implementados.

## Fuente y decisiones

| Elemento | Valor |
|---|---|
| Repositorio | `https://github.com/roboflow/sports` |
| Commit fijado | `42c80c06b6b65a7f89455b89fe31cdf4c38ba227` |
| Peso general | `football-player-detection.pt` |
| Peso de balón | `football-ball-detection.pt` |
| Peso de campo | `football-pitch-detection.pt` |
| Seguimiento | ByteTrack sobre el detector general |
| Python | 3.12 |
| Aceleración | CPU o NVIDIA CUDA mediante Docker |
| Licencia del código Sports | MIT |
| Licencia de Ultralytics | AGPL-3.0-or-later |
| Licencia separada de pesos | No declarada inequívocamente |

Los pesos se descargan durante la construcción y no se confirman ni se
redistribuyen. El modelo de campo se ejecuta cada cinco cuadros para reducir
costo; el intervalo es configurable. CUDA usa media precisión por defecto. El
lanzador detecta la VRAM y, con 8 GB o menos, usa automáticamente 640 px y un
intervalo de 10 cuadros para que una GPU de 6 GB no requiera configuración
manual.

## Archivos modificados

- `experiments/roboflow-sports/Dockerfile`
- `experiments/roboflow-sports/run_inference.py`
- `experiments/roboflow-sports/run_variant.sh`
- `experiments/roboflow-sports/run-gpu.sh`
- `experiments/roboflow-sports/README.md`
- `apps/backend/src/match_intelligence/application/integrated_pipeline.py`
- `apps/backend/src/match_intelligence/application/observation_playback.py`
- `apps/backend/scripts/realtime_replay_worker.py`
- `apps/backend/tests/test_observation_playback.py`

## Contrato de salida

Las cajas generales y del balón se guardan en `predictions` con
`model_role=player|ball`, `prediction_id`, cuadro, `timestamp_ms`, clase,
confianza, caja normalizada y origen. Los puntos del campo se guardan en
`pitch_observations` con `model_role=pitch`, confianza y coordenadas normalizadas.
Todos mantienen `player_id=null`.

El backend incorpora ambas colecciones a la reproducción controlada. Su fuente
es `roboflow-player`, `roboflow-ball` o `roboflow-pitch`, lo que evita confundir
dos modelos que observaron el mismo instante.

## Ejecución GPU

Prerrequisito:

```bash
nvidia-smi
sudo docker run --rm --gpus all \
  nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi
```

Ejecución completa:

```bash
cd /home/university/league/Mentox-Premier-league

MENTOX_CUDA_INDEX_URL=https://download.pytorch.org/whl/cu128 \
MENTOX_CUDA_DEVICE=0 \
bash experiments/roboflow-sports/run-gpu.sh
```

Para el vídeo permitido:

```bash
MENTOX_CUDA_INDEX_URL=https://download.pytorch.org/whl/cu128 \
MENTOX_CUDA_DEVICE=0 \
bash experiments/roboflow-sports/run-real.sh
```

`run-real.sh` seleccionará GPU automáticamente cuando `nvidia-smi` esté
disponible. La primera construcción descargará las dependencias y los tres pesos;
las siguientes reutilizarán la caché de Docker.

## Matriz de aceptación

| Criterio | Implementación | Verificación |
|---|---|---|
| Tres pesos oficiales | Dockerfile con los tres identificadores oficiales | Descarga e inferencia GPU aprobadas |
| Procedencia por observación | `model_role`, identificador y origen real | Pruebas de carga aprobadas |
| Seguimiento sin identidad inventada | ByteTrack y `player_id=null` | Inspección estática aprobada |
| Keypoints separados | `pitch_observations` y fuente propia | Prueba del loader aprobada |
| CPU y GPU | scripts automáticos y explícitos | CPU anterior y GPU actual comprobadas |
| Perfil de 6 GB | detección de VRAM, 640 px, stride 10 y FP16 | Inferencia completa aprobada |
| Límites documentados | README y esta evidencia | Aprobado |

## Comandos de verificación local

```bash
python3 -m py_compile experiments/roboflow-sports/run_inference.py
bash -n experiments/roboflow-sports/run.sh \
  experiments/roboflow-sports/run-cpu.sh \
  experiments/roboflow-sports/run-gpu.sh \
  experiments/roboflow-sports/run-real.sh \
  experiments/roboflow-sports/run_variant.sh

UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_observation_playback.py -q

git diff --check
```

Resultado local del 22 de octubre de 2026: el script de inferencia compiló, los
scripts Bash pasaron `bash -n`, las 9 pruebas enfocadas aprobaron y la suite
completa del backend terminó con **161 pruebas aprobadas en 0,86 segundos**. No
se descargaron pesos ni se ejecutó inferencia durante esta comprobación local.

## Resultado y trabajo pendiente

## Ejecución GPU del 23 de octubre de 2026

Una NVIDIA GeForce RTX 3060 Laptop de 6144 MiB ejecutó CUDA 13.0 con PyTorch
2.14.1, resolución 640, precisión FP16 y `pitch_stride=10`. Procesó los 750
cuadros del vídeo de 30 segundos en 51.282,675 ms.

| Salida | Cantidad |
|---|---:|
| Detecciones generales | 16.011 |
| Detecciones del modelo especializado de balón | 313 |
| Observaciones de campo | 75 |
| Trayectorias únicas | 111 |

Las detecciones generales fueron 14.125 jugadores, 1.375 árbitros, 471 porteros
y 40 balones. Las tres capturas recibidas muestran cajas sobre participantes,
pero también etiquetas superpuestas. Las 111 trayectorias en 30 segundos sugieren
fragmentación y requieren medición manual. El JSON tiene SHA-256
`825262770b591ad447f32d3cff0c192377962e39511dd9ad937703ab470d90af`.

La ejecución GPU queda verificada, no la calidad del modelo. Sin anotaciones
manuales no se calculan precisión, recobrado ni F1 y ninguna observación se eleva
a `MatchEvent`.
