# Evidencia técnica de DV-US-03

## Identificación

- **Historia:** DV-US-03 · Recibir únicamente eventos válidos.
- **Estado:** verificada localmente.
- **Prioridad:** P0.
- **Última verificación:** 9 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.
- **Requisitos relacionados:** DV-RF-04, DV-RF-05, DV-RF-07 y DV-RNF-02.

## Objetivo comprobado

Un consumidor puede entregar una secuencia de objetos candidatos y obtener únicamente instancias válidas de `MatchEvent 1.0`. Cada candidato inválido produce un rechazo estructurado y aislado, por lo que no contamina las estadísticas ni impide validar los elementos posteriores.

## Alcance implementado

- Caso de uso `validate_event_batch` independiente de HTTP y de Azure.
- Validación de cada candidato contra el contrato `MatchEvent 1.0` de Pydantic.
- Conservación de `event_id`, `match_id`, `period`, `clock_ms` y `video_time_ms` en eventos válidos.
- Aceptación de eventos que omiten campos realmente opcionales.
- Rechazo de campos obligatorios ausentes, valores fuera de rango, campos desconocidos y candidatos que no son objetos.
- Resultado separado en colecciones ordenadas `accepted` y `rejected`.
- Rechazo con índice original, `event_id` cuando puede recuperarse y uno o más problemas estructurados.
- Continuación del lote después de uno o varios candidatos inválidos.
- Endpoint `POST /api/v1/events/validate-batch` con esquema de respuesta publicado en OpenAPI.
- Conservación del endpoint individual `POST /api/v1/events/validate` para no romper el contrato previo.

## Fuera del alcance

- No se detectan eventos repetidos; corresponde a DV-US-04.
- No se clasifica un evento como tardío ni se reordena; corresponde a DV-US-05.
- No se comprueba todavía que `team_id` y `player_id` pertenezcan a los metadatos de un partido. Esta historia valida el contrato del evento, no la consistencia entre agregados.
- No se publican eventos en memoria ni en Event Hubs como parte del validador.
- No se persisten los rechazos en una base de datos o almacenamiento de diagnóstico.
- No se calcularon estadísticas deportivas ni se conectó el resultado con Persona 2.

## Entradas y resultados

| Elemento | Descripción |
|---|---|
| Entrada de aplicación | Iterable de candidatos; cada elemento puede ser un diccionario, una instancia compatible o un valor mal formado |
| Entrada HTTP | Arreglo JSON enviado a `POST /api/v1/events/validate-batch` |
| Evento aceptado | Instancia de `MatchEvent` que cumple tipos, campos, enumeraciones y restricciones del contrato 1.0 |
| Evento rechazado | Índice del candidato, `event_id` recuperable y lista de problemas |
| Problema estructurado | `location`, `code` y `message` |
| Resultado | Cantidades y colecciones ordenadas de aceptados y rechazados |

Ejemplo resumido de un rechazo:

```json
{
  "index": 1,
  "event_id": "evt-002",
  "issues": [
    {
      "location": ["clock_ms"],
      "code": "missing",
      "message": "Field required"
    }
  ]
}
```

El texto de `message` proviene de Pydantic y puede cambiar entre versiones menores. Los consumidores deben basarse en `location` y `code`; ambos campos constituyen la parte estable del diagnóstico de esta aplicación.

## Cambios técnicos

| Archivo | Cambio | Motivo |
|---|---|---|
| `apps/backend/src/match_intelligence/application/validation.py` | Resultado, rechazo, problema y validación por lotes | Aislar la regla de aplicación del transporte |
| `apps/backend/src/match_intelligence/adapters/http/schemas.py` | Esquemas de respuesta del informe | Publicar un contrato tipado y visible en OpenAPI |
| `apps/backend/src/match_intelligence/adapters/http/router.py` | Endpoint `validate-batch` | Permitir probar e integrar la capacidad mediante HTTP |
| `apps/backend/tests/test_event_validation.py` | Siete pruebas de contrato, continuidad y API | Demostrar requisitos y criterios de aceptación |
| `docs/persona-1-datos-y-vision/historias-de-usuario.md` | Estado y enlace de evidencia | Mantener trazabilidad del backlog |
| `docs/persona-1-datos-y-vision/evidencias/README.md` | Registro de esta evidencia | Hacer visible el avance al equipo |

