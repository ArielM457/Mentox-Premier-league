# Evidencia técnica de DV-US-20

## Identificación

- **Historia:** DV-US-20 · Ejecutar SoccerNet sobre la muestra.
- **Estado:** verificada experimentalmente en CPU y GPU sobre vídeo permitido; calidad pendiente de anotación manual completa.
- **Prioridad:** P2.
- **Última actualización:** 22 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.

## Objetivo

Ejecutar el baseline oficial T-DEED de SoccerNet Team Ball Action Spotting sobre el MP4 sintético permitido, exportar observaciones temporales con `prediction_origin=actual_model` y evaluarlas sin incorporarlas automáticamente al flujo principal.

## Fuente y versiones fijadas

| Elemento | Valor |
|---|---|
| Repositorio | `https://github.com/SoccerNet/sn-teamspotting` |
| Commit | `091fed2fc35c33f7489f3596958a2fe385e37d65` |
| Modelo | T-DEED baseline 2025 |
| Checkpoint | `checkpoint_best.pt` |
| SHA-256 del checkpoint | `ed7c558d575eba1918be8f67813571723962eeff807dba68a12a2d794dd1c72a` |
| Python | 3.12 |
| PyTorch / Torchvision | 2.5.0 / 0.20.0 |
| Timm | 1.0.11 |
| OpenCV | 4.10.0.84 |

## Licencias y acceso

- El repositorio declara GPL-3.0.
- El conjunto SN-BAS-2025 publicado en Hugging Face declara GPL-3.0 y ocupa aproximadamente 19,3 GB.
- Los vídeos de SoccerNet históricos pueden requerir autorización o NDA.
- Este experimento no descarga el dataset ni sus vídeos.
- El README oficial publica un checkpoint de 49,6 MB en Google Drive, pero no declara una licencia separada inequívoca para el archivo.
- El checkpoint se descarga dentro de Docker, no se confirma en Git y no se redistribuye.
- El vídeo usado fue generado por el proyecto y está documentado en DV-US-17.

## Configuración

| Parámetro | Valor |
|---|---:|
| Resolución | 796 × 448 |
| FPS de preprocesamiento oficial | 25 |
| Stride | 2 |
| FPS efectivos del modelo | 12,5 |
| Longitud de clip | 100 cuadros |
| Solapamiento | 75 cuadros |
| Confianza mínima | 0,01 |
| Ventana NMS | 12 cuadros |
| Tolerancia de evaluación | 1.000 ms |

Las doce clases son pase, conducción, cabezazo, pase alto, fuera, centro, saque de banda, tiro, bloqueo jugador-balón, entrada exitosa, tiro libre y gol. La salida izquierda/derecha se conserva como equipo visual, no como identidad de jugador.

## Anotación disponible

El vídeo sintético contiene acciones preparadas manualmente en DV-US-18. Solo dos pertenecen al catálogo de SoccerNet: `pass` a 5.000 y 15.000 ms. Recuperación, cambio de posesión y presión quedan fuera porque el checkpoint no declara esas clases.

## Implementación

| Archivo | Función |
|---|---|
| `experiments/soccernet-teamspotting/Dockerfile` | Entorno, código y checkpoint fijados |
| `run_inference.py` | Preprocesamiento, T-DEED, NMS y exportación |
| `run.sh` | Selección automática CPU/GPU |
| `run-cpu.sh` | CPU explícita |
| `run-gpu.sh` | CUDA explícita |
| `run_variant.sh` | Construcción, inferencia y evaluación |
| `annotations/grf-dv-us-17-actions.csv` | Referencia temporal manual |
| `README.md` | Uso y límites |

Se desactiva la descarga de pesos ImageNet de Timm porque el checkpoint contiene el estado entrenado completo. Dos correcciones locales y reproducibles permiten CPU y GPU: el cabezal conjunto respeta el dispositivo actual y la salida de equipo se crea en el mismo dispositivo que la predicción.

Context7 confirmó la práctica recomendada de PyTorch para cargar un `state_dict`: `torch.load(..., weights_only=True, map_location=device)` limita la deserialización a pesos y permite remapear el checkpoint al dispositivo elegido. El exportador aplica ambos parámetros antes de llamar a `load_state_dict` mediante la interfaz del modelo.

## Criterios

| Criterio | Estado |
|---|---|
| Commit, checkpoint, clases, dispositivo, preprocesamiento y parámetros | Preparado |
| Licencias de código, pesos, dataset y vídeo | Revisadas; checkpoint sin licencia separada |
| Predicciones reales `actual_model` | Pendiente de ejecución |
| Calidad temporal, tiempo y errores | Pendiente de ejecución |
| Revisión de falso positivo y omisión | Pendiente de salida |
| Decisión `candidate` o `rejected` | Pendiente del informe |

## Comando pendiente

```bash
cd /home/university/league/Mentox-Premier-league
bash experiments/soccernet-teamspotting/run.sh
```

La historia no se marcará como verificada hasta completar la inferencia, validar los JSON, revisar instantes del vídeo y conservar el resultado del evaluador.

## Ejecución sobre vídeo permitido y preparación GPU

