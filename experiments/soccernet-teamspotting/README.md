# SoccerNet Team Ball Action Spotting para DV-US-20

Este experimento ejecuta el checkpoint oficial T-DEED 2025 sobre el vídeo sintético permitido de DV-US-17. Está aislado en Docker y no añade PyTorch ni SoccerNet al backend.

## Fuente fijada

- Repositorio: `SoccerNet/sn-teamspotting`.
- Commit: `091fed2fc35c33f7489f3596958a2fe385e37d65`.
- Checkpoint: `checkpoint_best.pt`, archivo público enlazado por el README oficial.
- SHA-256 esperado: `ed7c558d575eba1918be8f67813571723962eeff807dba68a12a2d794dd1c72a`.
- Código: GPL-3.0.
- Checkpoint: licencia separada no declarada; no se redistribuye.
- PyTorch/Torchvision: 2.5.0/0.20.0.
- Preprocesamiento: 796 × 448, 25 fps de base, stride 2 y 12,5 fps efectivos.
- Modelo: clips de 100 cuadros, solapamiento de 75 cuadros y confianza mínima 0,01, igual al umbral de generación usado por el código oficial antes del postprocesamiento.

Las clases son `pass`, `drive`, `header`, `high pass`, `out`, `cross`, `throw in`, `shot`, `ball player block`, `player successful tackle`, `free kick` y `goal`. El modelo también propone el lado `left` o `right`, pero esa salida no se convierte en identidad nominal.

## Ejecución

Automática:

```bash
bash experiments/soccernet-teamspotting/run.sh
```

CPU o GPU NVIDIA explícitas:

```bash
bash experiments/soccernet-teamspotting/run-cpu.sh
bash experiments/soccernet-teamspotting/run-gpu.sh
```

La primera construcción descarga dependencias y el checkpoint. La variante GPU necesita NVIDIA Container Toolkit. Los resultados quedan fuera de Git en `experiments/soccernet-teamspotting/output/`.

El lanzador detecta la memoria de la GPU y activa AMP por defecto. Una GPU de
6 GB puede usar directamente `run.sh` o `run-real.sh`; no deben ejecutarse otros
modelos al mismo tiempo.

La GPU se puede seleccionar y AMP se puede desactivar si el hardware presenta
inestabilidad numérica:

```bash
MENTOX_CUDA_DEVICE=0 bash experiments/soccernet-teamspotting/run-gpu.sh
MENTOX_CUDA_DEVICE=0 MENTOX_CUDA_AMP=0 \
  bash experiments/soccernet-teamspotting/run-gpu.sh
```

Para ejecutar el vídeo real autorizado con detección automática de GPU:

```bash
bash experiments/soccernet-teamspotting/run-real.sh
```

Antes de ejecutar, compruebe el runtime de Docker:

```bash
sudo docker run --rm --gpus all \
  nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

## Límites

El vídeo de Google Research Football no tiene apariencia de transmisión real y solo contiene dos referencias manuales compatibles con las clases del modelo: pases a 5 y 15 segundos. Una calidad baja es un resultado válido. El experimento nunca publica sus predicciones como `MatchEvent` ni bloquea el flujo sintético.
