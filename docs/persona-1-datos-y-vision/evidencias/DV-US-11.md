# Evidencia técnica de DV-US-11

## Identificación

- **Historia:** DV-US-11 · Evaluar modelos sin comprometer el MVP.
- **Estado:** en progreso; evaluador verificado, experimento real pendiente.
- **Prioridad:** P2.
- **Última verificación:** 9 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.
- **Requisitos relacionados:** DV-RF-17 y DV-RF-18.

## Resultado actual

Existe un evaluador reproducible para contrastar predicciones espaciales y temporales con anotaciones manuales. El informe conserva medio, permiso declarado, hash, modelo, versión, revisión del código, clases, parámetros, origen de las predicciones, calidad, tiempo de procesamiento, falsos positivos y observaciones omitidas.

La historia no está verificada por completo. El repositorio no contiene un vídeo seleccionado ni resultados producidos realmente por Roboflow Sports o SoccerNet. Los ejemplos tienen `prediction_origin=simulated_fixture`, por lo que el evaluador devuelve `pending_real_run` incluso cuando las cifras del ejemplo son perfectas.

## Alcance implementado

- Contrato de medio autorizado con identificador, SHA-256, duración, base del permiso y referencia documental.
- Metadatos obligatorios de proveedor, modelo, versión, revisión, tarea, clases y parámetros.
- Distinción entre predicciones reales y fixtures simulados.
- Evaluación espacial mediante clase, tolerancia temporal e IoU de cajas normalizadas.
- Evaluación de acciones mediante clase y tolerancia temporal configurable.
- Emparejamiento uno a uno para evitar contar una predicción dos veces.
- Precisión, recobrado y F1 calculados de forma reproducible.
- Tiempo total, duración del medio y factor de tiempo real separados de la calidad.
- Listas explícitas de falsos positivos y observaciones manuales no detectadas.
- Decisión `candidate`, `rejected` o `pending_real_run` según origen, umbrales y rendimiento.
- Comparación que conserva informes por tarea y exige mantener el flujo sintético.
- Comando JSON reproducible y ejemplo marcado como no real.

## Fuera del alcance y trabajo pendiente

- Elegir o producir el vídeo autorizado.
- Validar la referencia documental del permiso.
- Crear la anotación manual sobre ese vídeo.
- Fijar commits, pesos y versiones reales de ambos proyectos.
- Instalar sus entornos y revisar compatibilidad, licencias y hardware.
- Ejecutar inferencia y convertir sus salidas al formato del evaluador.
- Medir la calidad real y el tiempo completo de procesamiento.
- Acordar con el equipo los umbrales definitivos de entrada a la demo.

No se añadieron Roboflow Sports, Ultralytics, SoccerNet, pesos ni datasets como dependencias del backend. Esto protege el flujo sintético y evita aceptar licencias o descargas antes de la revisión correspondiente.

## Entradas y resultados

| Entrada | Resultado |
|---|---|
| Medio con referencia de permiso y SHA-256 | Identidad reproducible de la muestra |
| Anotaciones manuales espaciales | Referencias de clase, tiempo y caja |
| Predicciones espaciales | Precisión, recobrado, F1, falsos positivos y omisiones por IoU |
| Anotaciones manuales de acciones | Referencias de clase y tiempo |
| Predicciones de acciones | Las mismas métricas dentro de tolerancia temporal |
| Tiempo de ejecución | Milisegundos y factor respecto a la duración del medio |
| Umbrales de integración | Decisión explicada sin alterar el flujo sintético |

Roboflow Sports y SoccerNet resuelven tareas distintas. Sus cifras se muestran en informes separados; no se ordenan mediante un único número engañoso.

## Cambios técnicos

| Archivo | Cambio | Motivo |
|---|---|---|
| `apps/backend/src/match_intelligence/application/vision_evaluation.py` | Contratos, métricas y decisiones | Evaluar exportaciones sin acoplar el MVP a los modelos |
| `apps/backend/scripts/evaluate_vision_predictions.py` | Entrada y salida JSON | Repetir un experimento desde comandos |
| `apps/backend/tests/test_vision_evaluation.py` | Once pruebas automatizadas | Verificar métricas, diagnósticos y aislamiento |
| `docs/persona-1-datos-y-vision/experimentos-vision/README.md` | Protocolo experimental | Explicar permiso, fijación y ejecución |
| `docs/persona-1-datos-y-vision/experimentos-vision/input.example.json` | Plantilla simulada | Mostrar el contrato sin afirmar resultados reales |
| Documentos de Persona 1 | Estado y vínculo de evidencia | Mantener trazabilidad honesta |

