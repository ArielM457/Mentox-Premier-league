# Evidencia técnica de DV-US-13

## Identificación

- **Historia:** DV-US-13 · Fusionar observaciones con trazabilidad.
- **Estado:** política y servicio verificados localmente; vídeo real pendiente.
- **Prioridad:** P2.
- **Última verificación:** 9 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.
- **Requisitos relacionados:** DV-RF-19 y DV-RNF-03.

## Objetivo comprobado

El backend puede combinar una observación temporal de acción con una observación espacial de seguimiento únicamente cuando ambas son compatibles por partido, `track_id`, equipo, tiempo y posición. El resultado conserva los dos objetos originales, sus identificadores, las diferencias medidas, el seguimiento y la identidad resuelta cuando existe.

Una contradicción nunca produce `MatchEvent`. La falta de tiempo compatible, posición, seguimiento o equipo devuelve `insufficient_evidence`, incluye motivos revisables y conserva las entradas para diagnóstico.

## Alcance implementado

- `ActionObservation` para acciones inferidas con tiempo deportivo y de vídeo.
- `FusionPolicy` con tolerancia temporal en milisegundos y espacial en coordenadas normalizadas del campo.
- `ObservationFusionService` independiente de SDK y modelos.
- Coincidencia obligatoria de partido y `track_id`.
- Detección de contradicción entre equipos.
- Distancia temporal absoluta.
- Distancia euclidiana entre posiciones normalizadas.
- Estado `fused`, `insufficient_evidence` o `contradiction`.
- Evento `MatchEvent 1.0` con fuente `video_model` solo al superar todas las comprobaciones.
- Identificador de evento determinista a partir de las dos observaciones.
- Confianza conservadora igual al mínimo de los dos detectores.
- `player_id` únicamente si DV-US-12 entregó una identidad confirmada.
- Objetos e identificadores originales dentro de todos los resultados, incluso los rechazados.

## Fuera del alcance

- No se ejecutaron Roboflow Sports ni SoccerNet.
- No se utilizaron observaciones de un vídeo real.
- No se calibraron las tolerancias con frecuencia de cuadros, resolución o errores medidos.
- No se agregó almacenamiento permanente de resultados de fusión.
- No se implementó búsqueda entre colecciones grandes ni selección entre múltiples candidatos.
- No se fusionaron trayectorias completas ni se corrigieron cambios de `track_id`.
- No se publica automáticamente el evento fusionado en Event Hubs.

## Entradas y resultados

| Entrada | Resultado |
|---|---|
| Acción y track compatibles | `FusedVideoEvent` con `MatchEvent` y dos fuentes completas |
| Diferencia temporal superior a la política | Sin evento, estado `insufficient_evidence` y motivo |
| Distancia espacial superior a la política | Sin evento, estado `insufficient_evidence` y motivo |
| Falta posición, seguimiento o equipo | Sin evento y limitaciones explícitas |
| Partido, track o equipo contradictorio | Sin evento, estado `contradiction` |
| Identidad no confirmada | Evento permitido si el resto coincide, con `player_id=None` |
| Identidad confirmada compatible | Evento con `player_id` y evidencia conservada en el envoltorio |

## Cambios técnicos

| Archivo | Cambio | Motivo |
|---|---|---|
| `apps/backend/src/match_intelligence/application/observation_fusion.py` | Contratos, política, resultados y servicio | Fusionar sin perder fuentes ni ocultar contradicciones |
| `apps/backend/tests/test_observation_fusion.py` | Quince pruebas automatizadas | Verificar coincidencia, límites y trazabilidad |
| `docs/persona-1-datos-y-vision/historias-de-usuario.md` | Estado y evidencia | Mantener trazabilidad del backlog |
| `docs/persona-1-datos-y-vision/evidencias/README.md` | Registro de DV-US-13 | Mostrar el estado real |
| `docs/persona-1-datos-y-vision/plan-general.md` | Decisión parcial de tolerancias | Separar política configurable de calibración real pendiente |

## Diseño

```text
ActionObservation ───────────────┐
                                │
VisualTrackObservation ─────────┼─► ObservationFusionService
                                │           │
ResolvedVisualIdentity opcional ┘           ├─► fused + MatchEvent
                                            ├─► insufficient_evidence
FusionPolicy ────────────────────────────────└─► contradiction

Todos los resultados conservan las observaciones originales.
```

`MatchEvent` no contiene identificadores de observación visual. Por eso `FusedVideoEvent` lo envuelve y añade `source_observation_ids`, `track_id`, objetos originales, identidad, diferencia temporal y distancia espacial.

## Política de fusión

### Coincidencia estructural

Las dos observaciones deben pertenecer al mismo partido. Si la acción declara `track_id`, debe coincidir con el seguimiento. Si ambas declaran equipo, los valores deben ser iguales. Una diferencia en estos campos es contradicción, no evidencia insuficiente.

