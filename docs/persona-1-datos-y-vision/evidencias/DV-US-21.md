# Evidencia técnica de DV-US-21

## Identificación

- **Historia:** DV-US-21 · Calibrar identidad y fusión con observaciones reales.
- **Estado:** verificada experimentalmente; no autorizada para publicar `MatchEvent`.
- **Prioridad:** P2.
- **Última verificación:** 23 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.
- **Requisitos relacionados:** DV-RF-19, DV-RF-20 y DV-RNF-03.

## Resultado

Se cruzaron las exportaciones reales de Roboflow Sports y SoccerNet producidas sobre el mismo clip permitido de 30 segundos. El proceso conservó acciones, balón, jugador, tiempos, cajas, confianzas y `track_id` originales. No asignó `player_id` y no produjo ningún `MatchEvent`.

Con la política seleccionada se obtuvieron dos hipótesis iniciales alrededor de 19,5 segundos. Ambas apuntaban al mismo `track_id` dentro de 160 ms y representaban clases competidoras para una sola jugada. La deduplicación conservó el `pass` con mayor confianza de acción y suprimió `high pass` como hipótesis competidora. El resultado final fue un candidato revisable.

## Entradas

| Entrada | Resultado |
|---|---:|
| Vídeo | 1920 × 1080, 25 FPS, 30 segundos |
| SHA-256 | `7788719b32b944e42d8f1024fb4802f681bc2053d6301218a5bff6705b549f96` |
| Roboflow | 16.018 detecciones; todas con `track_id` |
| SoccerNet | 127 acciones temporales |
| Acciones con confianza ≥ 0,10 | 23 |

El MP4 no se confirma en Git. La fuente y los términos de acceso están referenciados por los scripts `run-real.sh`; el archivo se usa localmente y no se redistribuye.

## Política calibrada

| Parámetro | Valor | Justificación |
|---|---:|---|
| Ventana temporal | 120 ms | El vídeo aporta un cuadro cada 40 ms y SoccerNet uno cada 80 ms; 120 ms cubre un cuadro de cada fuente sin abrir una ventana extensa |
| Distancia de imagen | 0,12 | Distancia entre centros sobre ancho y alto normalizados; se exploraron 0,08, 0,12 y 0,18 |
| Margen de ambigüedad | 0,01 | Si dos tracks distintos quedan casi a la misma distancia, no se selecciona ninguno |
| Confianza mínima de acción | 0,10 | Reduce las 127 salidas exploratorias a 23 acciones y evita usar el ruido del umbral 0,01 |
| Conflicto temporal por track | 250 ms | Clases competidoras sobre el mismo track se consideran una sola jugada; conserva la mayor confianza de acción |

La distancia espacial sigue expresada en coordenadas de imagen. No equivale a metros ni a coordenadas del campo porque todavía no existe homografía. Por ello el resultado permanece como `FusionCandidate` y no entra en `ObservationFusionService` como evento confirmado.

## Resultado cuantitativo

| Clasificación | Cantidad |
|---|---:|
| Acciones evaluadas | 127 |
| Descartadas por confianza inferior a 0,10 | 104 |
| Sin balón dentro de 120 ms | 21 |
| Hipótesis iniciales | 2 |
| Hipótesis competidoras suprimidas | 1 |
| Candidatos finales | 1 |
| `MatchEvent` producidos | 0 |
| Identidades nominales asignadas | 0 |

## Recalibración con la ejecución GPU

El 23 de octubre se recibió una nueva exportación GPU con los tres modelos
espaciales. No se reutilizó el informe anterior: se volvió a ejecutar la
calibración sobre las 16.324 observaciones espaciales y las 127 acciones
temporales del paquete recibido.

| Clasificación | Cantidad |
|---|---:|
| Acciones evaluadas | 127 |
| Descartadas por confianza inferior a 0,10 | 104 |
| Sin balón dentro de 120 ms | 1 |
| Ambiguas | 3 |
| Hipótesis iniciales | 19 |
| Hipótesis competidoras suprimidas | 7 |
| Candidatos finales | 12 |
| `MatchEvent` producidos | 0 |

El informe nuevo está en
`docs/mentox-modelos-20261023T045413Z/resultados/dv-us-21-report-recalculado.json`.
El aumento de candidatos se debe principalmente al detector especializado de
balón; no prueba que las asociaciones sean correctas. Continúan siendo
hipótesis para revisión manual.

## Candidato conservado

| Campo | Valor |
|---|---|
| Acción | `soccernet-0083` · `pass` · 19.680 ms |
| Equipo visual | `right`; no asociado a un equipo nominal |
| Confianza de acción | 0,5252 |
| Balón | `frame-0491-det-022` · 19.640 ms · track 294 |
| Jugador | `frame-0493-det-003` · 19.720 ms · track 140 |
| Diferencia acción-balón | 40 ms |
| Diferencia acción-jugador | 40 ms |
| Distancia normalizada en imagen | 0,0185 |
| Confianza conservadora | 0,1066 |
| `player_id` | Ausente |

