# Contratos del programa

Los modelos Python y el OpenAPI generado por la API son la fuente de verdad. Esta guía explica su propósito sin duplicar todos sus campos. Los contratos de dominio usan Pydantic y rechazan campos adicionales cuando así se declara.

## Datos de partido

`MatchMetadata` y `MatchEvent` están en `apps/backend/src/match_intelligence/domain/contracts.py`, con `schema_version="1.0"`.

| Contrato | Contenido y reglas principales |
|---|---|
| `MatchMetadata` | Identificador, equipos, jugadores, dimensiones del campo y direcciones de ataque por periodo |
| `MatchEvent` | Identificadores de evento/partido, periodo, reloj deportivo, tiempo de vídeo opcional, tipo, equipo, jugador/receptor opcionales, posiciones, resultado y procedencia |
| Posición | Coordenadas normalizadas `x`, `y` entre 0 y 100; dimensiones reales en metadatos |
| Procedencia | `synthetic` o `video_model`; una procedencia declarada no sustituye la validación del material |

El contrato de dominio admite pase, tiro, entrada, cambio de posesión, presión, recuperación, falta, tarjetas, lesión y reanudación. El `RoutingEvent` de `application/routing/contracts.py` conserva un subconjunto de seis tipos: **no se debe asumir equivalencia total entre ambos esquemas**. La ampliación del filtro necesita adaptar y probar sus límites.

`clock_ms` expresa tiempo deportivo; `video_time_ms` expresa posición del medio. No se intercambian sin una regla de sincronización.

## Analítica y presentación

| Contrato | Fuente | Uso |
|---|---|---|
| `MatchSnapshot` | `domain/analytics/models.py` | Estado, marcador, reloj, posesión, métricas y eventos recientes |
| `InsightCandidate` | Mismo módulo | Momento candidato con hechos, prioridad, jugadores, fuentes y límites |
| `AttentionDecision` | Mismo módulo | Decisión emitida o descartada y sus motivos |
| `OverlayMessage` | `domain/presentation.py` | Texto temporizado para pantalla, idioma, prioridad, duración y fuentes |
| Borrador/revisión | `domain/presentation.py` | Resultado narrativo, verificación y estado editorial |

Existen modelos de presentación, analítica y narrativa con nombres similares. Los adaptadores realizan su conversión; no se deben mezclar sus clases ni sus versiones por coincidencia del nombre.

Los ejemplos válidos, mínimos e inválidos están en `apps/backend/tests/fixtures/contracts/analytics/` y `apps/backend/tests/fixtures/contracts/presentation/`. Las pruebas los validan contra los modelos; no son muestras de partidos reales.

## Filtro y agentes

`application/routing/contracts.py` define:

```text
RoutingEvaluationRequest
  → RoutingDecision + MetricUpdate + PlayContext
  → AgentRequest, cuando la decisión necesita una tarea
  → AgentDispatch, con correlación, prioridad, TTL e idempotencia
```

Las rutas son `metrics_only`, `moment_candidate`, `danger_immediate`, `dead_ball_context`, `recap` y `rejected`. Las tareas de despacho son `danger_simulation`, `moment_selector`, `narrator` y `recap`. La existencia de una tarea en el contrato no demuestra que su ejecutor remoto esté conectado.

`application/narrative/contracts.py` define solicitudes, hechos, afirmaciones, preferencias, planes, borradores y decisiones. Una afirmación debe conservar la evidencia permitida; el servicio rechaza selecciones o cifras sin soporte.

## Visión, seguimiento y comunicación

`domain/vision.py` y las aplicaciones de observación separan detecciones espaciales, acciones temporales y candidatos de fusión. Se conservan tiempo, procedencia, confianza y metadatos de seguimiento cuando están disponibles. El `track_id` no confirma identidad nominal.

El frontend recibe seguimiento en ventanas para interpolar el movimiento. La procedencia `synthetic_mock` debe seguir siendo visible como simulación y no como observación de un partido real.

Las rutas HTTP se publican en `/openapi.json` y `/docs`. El cliente React usa rutas relativas `/api/v1/...`; los detalles de SSE, WebSocket y proxy están en [arquitectura](../funcionamiento/arquitectura.md).
