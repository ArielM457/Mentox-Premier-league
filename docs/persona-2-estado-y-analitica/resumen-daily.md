# Resumen para el daily · Persona 2 (estado y analítica)

Actualizado el 11 de octubre de 2026. Rama `persona-2/estado-analitica`.

## En un minuto

- **Hecho:** el motor de estado y analítica está terminado y probado en local. Recibe eventos `MatchEvent 1.0` y entrega estado del partido (`MatchSnapshot v1`), momentos candidatos con prioridad y motivos (`InsightCandidate v1`) y cifras de velocidad y distancia desde posiciones. Hay 223 pruebas pasando: 134 de antes y 89 nuevas.
- **Demo:** [`demo/tablero.html`](demo/tablero.html) reproduce un partido sintético con todo lo que calcula el motor.
- **Siguiente:** desplegar en Azure, recibir las observaciones reales de vídeo de Persona 1 y cerrar la integración con Persona 3 y Persona 4.
- **Bloqueos:** falta una suscripción de Azure con permisos para desplegar y un vídeo permitido (Persona 1).

## Qué hace el motor con cada evento

```text
MatchEvent 1.0
  → estado: marcador, reloj, período y posesión por tramos
  → estadísticas: tiros, pases, precisión, recuperaciones, presión, pases progresivos…
  → jugadas: agrupa recuperación, pases y tiro en una sola secuencia
  → reglas: progresión rápida, recuperación y tiro, presión sostenida, hitos de jugador,
            cambio de control y fase de caos
  → atención: decide qué momento merece salir en pantalla y por qué
  → salida: MatchSnapshot v1 + InsightCandidate v1 (+ registro de decisiones)
```

Cuatro ideas para explicarlo:

1. **Toda cifra se puede comprobar.** Cada número lleva fórmula, unidad, versión y los eventos de donde sale. Si faltan datos, aparece como «no disponible», nunca como cero.
2. **La IA no calcula cifras.** El motor calcula; los agentes de Persona 3 explican. Así un agente no puede inventar un dato.
3. **La prioridad se explica.** Es una suma visible de motivos: tipo de momento, fuerza del hecho, novedad, repetición y preferencias. Los momentos descartados también quedan registrados con su motivo.
4. **Personalización sin cambiar los hechos.** Casual, analista, club favorito y modo jugador cambian qué momentos salen y con qué prioridad, pero no las cifras. Los goles del rival salen siempre.

Con el partido de prueba de 178 eventos: el perfil casual recibe 14 momentos, el analista 33 y el modo jugador de L. Sol 9.

## Qué está acoplado hoy

| Con quién | Qué se conectó | Estado |
|---|---|---|
| Persona 1 (datos) | Uso su contrato `MatchEvent 1.0`, su validación, su deduplicación y su detector de eventos tardíos. Cuando llega un evento tardío, mi motor reconstruye el estado; eso cierra lo que quedó pendiente en DV-US-05. | Probado en local |
| Persona 1 (vídeo) | Mi motor cumple su interfaz `MatchStateRebuilder`: al adelantar o retroceder el vídeo, el estado se reconstruye. | Probado en local |
| Persona 1 (Azure) | Un puente lee los eventos que su consumidor de Event Hubs ya validó, sin modificar su código. | Probado con dobles de Azure |
| Persona 4 (API) | `MatchAnalytics` implementa su `AnalyticsPort` (`snapshot` y `candidates`). Lo probé en una copia de su rama: 240 de 242 pruebas pasan. | Faltan 2 ajustes en su rama |
| Persona 3 (agentes) | Tiene los contratos y ejemplos para trabajar ya. | Sin conexión de código todavía |

Los 2 ajustes de Persona 4 son pequeños. Uno es cambiar `moment-evt-006` por `moment-evt-009` en una prueba. El otro es añadir textos para los tipos de momento nuevos en su narración provisional.

## Qué usa datos simulados (mocks)

