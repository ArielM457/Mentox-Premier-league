# Evidencia técnica de DV-US-10

## Identificación

- **Historia:** DV-US-10 · Sincronizar eventos con vídeo.
- **Estado:** coordinación temporal verificada localmente; vídeo e interfaz pendientes.
- **Prioridad:** P0.
- **Última verificación:** 9 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.
- **Requisitos relacionados:** DV-RF-05 y DV-RF-10; detalla RF-37.

## Objetivo comprobado

El backend puede recibir posiciones absolutas de un reproductor de vídeo y entregar únicamente los eventos sintéticos cuyo `video_time_ms` fue cruzado durante el avance normal. Una pausa impide el avance y la emisión. Un salto reconstruye el estado con todos los eventos hasta el destino, mediante un puerto separado, sin convertir el historial en mensajes visibles del tramo actual.

Cada entrega conserva el objeto `MatchEvent` original, incluido `clock_ms`, `video_time_ms`, identificadores y procedencia. La base temporal se etiqueta como `provided_event_timestamp`: es una alineación suministrada por los datos, no una detección automática desde imágenes.

## Alcance implementado

- Estado explícito `paused` o `playing`.
- Posición absoluta del vídeo en milisegundos.
- Publicación de eventos al cruzar su `video_time_ms` durante el avance.
- Conservación completa de `MatchEvent 1.0` en cada entrega sincronizada.
- Pausa sin emisión ni movimiento a una posición futura.
- Salto hacia adelante o atrás mediante reconstrucción del prefijo histórico.
- Canal separado para reconstrucción y mensajes visibles.
- Reanudación que publica solo eventos posteriores al destino del salto.
- Reinicio que pausa y reconstruye la posición cero.
- Rechazo de posiciones negativas, no enteras o booleanas.
- Rechazo de eventos sin tiempo de vídeo, fuera de orden o pertenecientes a partidos distintos.
- Distinción explícita entre alineación temporal y detección automática.

## Fuera del alcance

- No se incorporó un archivo de vídeo al repositorio.
- No se modificó el frontend ni se conectó un elemento HTML `video`.
- No se extrajeron eventos desde imágenes o audio.
- No se midió latencia con reproducción visual real.
- No se implementó el estado deportivo de Persona 2; se definió un puerto para reconstruirlo.
- No se generan ni suprimen narraciones; el coordinador separa el canal visible del historial para que Persona 3 y Persona 4 no muestren mensajes antiguos.
- No se define tolerancia de cuadros ni corrección de deriva.

## Entradas y resultados

| Entrada | Resultado |
|---|---|
| Eventos ordenados con `video_time_ms` | Secuencia sincronizable e inmutable |
| `play()` seguido de `advance_to(t)` | Eventos no entregados con tiempo menor o igual a `t` |
| `pause()` seguido de un avance futuro | Ningún evento y posición sin cambios |
| `seek(t)` | Reconstrucción con el prefijo hasta `t`, sin mensajes visibles |
| `restart()` | Estado pausado, posición cero y reconstrucción vacía |
| Evento sin `video_time_ms` | `VideoSyncError` explícito |
| Avance hacia atrás | Error que exige usar `seek` |

## Cambios técnicos

| Archivo | Cambio | Motivo |
|---|---|---|
| `apps/backend/src/match_intelligence/application/video_sync.py` | Contratos y coordinador temporal | Aislar sincronización de interfaz, Azure y detección |
| `apps/backend/tests/test_video_sync.py` | Catorce pruebas automatizadas | Cubrir tiempos, pausa, saltos, reinicio y límites |
| `docs/persona-1-datos-y-vision/historias-de-usuario.md` | Estado y evidencia | Mantener trazabilidad del backlog |
| `docs/persona-1-datos-y-vision/evidencias/README.md` | Registro de DV-US-10 | Exponer su estado real |
| `docs/persona-1-datos-y-vision/plan-general.md` | Decisión parcial de sincronización | Separar la regla implementada del vídeo aún pendiente |

## Diseño

```text
posición del vídeo
       │
       ▼
VideoSynchronizedReplay
       │
       ├─ avance normal ─► SynchronizedEventPublisher ─► mensajes del tramo
       │
       └─ seek/restart ──► MatchStateRebuilder ─────────► estado reconstruido
                              sin publicar historial
```

`VideoSynchronizedReplay` pertenece a aplicación y solo depende de `MatchEvent`. La interfaz podrá llamar `play`, `pause`, `advance_to`, `seek` y `restart` sin conocer el origen de los eventos.

## Política temporal

### Avance normal

Cuando el vídeo está reproduciéndose y avanza desde su posición actual hasta `t`, se entregan en orden todos los eventos aún no procesados con `video_time_ms <= t`. Un tiempo igual al destino se considera alcanzado.

### Pausa

Mientras el coordinador está pausado, `advance_to` no publica eventos y tampoco cambia la posición registrada. Así una actualización futura recibida por error no adelanta el estado.

### Salto

`seek(t)` selecciona todos los eventos desde el comienzo cuyo tiempo de vídeo sea menor o igual a `t`. Ese prefijo se entrega una sola vez a `MatchStateRebuilder`. No se usa el publicador visible, por lo que no aparecen mensajes pertenecientes al tramo omitido.

