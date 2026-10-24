# Google Research Football para DV-US-17

Este experimento genera un clip sintético corto sin modificar el entorno Python 3.12 del backend. Google Research Football se compila dentro de Docker desde el commit oficial `3d9e754720a95621bba6475c4d3b0d56fe919014`.

## Alcance

- Escenario `11_vs_11_stochastic`, limitado a 300 pasos para obtener aproximadamente 30 segundos de vídeo.
- Bots integrados, sin TensorFlow ni checkpoints externos.
- Renderizado no interactivo y exportación a MP4.
- Manifiesto con origen, licencia, commit, tamaño, SHA-256, duración, resolución y FPS.
- Archivos generados fuera de Git en `output/`.

El video es una entrada de DV-US-17. La interfaz web sincronizada pertenece a DV-US-18 y utilizará el MP4 después de revisar el manifiesto y crear la anotación manual.

## Requisitos

- Docker funcionando mediante `sudo docker`.
- Acceso a Internet durante la primera construcción.
- Espacio temporal para compilar el motor C++.

## Ejecución

Desde la raíz del repositorio:

```bash
bash experiments/google-research-football/run.sh
```

La primera construcción puede tardar varios minutos. Las siguientes ejecuciones reutilizan la imagen local.

Resultados esperados:

```text
experiments/google-research-football/output/grf-dv-us-17.mp4
experiments/google-research-football/output/grf-dv-us-17.manifest.json
```

La referencia manual mínima para comprobar localización y sincronización del balón está en `annotations/grf-dv-us-17.csv`. Incluye cajas en píxeles sobre 800 × 450 y coordenadas normalizadas entre 0 y 1. No contiene predicciones de un modelo.

No confirme el directorio `output/`. Antes de subir el video al contenedor privado `authorized-videos`, revise el manifiesto y complete la evidencia de DV-US-17.

## UI

GRF también puede abrir una ventana interactiva mediante X11, pero esa ventana no demuestra la sincronización de Mentox. Para la entrega se usará el MP4 generado dentro de la página de diagnóstico de DV-US-18, con reloj de video, reloj del partido y eventos de origen.

## Referencias

- Repositorio oficial: <https://github.com/google-research/football>
- Docker oficial: <https://github.com/google-research/football/blob/master/gfootball/doc/docker.md>
- Repeticiones y videos: <https://github.com/google-research/football/blob/master/gfootball/doc/saving_replays.md>
- Licencia Apache 2.0: <https://github.com/google-research/football/blob/master/LICENSE>
