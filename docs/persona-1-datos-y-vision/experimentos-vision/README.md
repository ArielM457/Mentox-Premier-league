# Experimentos de visión de DV-US-11

Esta carpeta define cómo comparar predicciones exportadas con una muestra manual. No contiene vídeos, pesos, predicciones reales ni resultados de Roboflow Sports o SoccerNet.

## Condiciones antes de ejecutar

1. Elegir un vídeo propio, generado por el proyecto o con autorización escrita.
2. Guardar fuera de Git el vídeo si su permiso no autoriza redistribuirlo.
3. Calcular su SHA-256 y registrar una referencia comprobable al permiso.
4. Anotar manualmente la misma muestra para las tareas que se evaluarán.
5. Fijar repositorio, revisión, modelo, pesos, clases y parámetros de cada herramienta.
6. Medir el procesamiento completo, sin mezclarlo con las métricas de calidad.

`permission_reference` debe apuntar al registro de autorización adoptado por el equipo. Su presencia en el JSON no demuestra por sí sola que el permiso sea válido.

## Tareas separadas

- `spatial_detection`: compara clase y caja normalizada mediante IoU. Es la tarea esperada para las salidas espaciales de Roboflow Sports.
- `action_spotting`: compara clase y tiempo dentro de una tolerancia en milisegundos. Es la tarea esperada para SoccerNet Team Ball Action Spotting.

No se comparan directamente los valores de ambas tareas. Cada modelo se contrasta con la parte correspondiente de la anotación manual.

## Ejecución

Copie `input.example.json` fuera de su ruta original, reemplace todos los marcadores y agregue anotaciones y predicciones reales:

```bash
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/evaluate_vision_predictions.py \
  docs/persona-1-datos-y-vision/experimentos-vision/input.example.json
```

Para conservar el resultado:

```bash
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/evaluate_vision_predictions.py \
  <entrada-real.json> --output <informe.json>
```

El informe separa `quality` de `processing`, y enumera `false_positive_ids` y `missed_observation_ids`.

## Regla para decisiones

Una entrada con `prediction_origin=simulated_fixture` siempre produce `pending_real_run`, aunque sus cifras sean perfectas. Solo una ejecución real puede resultar `candidate` o `rejected`. `candidate` significa que superó los umbrales declarados; todavía requiere revisión de licencia, permiso, integración y comportamiento visual.

El flujo sintético de DV-US-01 a DV-US-10 sigue siendo obligatorio cualquiera que sea el resultado experimental.