La ejecución posterior sobre el MP4 autorizado de 30 segundos produjo 127
observaciones en 90.792,692 ms de CPU: 48 conducciones, 46 pases, 16 pases
altos, 7 salidas, 7 cabezazos y 3 saques de banda. El modelo asignó 64 al lado
izquierdo y 63 al derecho. No se calculó precisión porque el vídeo real todavía
no tiene anotaciones manuales para las doce clases.

La ruta CUDA admite ahora `MENTOX_CUDA_DEVICE`, valida el índice solicitado,
activa AMP de inferencia de forma configurable, sincroniza CUDA antes de medir y
registra nombre, memoria, versión CUDA y conteo de GPU. `run-gpu.sh` valida
`nvidia-smi` antes de construir. También consulta la VRAM y mantiene AMP activo
de forma automática con una GPU de 6 GB. La prueba directa en el nuevo equipo es:

```bash
bash experiments/soccernet-teamspotting/run-real.sh
```

AMP puede desactivarse ante una incompatibilidad:

```bash
MENTOX_CUDA_DEVICE=0 MENTOX_CUDA_AMP=0 \
bash experiments/soccernet-teamspotting/run-real.sh
```

## Verificación previa

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python -m py_compile \
  experiments/soccernet-teamspotting/run_inference.py

UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_vision_evaluation.py -q

bash -n experiments/soccernet-teamspotting/run*.sh
git diff --check
```

Resultado: compilación con Python 3.12 correcta, 11 pruebas del evaluador aprobadas en 0,09 segundos, scripts Bash válidos y diff sin errores de espacios. La construcción Docker y la inferencia continúan pendientes de la ejecución del usuario porque requieren su acceso local a `sudo`.

## Primer intento de construcción y ejecución

La selección automática eligió CPU. Docker construyó correctamente la imagen, instaló PyTorch y las dependencias, fijó el commit oficial y descargó el checkpoint. T-DEED comenzó a crear sus bloques GSF, pero la inferencia se detuvo antes de cargar los pesos porque el adaptador no había trasladado tres parámetros de la configuración oficial:

```text
AttributeError: 'types.SimpleNamespace' object has no attribute 'n_layers'
```

Se añadieron los valores exactos de `SoccerNetBall_baseline.json`: `n_layers=2`, `sgp_ks=9` y `sgp_r=4`. No se generaron predicciones en este intento. Las capas de dependencias, repositorio y checkpoint permanecen en la caché de Docker.

## Primera inferencia completa

La segunda ejecución cargó el checkpoint y procesó los 15 clips, equivalentes a 375 cuadros a 12,5 fps. Con el umbral inicial de 0,10 no generó predicciones.

| Medida | Resultado |
|---|---:|
| Cuadros procesados | 375 |
| Predicciones | 0 |
| Tiempo de procesamiento | 280.435,798 ms |
| Factor de tiempo real | 9,3479 |
| Verdaderos positivos | 0 |
| Falsos positivos | 0 |
| Omisiones | 2 |
| F1 | 0,00 |
| Decisión del evaluador | `rejected` |

Las dos omisiones fueron `ann-pass-005` y `ann-pass-015`. El resultado demuestra que el modelo no reconoce las acciones sintéticas con confianza 0,10, pero no permite revisar un falso positivo porque no produjo ninguna salida.

El código oficial de `util/eval.py` genera eventos desde un umbral de 0,01 antes de aplicar NMS o Soft-NMS. Se alineó el experimento con ese valor para una segunda inferencia. Esta calibración puede aumentar falsos positivos y queda registrada; no reemplaza ni oculta el resultado obtenido con 0,10.

Integridad de la primera inferencia:

| Artefacto local | SHA-256 |
|---|---|
| `soccernet-predictions.json` | `aa3cb881fd4aa54dea77a647eda791a91e0c89bee88d0a766128722c8c811737` |
| `soccernet-evaluation-input.json` | `f57485abaf3096d675ab54acc25eb843bc5edd6798c7db112d9e7f1049cc0150` |
| `soccernet-evaluation-report.json` | `b82615d0a1f7770bebe3d7cae1872d5a9217411af604f91c41091372c9725a4b` |

La siguiente ejecución sobrescribirá los archivos locales de `output/`, pero estos hashes y resultados conservan la trazabilidad del primer umbral.

## Ejecución GPU de 6 GB

El 23 de octubre de 2026 se ejecutó el mismo vídeo permitido en WSL 2 con una
NVIDIA GeForce RTX 3060 Laptop de 6144 MiB, CUDA 12.4, PyTorch 2.5.0 y AMP. Los
15 clips y 375 cuadros efectivos terminaron sin error.

| Medida | Resultado |
|---|---:|
| Predicciones | 127 |
| Tiempo de procesamiento | 5.659,923 ms |
| Duración del vídeo | 30.000 ms |
| Velocidad respecto al vídeo | 5,30 veces más rápida |
| Confianza media | 0,0723 |
| Predicciones con confianza ≥ 0,10 | 23 |
| Predicciones con confianza ≥ 0,50 | 3 |

La distribución permaneció en 48 conducciones, 46 pases, 16 pases altos, 7
cabezazos, 7 salidas y 3 saques de banda. Esto verifica dispositivo, ejecución y
exportación, pero no precisión: el vídeo carece de anotaciones manuales completas
para las doce clases. El JSON recibido tiene SHA-256
`e15e9265cf913e648968a02a9799e9d87f3eb83e921db208ddb0efc79bd248a3`.
