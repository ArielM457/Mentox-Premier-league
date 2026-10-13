# Estado y analítica del partido

Esta carpeta documenta el trabajo de Persona 2. El objetivo es convertir eventos `MatchEvent 1.0` en estado, estadísticas y momentos candidatos explicables, con cálculos reproducibles. Persona 2 no redacta mensajes ni decide la publicación: entrega cifras, hechos y motivos para que Persona 3 los explique y Persona 4 los muestre.

- **Rama:** `persona-2/estado-analitica`.
- **Estado:** implementado y verificado localmente con datos sintéticos y dobles de Azure. El despliegue y la prueba de humo en Azure están pendientes porque necesitan una suscripción.
- **Última verificación:** 11 de octubre de 2026.
- **Tablero de demostración:** [`demo/tablero.html`](demo/tablero.html), con su [guion para presentar](demo/README.md#guion-sugerido-para-presentar-avances-5-minutos).

## Documentos

- [Historias de usuario](historias-de-usuario.md): necesidades, criterios de aceptación y estado de cada historia.
- [Catálogo de métricas](catalogo-de-metricas.md): fórmula, datos necesarios, unidad, ejemplos y casos sin datos.
- [Reglas de jugadas, patrones y atención](reglas-de-patrones-y-atencion.md): detectores con ejemplos positivos y negativos, y cómo se calcula la prioridad.
- [Informe de viabilidad de xT, VAEP y xG](informe-modelos-de-valor.md): qué se puede validar hoy y qué queda desactivado.
- [Integración con Azure](integracion-azure.md): flujo en Event Hubs y Blob Storage, despliegue y prueba de humo.
- [Analítica de seguimiento](analitica-de-seguimiento.md): velocidad, distancia, presión por cercanía y forma del equipo a partir de las observaciones de visión de Persona 1, hoy simuladas.
- [Tablero de demostración](demo/README.md): reproducción del partido con todo lo que calcula el motor y un guion para presentar avances.
- [Evidencias](evidencias/README.md): criterios cubiertos, archivos, comandos, versiones y limitaciones.
- [Ejemplos de contrato](ejemplos/): `MatchSnapshot v1`, `InsightCandidate v1` y salidas completas de dos partidos.

## Qué existe ahora

```text
MatchEvent 1.0
   │
   ├─ MatchStateEngine ── tardíos, correcciones y retiros (rebuild_from_ordered_history@1)
   │        │
   │        ▼
   │   MatchAnalyzer (causal, evento a evento)
   │        ├─ MatchState: marcador, período, reloj, posesión por tramos
   │        ├─ SequenceBuilder: jugadas (sequence@1)
   │        └─ detectores: tiro y gol, progresión rápida, recuperación y tiro,
   │           presión sostenida, pase progresivo, recuperación alta, hitos,
   │           cambio de control y fase de caos
   │        │
   │        ▼
   │   merge_signals → AttentionEngine (attention@1) → InsightCandidate v1 + decisiones
   │
   └─ build_snapshot → MatchSnapshot v1 (estadísticas, posesión, indicadores, modelos)
```

| Pieza | Archivo |
|---|---|
| Contratos `MatchSnapshot v1`, `InsightCandidate v1`, `AttentionDecision` | `apps/backend/src/match_intelligence/domain/analytics/models.py` |
| Estado y posesión | `domain/analytics/state.py` |
| Estadísticas y ventanas | `domain/analytics/statistics.py` |
| Catálogo de métricas | `domain/analytics/catalog.py` |
| Jugadas | `domain/analytics/sequences.py` |
| Patrones | `domain/analytics/patterns.py` |
| Hitos de jugador | `domain/analytics/milestones.py` |
| Indicadores propios | `domain/analytics/indicators.py` |
| Motor de atención | `domain/analytics/attention.py` |
| Análisis y `AnalyticsPort` | `application/analytics/pipeline.py` |
| Reconstrucción | `application/analytics/engine.py` |
| Flujo continuo | `application/analytics/stream.py` |
| Puerto de modelos de valor | `application/analytics/value_models.py` |
| Adaptadores xT, xG y VAEP | `adapters/models/` |
| Azure Event Hubs `match-insights` | `adapters/messaging/azure_insights.py` |
| Azure Blob Storage `analytics` y `matches` | `adapters/storage/azure_analytics.py` |
| Puente con la ingesta de Persona 1 | `adapters/messaging/analytics_bridge.py` |
| Analítica de seguimiento | `domain/analytics/tracking.py` |
| Entrada desde las observaciones de visión de Persona 1 | `application/analytics/tracking_input.py` |
| Infraestructura | `infra/azure/analytics.bicep` |

Las rutas de código son relativas a `apps/backend/src/match_intelligence/`, salvo la de la infraestructura. El dominio no importa FastAPI, Azure, CrewAI ni bibliotecas de modelos.

Los datos de prueba no forman parte del código de producción y están en `apps/backend/tests/`:

| Pieza | Archivo |
|---|---|
| Escenario sintético de 178 eventos para probar la analítica | `tests/analytics_scenarios.py` |
| Observaciones de seguimiento simuladas con el formato de Persona 1 | `tests/tracking_mock.py` |
| Generador de los ejemplos de contrato | `tests/analytics_examples.py` y `scripts/export_analytics_examples.py` |
| Datos del tablero | `tests/analytics_demo.py` y `scripts/export_analytics_demo.py` |
| Constructores de eventos para pruebas | `tests/analytics_builders.py` |

## Cómo probarlo

Desde la raíz del repositorio, con el entorno del README principal:

```bash
uv run --project apps/backend pytest apps/backend/tests -q
```

Sin `uv`, con un entorno virtual de Python 3.12 o 3.13:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e "apps/backend[dev]"
.venv/Scripts/python -m pytest apps/backend/tests -q
```

Para regenerar los ejemplos después de cambiar una regla:

```bash
python apps/backend/scripts/export_analytics_examples.py
```

Una prueba falla si los ejemplos guardados no coinciden con el código.

## Cómo integrarlo con Persona 4

La rama `persona-4/api-frontend` define `AnalyticsPort` con `snapshot(metadata, events, *, video_time_ms)` y `candidates(metadata, events, preferences)`. `MatchAnalytics` implementa esas dos funciones. Se probó la integración en una copia de esa rama con estos dos cambios:

1. En `domain/presentation.py`, borrar las clases `MetricValue`, `MatchSnapshot` e `InsightCandidate` e importarlas de `match_intelligence.domain.analytics.models`. Los campos que usa Persona 4 conservan nombre y tipo; los campos nuevos son opcionales.
2. En `adapters/http/registry.py`, usar `MatchAnalytics` en lugar de `ProvisionalAnalytics`.

Resultado: 240 de 242 pruebas pasaron. Las dos que fallan dependen de la analítica provisional y deben ajustarse:

- `test_favorite_player_raises_priority_only_when_involved` busca `moment-evt-006`, un momento que solo existía en la analítica provisional. El momento real donde participa `aurora-8` es `moment-evt-009`.
- `test_language_changes_text_not_facts` falla porque la narración provisional no tiene plantillas para los tipos nuevos y repite el nombre del tipo en ambos idiomas. Los tipos que debe cubrir la narración están en [reglas de patrones y atención](reglas-de-patrones-y-atencion.md#tipos-de-momento).

`MatchAnalytics` reutiliza el análisis cuando la lista de eventos crece o retrocede, así que las llamadas repetidas de la API al reproducir o adelantar el vídeo no recalculan todo el partido.

## Cómo lo usa Persona 3

Persona 3 recibe `InsightCandidate v1` con:

- `facts`: cifras con unidad, versión de fórmula, origen (`event_count`, `derived`, `team_indicator` o `value_model`) y eventos de origen.
- `evidence_limits`: lo que los datos no permiten afirmar. Por ejemplo, que una recuperación causó un tiro.
- `reasons`: los puntos que sumó o restó cada motivo de selección.
- `signals`: todas las reglas que se cumplieron en el mismo evento.

Un hecho con origen `team_indicator` es una escala del equipo, no una estadística oficial, y debe presentarse así. Las preferencias cambian prioridad y selección, nunca hechos ni fuentes.

## Decisiones propuestas por Persona 2

Estas decisiones están implementadas pero todavía deben confirmarse con el equipo:

1. **Reconstrucción de tardíos.** El motor inserta el evento en su lugar y vuelve a plegar el estado. Complementa la política `forward_and_flag` de Persona 1 (DV-US-05).
2. **Correcciones explícitas.** Un evento con el mismo `event_id` y contenido distinto se rechaza como conflicto. Corregir exige llamar a `correct`. Hace falta un contrato de corrección en la ingesta, porque el deduplicador de Persona 1 descarta cualquier `event_id` repetido.
3. **Salida en Azure.** Un Event Hub nuevo, `match-insights`, con grupos `narrative`, `experience` y `diagnostics`, y los contenedores `analytics` y `models`.
4. **Perfil neutro en el flujo publicado.** El flujo de Azure publica momentos sin preferencias. Cada espectador recibe su versión personalizada desde la API.
5. **Umbrales y pesos iniciales.** Están en el catálogo y en las reglas. Cubren la decisión pendiente 5 de [decisiones pendientes](../05-decisiones-pendientes.md) como propuesta.

## Pendiente

- Desplegar `analytics.bicep` y ejecutar `analytics_azure_smoke.py` en una suscripción real.
- Alojar el procesador continuo en Azure (propuesta: Azure Container Apps con identidad administrada, junto con la API de Persona 4).
- Entrenar xT y xG con datos con licencia antes de activarlos.
- Revisar umbrales con un partido sintético más largo de Persona 1.
- Recibir observaciones reales de vídeo de Persona 1 (DV-US-19) y acordar cómo marcar el balón y los porteros en `VisualTrackObservation` ([analítica de seguimiento](analitica-de-seguimiento.md#entrada-observaciones-de-visión-de-persona-1)).