La revisión del cuadro anotado muestra el balón junto al jugador con track 140. Esto hace plausible la asociación espacial, pero un solo cuadro no confirma recepción, control ni identidad. El registro continúa siendo candidato.

## Falso emparejamiento evitado

SoccerNet también produjo `soccernet-0082`, `high pass`, a 19.520 ms. Coincidía con el mismo balón y track 140. Publicar ambas salidas habría contado dos acciones sobre una sola secuencia. La regla de conflicto conservó `pass`, cuya confianza de acción era 0,5252 frente a 0,3362, y registró `high pass` como hipótesis suprimida.

## Caso no fusionado revisado

`soccernet-0017` propuso `pass` a 4.160 ms con confianza 0,5174. Roboflow no detectó un balón dentro de 120 ms, aunque sí había jugadores seguidos. El sistema conservó la acción original y registró `insufficient_evidence`; no eligió al jugador más cercano sin balón.

## Cambios técnicos

| Archivo | Cambio |
|---|---|
| `candidate_fusion.py` | Contratos de acción, detección espacial, política, candidato y decisiones |
| `calibrate_observation_fusion.py` | Importación de exportaciones, cuadrícula de políticas e informe reproducible |
| `integrated_pipeline.py` | Comprueba SHA-256 de ambas entradas antes de aceptar el informe de fusión |
| `test_candidate_fusion.py` | Pruebas de trazabilidad, identidad ausente, evidencia insuficiente, ambigüedad y conflictos |
| `run-real.sh` de ambos experimentos | Entrada real configurable y salidas separadas |
| `vision_evaluation.py` | Procedencia `source_terms` para medios usados bajo términos documentados |

## Reproducción

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/calibrate_observation_fusion.py \
  experiments/roboflow-sports/output-real/roboflow-sports-predictions.json \
  experiments/soccernet-teamspotting/output-real/soccernet-predictions.json \
  --output experiments/fusion-calibration/output/dv-us-21-report.json
```

Pruebas específicas:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_candidate_fusion.py \
         apps/backend/tests/test_observation_fusion.py \
         apps/backend/tests/test_visual_identity.py -q
```

Suite completa:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 pytest -q
```

Resultado histórico: `151 passed in 0.69s`. Tras incorporar los artefactos GPU,
la protección contra informes obsoletos y las pruebas correspondientes, la
suite se volvió a ejecutar el 23 de octubre de 2026; el resultado vigente se
registra al final de esta evidencia.

El informe contiene fecha de generación, por lo que su SHA-256 cambia en cada
recalibración. La integridad relevante se conserva dentro del documento con las
huellas exactas de los JSON de Roboflow y SoccerNet usados como entrada.

## Cobertura de criterios

| Criterio | Evidencia | Estado |
|---|---|---|
| Tolerancias justificadas con FPS y ejemplos | Cuadrícula 80/120/200 ms y 0,08/0,12/0,18; revisión a 4.160 y 19.680 ms | Cumplido para imagen, no para campo |
| Sin evidencia nominal conserva track y omite jugador | Candidato con track 140 y `player_id=None` | Cumplido |
| Fuentes conservadas | IDs de SoccerNet, balón y jugador dentro del candidato | Cumplido |
| Contradicción y evidencia insuficiente no generan evento | Conflicto `pass/high pass`, ausencia de balón y pruebas heredadas de DV-US-13 | Cumplido |
| Aciertos, falsos emparejamientos y no fusionados | Candidato plausible, duplicado suprimido y caso de 4.160 ms | Cumplido experimentalmente |
| Flujo sintético continúa operativo | Suite completa con 162 pruebas | Cumplido |

## Limitaciones

- El clip se usa según la referencia publicada por Roboflow; no se redistribuye.
- Falta una anotación manual completa del clip para calcular precisión, recobrado y F1.
- La cámara se mueve y la distancia en imagen no representa distancia sobre el campo.
- Los 112 tracks de Roboflow muestran fragmentación durante los 30 segundos.
- `left/right` de SoccerNet no confirma el equipo real.
- No existe evidencia nominal de jugadores.
- Un candidato no es un hecho y no se publica en Event Hubs.

## Integridad entre inferencia y fusión

Los informes nuevos incluyen el SHA-256 exacto de los JSON de Roboflow y
SoccerNet. El backend rechaza el informe si cualquiera de esos archivos cambia.
Para informes antiguos sin esas huellas también contrasta los conteos y los
identificadores referenciados. Esto impide presentar como actuales candidatos
calculados con una inferencia anterior.

Verificación final: **162 pruebas aprobadas en 1,06 segundos**, compilación
Python, sintaxis Bash y `git diff --check` sin errores.

## Decisión

DV-US-21 queda verificada como calibración experimental y barrera de seguridad. La fusión automática permanece fuera del flujo principal: un candidato puede mostrarse para revisión, pero el partido sintético continúa siendo la fuente operativa. El siguiente paso es DV-US-22.
