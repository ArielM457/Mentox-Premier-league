# Evidencia técnica de DV-US-12

## Identificación

- **Historia:** DV-US-12 · No inventar identidad de jugadores.
- **Estado:** regla y pruebas negativas verificadas localmente; asociación real pendiente.
- **Prioridad:** P2.
- **Última verificación:** 9 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.
- **Requisito relacionado:** DV-RF-20.

## Objetivo comprobado

Una observación visual conserva su `track_id`, tiempo, posición, equipo estimado y confianza del detector sin convertirlos automáticamente en la identidad nominal de un jugador. `player_id` permanece ausente hasta recibir una asociación explícita, trazable, correspondiente al mismo partido y seguimiento, y perteneciente a la plantilla conocida.

La regla se comprobó con confianza de detector desde 0 hasta 1. Incluso `detector_confidence=1` mantiene la identidad como `unconfirmed` cuando no existe evidencia independiente.

## Alcance implementado

- Contrato `VisualTrackObservation` separado del evento deportivo.
- Identificadores de observación, partido y seguimiento obligatorios.
- Conservación de `video_time_ms`, confianza, equipo estimado y posición opcional.
- Resultado `ResolvedVisualIdentity` con estado `unconfirmed` o `confirmed`.
- `player_id=None` por defecto.
- Evidencia explícita `manual_confirmation` o `verified_roster_mapping`.
- Referencia de evidencia y responsable de verificación obligatorios.
- Comprobación de coincidencia de partido y `track_id`.
- Comprobación contra la plantilla conocida.
- Separación entre `detector_confidence` y evidencia de identidad.
- Pruebas negativas para ausencia de evidencia, confianza máxima y asociaciones incompatibles.

## Fuera del alcance

- No se ejecutó un detector ni un seguidor real.
- No se incorporó reconocimiento facial, dorsal, OCR o reidentificación.
- No se diseñó la interfaz de revisión manual.
- No se definió un proveedor operativo de mapeos externos.
- No se fusionó la observación en `MatchEvent`; corresponde a DV-US-13.
- No se modificó `MatchEvent 1.0`, porque es un contrato compartido y actualmente no contiene `track_id`.
- No se afirma que `team_id`, posición o confianza confirmen el nombre del jugador.

## Entradas y resultados

| Entrada | Resultado |
|---|---|
| Observación sin asociación | Mismo `track_id`, `player_id=None`, estado `unconfirmed` |
| Confianza alta sin asociación | Continúa sin identidad nominal |
| Confirmación manual trazable | `player_id` conocido, estado `confirmed` y referencia conservada |
| Mapeo externo verificado | Puede confirmar si cumple las mismas reglas |
| Asociación de otro partido o track | Error explícito |
| Jugador fuera de la plantilla | Error explícito |

## Cambios técnicos

| Archivo | Cambio | Motivo |
|---|---|---|
| `apps/backend/src/match_intelligence/application/visual_identity.py` | Observación, evidencia, resultado y resolvedor | Separar seguimiento de identidad nominal |
| `apps/backend/tests/test_visual_identity.py` | Trece pruebas | Demostrar casos positivos, negativos y límites |
| `docs/persona-1-datos-y-vision/historias-de-usuario.md` | Estado y evidencia | Mantener trazabilidad del backlog |
| `docs/persona-1-datos-y-vision/evidencias/README.md` | Registro de la historia | Mostrar el estado real |
| `docs/persona-1-datos-y-vision/plan-general.md` | Decisión parcial de asociación | Separar la regla ya fijada del mecanismo operativo pendiente |

## Diseño

```text
detector / tracker
       │
       ▼
VisualTrackObservation
  track_id + detector_confidence
       │
       ├─ sin evidencia ───────────────────────┐
       │                                       ▼
       └─ ConfirmedPlayerIdentity ─► PlayerIdentityResolver
              │ partido y track iguales        │
              │ jugador de plantilla           ▼
              │ referencia trazable      ResolvedVisualIdentity
              └────────────────────────── player_id opcional
```