| Parte | Qué se simula | Por qué | Qué lo reemplaza |
|---|---|---|---|
| Posiciones de jugadores y balón | Observaciones generadas desde los eventos con una cinemática simple, 5 por segundo, con el formato de visión de Persona 1 (`VisualTrackObservation`) | No hay vídeo permitido procesado | Las observaciones reales de vídeo de Persona 1, sin cambiar la analítica |
| Distancias, velocidades y avisos por umbral | El cálculo es real, pero sobre posiciones simuladas | Depende de lo anterior | Lo mismo: con posiciones reales, el cálculo no cambia |
| Frases de los momentos en el tablero | Plantillas de ejemplo | La narración es de Persona 3 | Los agentes de Persona 3 |
| Azure en las pruebas | Clientes simulados de Event Hubs y Blob Storage | No hay suscripción desplegada | El despliegue y la prueba de humo ya están escritos |
| Partido | Escenario sintético de 178 eventos con fases diseñadas | El reto exige datos sintéticos | Partidos más largos de Persona 1 |

**No es simulado:** el estado, las estadísticas, los patrones, los indicadores, los momentos, las prioridades y los motivos. Todo eso sale del motor real.

**xT, xG y VAEP** no están simulados: están **desactivados**. Los adaptadores están probados contra referencias, pero falta entrenarlos con datos que tengan licencia. Mientras tanto aparecen como «no disponible» con su motivo, y nunca se muestra un valor inventado.

## Qué recibe Persona 3 (agentes)

Persona 3 recibe dos objetos.

**`InsightCandidate v1` (momento candidato):** un momento que vale la pena narrar, con todo lo necesario para explicarlo sin inventar nada. Este es el ejemplo real del gol, recortado:

```json
{
  "candidate_id": "moment-evt-010",
  "kind": "goal",
  "priority": 100,
  "team_id": "team-aurora",
  "player_ids": ["aurora-9", "aurora-8", "aurora-11"],
  "clock_ms": 32000,
  "video_time_ms": 34000,
  "facts": [
    {"key": "goals", "team_id": "team-aurora", "value": 1, "unit": "count",
     "origin": "event_count", "formula_version": "goals@1", "source_event_ids": ["evt-010"]},
    {"key": "shot_distance_m", "value": 14.2, "unit": "meters", "origin": "derived"},
    {"key": "sequence_passes", "value": 2, "unit": "count"},
    {"key": "seconds_since_recovery", "value": 11.0, "unit": "seconds"}
  ],
  "source_event_ids": ["evt-006", "evt-007", "evt-008", "evt-009", "evt-010"],
  "evidence_limits": [
    "Relación temporal entre ganar el balón y el tiro; los eventos no demuestran que una acción causara la otra."
  ],
  "signals": ["goal", "recovery_to_shot"],
  "reasons": [{"code": "base_kind", "points": 80}, {"code": "measured_fact", "points": 13},
              {"code": "combined_signals", "points": 5}, {"code": "novelty", "points": 10}]
}
```

| Campo | Para qué le sirve al agente |
|---|---|
| `kind` | Qué pasó. Hay 10 tipos: gol, tiro, recuperación y tiro, progresión rápida, presión sostenida, cambio de control, fase de caos, hito de jugador, recuperación alta y pase progresivo |
| `facts` | Las únicas cifras que puede decir, cada una con unidad y eventos de origen |
| `origin` de cada cifra | Si es `team_indicator` (control, impulso o caos), debe presentarla como escala del equipo, no como estadística oficial |
| `evidence_limits` | Lo que **no** puede afirmar. Por ejemplo, una causa táctica que los eventos no demuestran |
| `reasons` | Por qué se eligió el momento; útil para explicar «por qué importa» |
| `source_event_ids` | Para que el verificador contraste cada afirmación |

**`MatchSnapshot v1` (estado):** el estado completo del partido en un instante. Sirve para responder preguntas («¿cuántos tiros lleva Río?») y para los resúmenes. Incluye marcador, reloj, posesión y unas 150 cifras por equipo y jugador.

**Reglas para Persona 3:**
- No cambiar cifras ni fuentes.
- Respetar los límites de evidencia.
- Las preferencias del espectador solo cambian el enfoque y la redacción.

Ejemplos listos en [`ejemplos/`](ejemplos/), con un caso válido, uno mínimo y uno inválido de cada contrato.

