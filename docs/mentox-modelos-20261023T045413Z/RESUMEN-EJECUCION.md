# Ejecución de modelos en WSL · 23 de octubre de 2026

## Entorno

- Ubuntu 24.04 en WSL 2; repositorio montado desde Windows en `/mnt/c/Users/Usuario/Downloads/Mentox-Premier-league`.
- GPU NVIDIA GeForce RTX 3060 Laptop GPU, 6144 MiB; controlador 592.82. Docker 29.9.2 y Compose v5.6.1.
- La prueba `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi` terminó correctamente.
- Se instaló `uv` 0.13.5 y Python 3.12.15 en WSL. El entorno Linux del backend quedó en `/tmp/mentox-backend-venv` para evitar el `.venv` de Windows.
- El vídeo autorizado `2e57b9_0.mp4` estaba presente. SHA-256: `7788719b32b944e42d8f1024fb4802f681bc2053d6301218a5bff6705b549f96`. El vídeo no está incluido en el paquete.

## Resultados

| Prueba | Resultado |
|---|---|
| Roboflow Sports | CUDA, FP16, 640 px, campo cada 10 cuadros. 750 cuadros; 16 011 detecciones del modelo general, 313 del balón y 75 observaciones del campo; 51 282,675 ms de procesamiento. JSON y MP4 anotado generados. |
| TeamSpotting | CUDA. 375 cuadros efectivos en 15 clips; 127 observaciones; 5 659,923 ms de procesamiento. JSON generado. |
| GameState | No ejecutado: falta el conjunto GSR autorizado en `experiments/soccernet-gamestate/data/`. No se descargó material restringido. |
| Backend | 159 pruebas aprobadas y 2 fallidas. Las dos fallas comparan el conteo anterior `16018` con el nuevo `16324` de Roboflow. |

Los comandos de Roboflow y TeamSpotting fueron los `run-real.sh` de la guía. Sus registros completos están en `roboflow-gpu.log` y `teamspotting-gpu.log`. El registro de pruebas está en `backend-tests-wsl.log`.

## Revisión visual y límites

Las capturas de los segundos 5, 15 y 25 están en `screenshots/`. En los segundos 5 y 15 se ven cajas sobre múltiples jugadores y árbitros. Las etiquetas se superponen y no permiten contar aciertos con fiabilidad. Hay detecciones de balón dibujadas, pero no se puede confirmar su precisión con estas capturas. No se revisó manualmente cada cuadro.

El vídeo real no tiene anotaciones manuales completas para las clases evaluadas. Por eso los lanzadores omitieron la evaluación de precisión y los conteos anteriores son observaciones experimentales. Ninguna predicción se elevó a `MatchEvent`. No se ejecutó la fusión, la interfaz ni Azure, ya que el alcance solicitado por el overview es la prueba de modelos GPU.

El primer intento de pruebas del backend encontró un `.venv` de Windows incompatible con Linux; se repitió usando un entorno Linux separado. Los 2 fallos restantes están relacionados con el cambio de conteo de Roboflow y requieren actualizar la expectativa de las pruebas o desacoplarla de una salida generada.

El recolector oficial copió también `dv-us-21-report.json`, que ya existía antes de esta ejecución. No se recalculó ni verificó la fusión en esta sesión; ese archivo se conserva únicamente como artefacto previo y no como resultado de esta prueba GPU.