### Tolerancia temporal

Se calcula:

```text
temporal_delta_ms = abs(action.video_time_ms - track.video_time_ms)
```

El valor debe ser menor o igual que `FusionPolicy.temporal_tolerance_ms`.

### Tolerancia espacial

Ambas observaciones deben incluir posición. La distancia usa las coordenadas normalizadas de 0 a 100:

```text
distance = sqrt((action.x - track.x)² + (action.y - track.y)²)
```

El valor debe ser menor o igual que `FusionPolicy.spatial_tolerance`. La política no afirma metros porque las entradas están normalizadas.

### Evidencia mínima

Además de las tolerancias, la acción necesita `track_id` y la fusión necesita un `team_id` coherente para construir `MatchEvent 1.0`. Si falta algún dato, no se emite el evento.

### Confianza e identidad

La confianza del evento es el mínimo entre acción y seguimiento. No representa certeza táctica ni identidad nominal. Una identidad `unconfirmed` conserva el track, pero produce `player_id=None`. Solo una identidad confirmada por DV-US-12 puede completar ese campo.

## Context7

DV-US-13 no añade bibliotecas o frameworks externos. La fusión utiliza contratos internos y funciones de Python 3.12. No fue necesaria una consulta nueva a Context7.

## Cobertura de criterios de aceptación

| Criterio | Implementación | Evidencia | Estado |
|---|---|---|---|
| Tolerancias temporales y espaciales documentadas | `FusionPolicy` y fórmulas anteriores | Pruebas dentro y fuera de ambos límites | Cumplido localmente |
| Observaciones originales disponibles | `FusionResult` y `FusedVideoEvent` conservan ambos objetos | Prueba de fusión y prueba de rechazo temporal | Cumplido |
| Contradicción sin certeza falsa | Estado `contradiction`, `fused=None` | Casos de partido, track, equipo e identidad incompatibles | Cumplido |
| Evidencia insuficiente no emite o marca limitación | Estado, ausencia de evento y motivos | Casos de tiempo, espacio, posición y track faltante | Cumplido |

## Pruebas automatizadas

| Prueba o grupo | Comportamiento comprobado |
|---|---|
| Observaciones compatibles | Evento trazable y valores conservadores |
| Identificador determinista | Misma entrada produce el mismo `event_id` |
| Identidad confirmada | `player_id` y evidencia preservados |
| Identidad no confirmada | No inventa jugador |
| Fuera de tolerancia temporal | No emite y conserva fuentes |
| Fuera de tolerancia espacial | No emite |
| Posición ausente | Limitación explícita |
| `track_id` ausente | Limitación explícita |
| Tres contradicciones parametrizadas | Partido, track y equipo incompatibles |
| Identidad de otra observación | Contradicción explícita |
| Tres políticas inválidas | Tolerancias negativas o NaN rechazadas |

## Reproducción

Pruebas específicas:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_observation_fusion.py -q
```

Suite completa:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 pytest -q
```

Comprobaciones adicionales:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python -m compileall -q apps/backend/src apps/backend/scripts
UV_CACHE_DIR=/tmp/mentox-uv-cache uv lock --project apps/backend --check
git diff --check
```

## Entorno verificado

| Componente | Versión |
|---|---|
| Python | 3.12.13 |
| uv | 0.11.32 |
| pytest | 9.1.1 |
| Modelos o servicios externos | No utilizados |

## Resultado

Pruebas específicas:

```text
...............                                                          [100%]
15 passed in 0.11s
```

Suite completa:

```text
........................................................................ [ 53%]
..............................................................           [100%]
134 passed in 0.67s
```

`compileall`, `uv lock --check` y `git diff --check` terminaron correctamente y sin errores.

## Limitaciones y riesgos

- Las tolerancias de prueba son ejemplos y no están calibradas para un vídeo real.
- Una distancia normalizada no equivale directamente a metros ni píxeles.
- Usar el mínimo de dos confianzas es conservador, pero no constituye una probabilidad calibrada de que el evento sea correcto.
- Dos observaciones compatibles pueden seguir siendo falsas; la calidad depende de DV-US-11.
- La búsqueda de candidatos y resolución de múltiples coincidencias todavía no está implementada.
- `related_event_ids` queda vacío porque los identificadores de observación no son eventos deportivos.
- El envoltorio trazable debe conservarse si el evento se transporta o almacena en una etapa posterior.

## Dependencias y siguientes pasos

- Ejecutar DV-US-11 con un vídeo autorizado y producir observaciones reales.
- Calibrar tolerancias contra una muestra manual.
- Definir selección cuando existan varios tracks candidatos.
- Persistir `FusedVideoEvent` o un sobre equivalente para no perder fuentes.
- Persona 2 debe aceptar únicamente el `MatchEvent` cuando `FusionStatus=FUSED`.
- Persona 3 debe tratar confianza y limitaciones como evidencia, no como certeza narrativa.