## Diseño y flujo

```text
lista de candidatos
        │
        ▼
validate_event_batch
        │
        ├── MatchEvent.model_validate ── válido ──> accepted
        │
        └── ValidationError ────────────> rejected
                                               │
                                               └── location + code + message
```

Cada vuelta del ciclo tiene su propio manejo de `ValidationError`. Por ello, registrar un rechazo no abandona la función: la siguiente posición del iterable siempre se intenta validar.

## Decisiones técnicas

### Validación en la capa de aplicación

El caso de uso no depende de FastAPI. HTTP transforma el informe a una respuesta JSON, pero un futuro consumidor de memoria o Event Hubs puede llamar la misma función. Así se conserva DV-RNF-02 y no se obliga al dominio a conocer Azure.

### Uso del contrato existente

Se utiliza `MatchEvent.model_validate` en lugar de duplicar reglas. Los campos obligatorios, límites, enumeraciones y `extra="forbid"` siguen definidos en un solo lugar: `domain/contracts.py`.

La decisión se contrastó con la documentación oficial vigente de Pydantic sobre [modelos y `model_validate`](https://docs.pydantic.dev/latest/concepts/models/), [manejo de errores de validación](https://docs.pydantic.dev/latest/errors/errors/) y [`ConfigDict.extra`](https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.extra).

### Errores normalizados

El validador no expone directamente toda la estructura interna de `ValidationError`. Solo conserva:

- `location`: ruta del campo, apta para errores anidados;
- `code`: código clasificable por software;
- `message`: explicación legible.

No se devuelve el valor de entrada que causó el error. Esto reduce el tamaño de la respuesta y evita copiar datos candidatos innecesariamente en diagnósticos.

### Orden e identidad

Los aceptados conservan el orden relativo de entrada y los rechazados guardan el índice original. El validador crea el modelo normalizado, pero no genera identificadores ni modifica deliberadamente los cinco campos de identidad y tiempo exigidos por DV-RF-05.

### Modo de conversión

Se conserva el comportamiento normal de Pydantic, que puede convertir entradas compatibles a los tipos declarados. No se activó modo estricto porque la historia exige integridad del contrato, no identidad del tipo Python original. Los valores válidos de identificación y tiempo usados por el productor se comprobaron sin cambios.

## Cobertura de criterios de aceptación

| Criterio | Implementación | Evidencia | Estado |
|---|---|---|---|
| Un evento válido se entrega sin cambiar identificadores ni tiempos | `MatchEvent.model_validate` y colección `accepted` | `test_valid_event_preserves_identity_and_time` compara los cinco campos de DV-RF-05 | Cumplido |
| Un evento sin un campo obligatorio se rechaza con motivo estructurado | `RejectedEvent` y `ValidationIssue` | `test_missing_required_field_has_a_structured_rejection` comprueba índice, ID, ubicación, código y mensaje | Cumplido |
| Un evento inválido no impide procesar eventos válidos posteriores | Manejo de error dentro del ciclo de candidatos | `test_invalid_event_does_not_stop_later_valid_events` intercala inválido entre dos válidos | Cumplido |

## Cobertura adicional de requisitos

| Requisito | Evidencia | Estado |
|---|---|---|
| DV-RF-04: evento válido | `test_valid_event_preserves_identity_and_time` | Cumplido |
| DV-RF-04: evento sin opcionales | `test_event_without_optional_fields_is_accepted` | Cumplido |
| DV-RF-04: evento inválido | `test_missing_required_field_has_a_structured_rejection` y `test_invalid_values_and_unknown_fields_are_reported` | Cumplido |
| DV-RF-05: conservar identidad y tiempo | Comparación de `event_id`, `match_id`, `period`, `clock_ms` y `video_time_ms` | Cumplido localmente antes del transporte |
| DV-RF-07: rechazo explícito y continuidad | Lote válido-inválido-válido y posición del rechazo | Cumplido |
| DV-RNF-02: independencia de infraestructura | El módulo importa Pydantic y el contrato; no importa SDK de Azure, Roboflow ni SoccerNet | Cumplido |

## Pruebas automatizadas

| Prueba | Comportamiento comprobado |
|---|---|
| `test_valid_event_preserves_identity_and_time` | Un evento válido conserva los cinco valores críticos |
| `test_event_without_optional_fields_is_accepted` | Los campos opcionales reciben sus valores predeterminados sin causar rechazo |
| `test_missing_required_field_has_a_structured_rejection` | La ausencia de `clock_ms` se informa como `missing` en su ubicación exacta |
| `test_invalid_event_does_not_stop_later_valid_events` | Un rechazo intermedio no detiene el procesamiento y conserva el orden de aceptados |
| `test_invalid_values_and_unknown_fields_are_reported` | Un período fuera de rango y un campo extra generan problemas independientes |
| `test_non_object_candidate_is_rejected_without_stopping_the_batch` | Un candidato que no es objeto se rechaza y el válido posterior se acepta |
| `test_batch_endpoint_returns_machine_readable_results` | La forma JSON, los conteos, el índice y la operación OpenAPI están disponibles |

## Reproducción

Desde la raíz del repositorio:

```bash
uv python install 3.12
uv sync --project apps/backend --extra dev
uv run --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_event_validation.py -q
```

Para ejecutar toda la suite y comprobar OpenAPI:

```bash
uv run --project apps/backend --python 3.12 \
  pytest apps/backend/tests -q
uv run --project apps/backend --python 3.12 python -c \
  "from match_intelligence.main import app; assert '/api/v1/events/validate-batch' in app.openapi()['paths']; print('OpenAPI: ok')"
```

Si el entorno no permite escribir en la caché global de `uv`, se puede usar una ubicación temporal:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache uv run \
  --project apps/backend --python 3.12 \
  pytest apps/backend/tests -q
```

## Entorno verificado

| Componente | Versión |
|---|---|
| Python | 3.12.13 |
| uv | 0.11.32 |
| FastAPI | 0.143.0 |
| Pydantic | 2.12.5 |
| pytest | 9.1.1 |
| Contrato | MatchEvent 1.0 |
| Infraestructura externa | Ninguna |

## Resultado

Verificación específica de DV-US-03 ejecutada el 9 de octubre de 2026:

```text
.......                                                                  [100%]
7 passed in 0.25s
```

Verificación completa del backend y del documento OpenAPI:

```text
............................                                             [100%]
28 passed in 0.26s
OpenAPI: ok
```

## Limitaciones y riesgos

- Esta verificación es local. Todavía no demuestra preservación de valores después de serializar y consumir desde Event Hubs.
- Pydantic no está configurado en modo estricto; entradas compatibles pueden normalizarse al tipo declarado.
- El mensaje humano de Pydantic puede variar. Los consumidores deben usar `location` y `code` para automatizaciones.
- El `event_id` del rechazo solo se conserva cuando el candidato es un objeto y dicho valor ya es una cadena.
- Los rechazos viven en memoria durante la solicitud; aún no existe auditoría persistente.
- Un lote extremadamente grande se procesa completo en memoria. Antes de aceptar cargas productivas se deberá definir un límite HTTP o procesamiento por streaming.
- Validar el esquema no prueba consistencia con metadatos del partido ni autenticidad de una detección de vídeo.

## Dependencias y siguientes pasos

- DV-US-04 debe consumir los aceptados y deduplicarlos por `match_id` y `event_id`.
- DV-US-05 definirá qué hacer si el reloj de un evento válido retrocede.
- DV-US-07 reutilizará este caso de uso al consumir cargas desde Event Hubs.
- DV-US-08 conectará el mismo validador sin cambiar el dominio tanto al transporte local como al de Azure.
- Persona 2 podrá trabajar únicamente con `report.accepted`; la forma exacta de integración debe acordarse sin interpretar `rejected` como evento deportivo.