El resolvedor no contiene umbral de confianza. Esto es intencional: cambiar el valor del detector no puede cambiar el estado de identidad.

## Decisiones técnicas

### Contrato separado

`MatchEvent 1.0` representa acciones deportivas normalizadas y no tiene `track_id`. Agregar el campo durante esta historia cambiaría un contrato compartido antes de definir la fusión. La observación visual se mantiene separada y DV-US-13 decidirá si existe evidencia suficiente para originar un evento.

### Confianza no es identidad

`detector_confidence` mide la estimación del detector sobre su observación. No mide si el track corresponde a una persona nominal concreta. Por eso el resolvedor no consulta ese valor al asignar `player_id`.

### Evidencia independiente

Solo se admiten dos clases iniciales de confirmación:

- revisión manual con referencia conservada;
- mapeo externo previamente verificado.

Ambas requieren `verified_by` y `evidence_reference`. El contrato no implementa ni da por válido un mecanismo concreto de OCR o reconocimiento.

### Plantilla conocida

Una confirmación solo puede apuntar a un `player_id` del conjunto entregado al resolvedor. Esto evita introducir un nombre arbitrario aunque la referencia tenga la forma correcta.

## Context7

DV-US-12 no añade ni cambia bibliotecas externas. Usa `dataclass`, `StrEnum` y validación de Python 3.12, junto con `Position` del contrato existente. Por ello no fue necesaria una consulta nueva a Context7.

## Cobertura de criterios de aceptación

| Criterio | Implementación | Evidencia | Estado |
|---|---|---|---|
| Detección no asociada conserva `track_id` y omite `player_id` | Resultado predeterminado `unconfirmed` | `test_unconfirmed_detection_preserves_track_and_omits_player` | Cumplido |
| Confianza no prueba identidad nominal | No existe umbral ni rama basada en confianza | Prueba parametrizada con 0, 0.5, 0.999 y 1 | Cumplido |
| Al menos una prueba negativa | Ausencia, incompatibilidad y jugador desconocido | Ocho casos negativos o parametrizados | Cumplido |

## Pruebas automatizadas

| Prueba o grupo | Comportamiento comprobado |
|---|---|
| Observación sin asociación | Conserva track y omite jugador |
| Cuatro niveles de confianza | Nunca generan identidad por sí solos |
| Confirmación explícita | Asocia jugador conocido y conserva evidencia |
| Otro `track_id` | Rechazado |
| Otro partido | Rechazado |
| Jugador fuera de plantilla | Rechazado |
| Referencia vacía | Rechazada |
| Tres confianzas inválidas | Fuera de rango o NaN rechazadas |

## Reproducción

Pruebas específicas:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_visual_identity.py -q
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
.............                                                            [100%]
13 passed in 0.07s
```

Suite completa:

```text
........................................................................ [ 60%]
...............................................                          [100%]
119 passed in 0.64s
```

`compileall`, `uv lock --check` y `git diff --check` terminaron correctamente y sin errores.

## Limitaciones y riesgos

- Los tipos de evidencia indican procedencia, pero no verifican automáticamente que una referencia sea auténtica.
- La plantilla conocida debe corresponder al mismo partido y mantenerse por una fuente confiable.
- Un track puede cambiar por oclusión o reasignación del seguidor; una confirmación no debe propagarse sin revisar ese comportamiento.
- La estimación de equipo tampoco confirma identidad individual.
- Falta definir expiración, corrección y revocación de asociaciones.
- La prueba local no demuestra identidad sobre vídeo real.

## Dependencias y siguientes pasos

- Elegir el vídeo y los modelos según DV-US-11.
- Definir cómo se produce, revisa y revoca una confirmación.
- Persona 4 debe diseñar una interfaz que muestre claramente `unconfirmed`.
- DV-US-13 debe conservar la observación y la evidencia al fusionar eventos.
- Persona 2 y Persona 3 no deben usar `track_id` como nombre de jugador.