Después del salto, el cursor queda detrás del primer evento posterior a `t`. Al continuar la reproducción solo se publican eventos nuevos.

### Retroceso y reinicio

Un retroceso debe ser explícito mediante `seek`; `advance_to` lo rechaza para evitar mezclar el estado futuro con el pasado. `restart` pausa y ejecuta un salto a cero.

## Alineación, no detección

`SynchronizedEvent.timing_basis` siempre vale `provided_event_timestamp`. El valor indica que `video_time_ms` llegó dentro del contrato de entrada. No afirma que el backend haya observado, detectado o validado visualmente la acción.

Los eventos de aceptación conservan `source=synthetic`. Una futura inferencia de vídeo deberá pasar por su adaptador, declarar `source=video_inference` y demostrar calidad por separado antes de presentarse como implementada.

## Context7

DV-US-10 no incorpora bibliotecas ni frameworks externos. El coordinador usa `dataclass`, `StrEnum`, `Protocol` y colecciones de Python 3.12. Por ello no fue necesaria una consulta nueva a Context7.

## Cobertura de criterios de aceptación

| Criterio | Implementación | Evidencia | Estado |
|---|---|---|---|
| Conservar reloj de partido y tiempo de vídeo | `SynchronizedEvent` contiene el `MatchEvent` original y expone ambos tiempos | `test_synchronized_event_preserves_match_and_video_times` | Cumplido localmente |
| Pausa sin eventos futuros | `advance_to` retorna vacío y no mueve la posición cuando está pausado | `test_pause_does_not_emit_or_move_to_a_future_position` | Cumplido localmente |
| Adelantar reconstruye sin mensajes incorrectos | `seek` usa `MatchStateRebuilder`, ajusta el cursor y no llama al publicador | Dos pruebas de salto y una de reanudación | Cumplido localmente |
| Tiempo de vídeo no presentado como detección | Base `provided_event_timestamp` y procedencia sintética intacta | `test_video_timestamp_is_explicitly_alignment_not_detection` | Cumplido |

## Pruebas automatizadas

| Prueba | Comportamiento comprobado |
|---|---|
| `test_synchronized_event_preserves_match_and_video_times` | Identidad y dos relojes intactos |
| `test_pause_does_not_emit_or_move_to_a_future_position` | Bloqueo durante pausa |
| `test_seek_forward_rebuilds_state_without_publishing_old_messages` | Reconstrucción al adelantar sin salida visible |
| `test_play_after_seek_only_publishes_events_after_the_destination` | Continuación desde el tramo correcto |
| `test_seek_backward_rebuilds_the_shorter_prefix_without_visible_messages` | Retroceso determinista |
| `test_restart_pauses_and_reconstructs_the_beginning` | Reinicio a cero |
| `test_video_timestamp_is_explicitly_alignment_not_detection` | Límite de la evidencia |
| `test_event_without_video_time_is_rejected` | Tiempo obligatorio para esta vía |
| `test_events_must_be_ordered_by_video_time` | Orden temporal estable |
| `test_events_must_belong_to_the_same_match` | Una reconstrucción no mezcla partidos |
| `test_backward_advance_requires_an_explicit_seek` | Retroceso no ambiguo |
| Tres posiciones inválidas parametrizadas | Validación de posición absoluta |

## Reproducción

Pruebas específicas:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_video_sync.py -q
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
| Servicios externos | No utilizados |

## Resultado

Pruebas específicas:

```text
..............                                                           [100%]
14 passed in 0.08s
```

Suite completa:

```text
........................................................................ [ 75%]
.......................                                                  [100%]
95 passed in 0.64s
```

`compileall`, `uv lock --check` y `git diff --check` terminaron correctamente y sin errores.

## Limitaciones y riesgos

- La integración visual debe traducir correctamente eventos `play`, `pause`, `seeking`, `seeked` y actualizaciones de tiempo del reproductor.
- El puerto de reconstrucción requiere una implementación de Persona 2 que pueda rehacer el estado desde un prefijo completo.
- Un prefijo completo es adecuado para la muestra corta; partidos largos podrían necesitar checkpoints.
- El coordinador supone que una instancia recibe llamadas de control secuenciales. Una API concurrente deberá serializarlas.
- No existe todavía una tolerancia para redondeo entre cuadros y milisegundos.
- Un `video_time_ms` presente no garantiza que la alineación sea correcta; solo conserva el valor de entrada.
- La prueba local no demuestra sincronía perceptual con un vídeo ni mide retraso de pantalla.

## Dependencias y siguientes pasos

- Persona 2 debe implementar `MatchStateRebuilder` o un adaptador equivalente.
- Persona 4 debe conectar los controles del reproductor y mantener separados reconstrucción y mensajes visibles.
- El equipo debe elegir un vídeo sintético, propio o autorizado y documentar su permiso.
- La integración debe medir deriva y retraso con el hardware de la demo.
- Si el partido crece, evaluar checkpoints sin cambiar la semántica del salto.