## Diseño

```text
vídeo permitido ────────┐
anotación manual ───────┤
configuración fijada ───┼─► VisionExperimentEvaluator
predicciones exportadas ┤          │
tiempo medido ──────────┘          ├─► calidad + FP + omisiones
                                  ├─► tiempo de procesamiento
                                  └─► decisión experimental

flujo sintético ─────────────────────► permanece obligatorio
```

El evaluador recibe predicciones exportadas. No importa ni ejecuta SDK de visión. Así un fallo, una licencia incompatible o un resultado insuficiente no afecta el generador, la validación, Event Hubs, Blob Storage ni la sincronización sintética.

## Métricas

### Detección espacial

Una predicción coincide con una anotación si tiene la misma clase, está dentro de la tolerancia temporal y su intersección sobre unión es igual o superior al umbral. Cada predicción solo puede coincidir una vez.

### Detección temporal de acciones

Una predicción coincide si tiene la misma clase y la diferencia absoluta entre tiempos no supera la tolerancia. Entre varias candidatas se elige la más cercana.

### Calidad

- `precision = TP / (TP + FP)`.
- `recall = TP / (TP + FN)`.
- `F1 = 2 × precision × recall / (precision + recall)`.

Cuando un denominador es cero, la métrica correspondiente vale cero. Los identificadores de FP y FN se conservan para revisión cualitativa.

### Rendimiento

`realtime_factor = processing_time_ms / media_duration_ms`. Calidad y rendimiento aparecen en secciones distintas. Un valor bajo de tiempo no compensa omisiones, y una calidad alta no demuestra ejecución útil para una demo en directo.

## Regla de decisión

- `simulated_fixture` siempre produce `pending_real_run`.
- Una ejecución real que no alcanza un umbral produce `rejected` con motivos.
- Una ejecución real que alcanza todos los umbrales produce `candidate`, no integración automática.
- `VisionComparison.synthetic_flow_required` siempre permanece verdadero.

Los umbrales del archivo de ejemplo son ilustrativos. El equipo todavía debe acordar los valores usados para la decisión final.

## Consulta de documentación vigente

Se consultó Context7 el 9 de octubre de 2026:

- `/roboflow/sports`: el ejemplo de fútbol se instala desde el repositorio, utiliza YOLOv8 para jugadores y campo, y combina SigLIP, UMAP y KMeans para clasificación por equipo. Las licencias de componentes deben revisarse por separado.
- `/soccernet/sn-teamspotting`: Team Ball Action Spotting extiende la tarea de 12 acciones, añade el equipo y usa tolerancias de hasta un segundo; T-DEED figura como línea base.

