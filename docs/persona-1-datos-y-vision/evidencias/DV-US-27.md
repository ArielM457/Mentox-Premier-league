# Evidencia técnica de DV-US-27

## Identificación

- **Historia:** DV-US-27 · Evaluar SoccerNet Game State Reconstruction en GPU.
- **Estado:** contenedor y adaptador MP4 implementados; ejecución GPU completa pendiente.
- **Prioridad:** P2.
- **Última actualización:** 22 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.

## Objetivo

Ejecutar el baseline oficial de SoccerNet GSR en un entorno aislado para evaluar
detección, reidentificación, tracking, calibración, dorsal, equipo y posición 2D
sobre el campo. Esta historia no incorpora todavía el resultado al backend ni
afirma compatibilidad con cualquier MP4.

## Fuente y entorno fijados

| Elemento | Valor |
|---|---|
| Repositorio | `https://github.com/SoccerNet/sn-gamestate` |
| Commit | `1c958345067218297d221e45e1a6405f975f83e0` |
| TrackLab | 1.3.24 |
| Python | 3.9 |
| PyTorch / Torchvision | 1.13.1 / 0.14.1 |
| CUDA del wheel | 11.7 |
| Dataset | SoccerNet GSR público, versión 1.3 o posterior |
| Licencia | GPL-3.0 |

El entorno oficial exige Python menor que 3.10, por lo que no se instala dentro
del backend Python 3.12. Dataset, modelos, cachés y salidas se montan fuera de la
imagen y están excluidos de Git.

## Implementación

| Archivo | Función |
|---|---|
| `experiments/soccernet-gamestate/Dockerfile` | Entorno oficial fijado con CUDA |
| `run_official_baseline.sh` | Validación CUDA y ejecución TrackLab limitada |
| `run-gpu.sh` | Construcción, GPU, volúmenes y salida |
| `run.sh` | Entrada corta al experimento GPU |
| `README.md` | Requisitos, comandos y límites |
| `.gitignore` | Excluye dataset, pesos y resultados |

## Alcance de la primera prueba

La ejecución usa una secuencia del conjunto público de validación y limita el
smoke a 250 cuadros, o a 100 cuando detecta 8 GB de VRAM o menos. La reducción
acota la duración, pero no garantiza que todos los módulos quepan en una GPU de
6 GB. El perfil bajo también reduce los lotes de detección y dorsal a 1, ReID y
tracking a 8, y calibración a 1. Desactiva la evaluación GS-HOTA durante el smoke, conserva
el estado de tracking y genera visualización. La primera ejecución puede
descargar varios GB de datos y modelos.

El baseline oficial está orientado a datasets TrackLab. Existe una solicitud
abierta para inferencia directa sobre cualquier vídeo, por lo que el MP4
autorizado de Mentox requiere un adaptador de dataset posterior. No se declara
esa parte como implementada.

## Matriz de aceptación

| Criterio | Implementación | Estado |
|---|---|---|
| Versiones fijadas | Dockerfile y commit exacto | Verificado estáticamente |
| Aislamiento de Python 3.12 | Contenedor Python 3.9 | Verificado estáticamente |
| Validación de CUDA | Host y `torch.cuda` dentro del contenedor | Pendiente de GPU |
| Artefactos fuera de Git | Volúmenes y `.gitignore` | Verificado estáticamente |
| Smoke acotado | Una secuencia; 100 cuadros con 6-8 GB o 250 con más VRAM | Pendiente de ejecución |
| Identidad prudente | Ninguna conversión automática a `player_id` | Documentado |
| MP4 separado del smoke | Límite explícito | Documentado |

## Comandos

```bash
nvidia-smi
sudo docker run --rm --gpus all \
  nvidia/cuda:11.7.1-base-ubuntu22.04 nvidia-smi

cd /home/university/league/Mentox-Premier-league
bash experiments/soccernet-gamestate/run.sh
```

Para seleccionar GPU y procesar más cuadros:

```bash
MENTOX_CUDA_DEVICE=1 \
MENTOX_GAMESTATE_FRAME_LIMIT=750 \
bash experiments/soccernet-gamestate/run-gpu.sh
```

## Verificaciones locales sin GPU

```bash
bash -n experiments/soccernet-gamestate/run.sh \
  experiments/soccernet-gamestate/run-gpu.sh \
  experiments/soccernet-gamestate/run_official_baseline.sh

git diff --check
```

## Pendiente

1. Construir la imagen en el equipo GPU.
2. Registrar GPU, VRAM, CUDA, descargas, duración y errores.
3. Revisar el vídeo/minimapa y el estado de tracking.
4. Ejecutar el exportador del estado a JSON trazable implementado en DV-US-33.
5. Verificar el adaptador MP4 de DV-US-33 con una inferencia completa.
6. Publicar una muestra como `VisionObservation`, nunca como `MatchEvent` directo.

## Aclaración sobre datos

La primera persona con GPU no ejecutó GameState porque el overview interpretaba
la carpeta vacía como una dependencia que debía entregarse aparte. La guía
oficial de `SoccerNet/sn-gamestate` indica que TrackLab descarga automáticamente
el dataset GameState y los pesos del baseline al ejecutar `tracklab -cn
soccernet`. No hace falta incluirlos en el ZIP. Se necesita conexión, espacio en
disco y, si el proveedor solicita acceso, una cuenta autorizada del operador.

El smoke oficial continúa usando
`experiments/soccernet-gamestate/data/SoccerNetGS/{train,valid,test,challenge}`.
Para vídeos propios, TrackLab 1.3.24 incluye `ExternalVideo`; DV-US-33 lo activa
mediante `dataset=video` y evita fabricar anotaciones SoccerNet. DV-US-27 sigue
pendiente hasta ejecutar el pipeline completo en GPU.

La verificación local del 22 de octubre de 2026 confirmó sintaxis Bash válida,
compilación del adaptador T-DEED, `git diff --check` limpio y **161 pruebas del
backend aprobadas en 0,80 segundos**. No demuestra todavía construcción del
contenedor ni inferencia GameState en GPU.