## Qué recibe cada una de las demás personas

| Persona | Qué recibe | Qué necesito de ella |
|---|---|---|
| **Persona 4 (API y pantalla)** | `MatchAnalytics`, que ya cumple su `AnalyticsPort`, y los mismos dos contratos. Opcional: cifras de seguimiento en el snapshot con `tracking_provider`. | Aplicar los 2 ajustes y acordar dónde se aloja el procesador en Azure |
| **Persona 1 (datos y vídeo)** | La política de reconstrucción de eventos tardíos. La analítica de seguimiento ya consume su `VisualTrackObservation` y su identidad resuelta | Confirmar la política de tardíos, definir un mensaje de «corrección» de eventos, indicar en sus observaciones qué pista es el balón y cuál un portero, un vídeo permitido y un partido sintético más largo |
| **Persona 5 (UX/UI)** | La lista de tipos de momento, los tres indicadores propios y el tablero como referencia de qué datos existen | Diseñar cómo se muestran los indicadores propios y los avisos de velocidad y distancia |

## Cómo se integra con Azure

```text
Persona 1 publica eventos
        │
        ▼
Event Hubs · match-events   (grupo de consumidores "backend", reservado para Persona 2)
        │
        ▼
Procesador de Persona 2: valida, deduplica y marca tardíos (código de Persona 1),
reconstruye el estado, detecta y prioriza momentos
        │
        ├──► Event Hubs · match-insights
        │       grupo "narrative"  → Persona 3 (agentes)
        │       grupo "experience" → Persona 4 (API y pantalla)
        │       grupo "diagnostics" → pruebas
        │
        └──► Blob Storage · analytics/<partido>/<ejecución>/
                registro completo con hash SHA-256 de cada archivo (auditoría)

Blob Storage · matches  → metadatos del partido (los guarda Persona 1)
Blob Storage · models   → modelos xT y xG validados, cuando existan
```

Los mensajes que viajan por `match-insights`:

| Tipo de mensaje | Cuándo se envía |
|---|---|
| `match_snapshot.updated` | Con cada evento nuevo: estado actualizado |
| `insight_candidate.proposed` | Cuando aparece un momento o cambia uno existente |
| `insight_candidate.withdrawn` | Cuando un evento tardío o corregido invalida un momento |
| `match_state.revised` | Cuando se reconstruye el estado, con el marcador antes y después |

Todos los mensajes de un partido van en la misma partición (clave = `match_id`), así llegan en orden.

**Qué está listo:**
- Plantilla `infra/azure/analytics.bicep`: crea el hub `match-insights`, sus tres grupos de consumidores y los contenedores `analytics` y `models`. Reutiliza los recursos de Persona 1 sin modificarlos.
- Adaptadores de Event Hubs y Blob Storage probados con dobles.
- Procesador continuo (`analytics_stream_worker.py`).
- Prueba de humo de extremo a extremo (`analytics_azure_smoke.py`): publica un partido con un evento tardío y uno duplicado, y comprueba que los momentos recibidos desde Azure sean iguales a los calculados en local.
- Sin claves ni cadenas de conexión: todo usa la identidad de Azure (RBAC).

**Qué falta:**
- Desplegar en una suscripción y asignar roles.
- Compilar la plantilla (en este equipo no hay Azure CLI).
- Ejecutar la prueba de humo.
- Decidir dónde corre el procesador. Propuesta: Azure Container Apps junto con la API de Persona 4.

Medido en local: unos 3 ms de procesamiento por evento; el snapshot más grande pesa 106 KB, por debajo del límite de 1 MB de Event Hubs.

## Para profundizar

- [README de Persona 2](README.md)
- [Catálogo de métricas](catalogo-de-metricas.md)
- [Reglas de patrones y atención](reglas-de-patrones-y-atencion.md)
- [Analítica de seguimiento](analitica-de-seguimiento.md)
- [Integración con Azure](integracion-azure.md)
- [Informe de xT, VAEP y xG](informe-modelos-de-valor.md)
- [Evidencias](evidencias/README.md)