También se verificaron las fuentes oficiales actuales: [ejemplo de fútbol de Roboflow Sports](https://github.com/roboflow/sports/blob/main/examples/soccer/README.md), [SoccerNet Team Ball Action Spotting](https://github.com/SoccerNet/sn-teamspotting) y sus [reglas del reto](https://github.com/SoccerNet/sn-teamspotting/blob/main/ChallengeRules.md).

La consulta orienta el protocolo. No demuestra que esas herramientas estén instaladas, ejecutadas o aprobadas para este proyecto.

## Cobertura de criterios de aceptación

| Criterio | Implementación o evidencia | Estado |
|---|---|---|
| El vídeo tiene permiso documentado | `AuthorizedMedia` exige base y referencia; la guía explica el registro | Pendiente: no se eligió vídeo |
| Registrar modelo, versión, clases y configuración | `ModelConfiguration` valida todos los campos | Cumplido para el contrato; faltan valores reales |
| Informar calidad y tiempo por separado | `VisionEvaluationReport.quality` y `.processing` | Verificado localmente |
| Documentar falsos positivos y acciones no detectadas | Identificadores explícitos en cada informe | Verificado localmente |
| Resultado insuficiente no bloquea el flujo sintético | Decisiones experimentales aisladas y `synthetic_flow_required=True` | Verificado localmente |

DV-US-11 permanece en progreso porque los dos primeros puntos necesitan el vídeo y las ejecuciones reales.

## Pruebas automatizadas

| Prueba | Comportamiento comprobado |
|---|---|
| `test_media_requires_documented_permission` | Referencia de permiso obligatoria |
| `test_model_records_version_classes_revision_and_configuration` | Metadatos completos del modelo |
| `test_spatial_evaluation_reports_quality_false_positives_and_misses` | IoU, métricas y diagnósticos espaciales |
| `test_action_evaluation_uses_temporal_tolerance` | Tolerancia y diagnósticos temporales |
| `test_quality_and_processing_are_reported_separately` | Calidad y rendimiento independientes |
| `test_simulated_predictions_cannot_qualify_a_model_for_the_demo` | Fixtures no habilitan modelos |
| `test_insufficient_actual_result_is_rejected_with_reasons` | Rechazo y motivos trazables |
| `test_sufficient_actual_result_is_only_marked_as_candidate` | Éxito no equivale a integración automática |
| `test_comparison_keeps_task_specific_reports_and_synthetic_fallback` | Comparación correcta y respaldo obligatorio |
| `test_undeclared_prediction_class_is_rejected` | Clases fuera de configuración rechazadas |
| `test_evaluation_failure_does_not_block_the_synthetic_match` | Generador sintético operativo tras un fallo |

## Reproducción

Pruebas específicas:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_vision_evaluation.py -q
```

Ejemplo simulado:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/evaluate_vision_predictions.py \
  docs/persona-1-datos-y-vision/experimentos-vision/input.example.json
```

Suite completa:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 pytest -q
```

## Entorno verificado

| Componente | Versión |
|---|---|
| Python | 3.12.13 |
| uv | 0.11.32 |
| pytest | 9.1.1 |
| Roboflow Sports | No instalado; revisión real pendiente |
| SoccerNet | No instalado; revisión real pendiente |
| Vídeo | No seleccionado |

## Resultado local

Pruebas específicas:

```text
...........                                                              [100%]
11 passed in 0.08s
```

El comando de ejemplo devolvió `pending_real_run`, como exige la protección contra resultados simulados.

Suite completa:

```text
........................................................................ [ 67%]
..................................                                       [100%]
106 passed in 0.63s
```

`compileall`, `uv lock --check` y `git diff --check` terminaron correctamente y sin errores.

## Limitaciones y riesgos

- Declarar una referencia de permiso no verifica jurídicamente la autorización.
- Las etiquetas exportadas deben mapearse de forma explícita; el evaluador rechaza clases no declaradas.
- La métrica espacial implementada es una evaluación simple de cajas, no COCO mAP.
- La métrica temporal implementada informa precisión, recobrado y F1, no reemplaza el mAP oficial de SoccerNet.
- Comparar tareas distintas requiere lectura separada y revisión cualitativa.
- `prediction_origin=actual_model` es una declaración del ejecutor; la evidencia debe incluir comando, revisión, pesos y salida original.
- Los pesos, datasets y ejemplos externos pueden tener condiciones distintas al código del repositorio.
- El ejemplo contiene marcadores y no constituye una evaluación.

## Siguiente verificación necesaria

1. Seleccionar el vídeo y aprobar su uso.
2. Generar el SHA-256 y la anotación manual.
3. Fijar commits y pesos de Roboflow Sports y SoccerNet.
4. Revisar licencias de todos los componentes y datos.
5. Ejecutar ambos modelos sobre la misma muestra y medir el tiempo completo.
6. Exportar predicciones al contrato documentado.
7. Ejecutar el evaluador y revisar cada falso positivo y omisión.
8. Acordar umbrales y decidir si alguno queda como candidato para la demo.

## Ampliación del contrato de observaciones · 18 de octubre de 2026

Se añadió `domain/vision.py` con dos contratos estrictos y separados. `SoccerNetActionRecord` conserva fotograma, tiempo de partido, tiempo de vídeo, tipo de evento, equipo con posesión, color de camiseta, jugador opcional, posición del balón y confianza. `RoboflowDetectionRecord` conserva clase, confianza, caja limitadora, `track_id`, equipo, color, identidad opcional, posición de campo y retraso de procesamiento.

`tests/test_vision_records.py` verifica ambos registros y el rechazo de una caja limitadora inválida. Esto completa el modelo local de entrada, pero no cambia el estado general de DV-US-11: no se ejecutó SoccerNet ni Roboflow Sports y no existe evidencia sobre vídeo real.
