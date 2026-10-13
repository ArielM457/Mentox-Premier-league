# Resumen para el daily · Persona 2 (estado y analítica)

Actualizado el 13 de octubre de 2026. Rama `persona-2/estado-analitica`.

## En un minuto

- **Hecho:** el motor de estado y analítica está terminado y probado en local. Recibe eventos `MatchEvent 1.0` y entrega estado del partido (`MatchSnapshot v1`), momentos candidatos con prioridad y motivos (`InsightCandidate v1`) y cifras de velocidad y distancia desde las observaciones de visión de Persona 1. Hay 225 pruebas pasando: 134 de antes y 91 de Persona 2.
- **Desde el último daily:** adapté la analítica a lo que ya hizo Persona 1 y dejé en Persona 2 solo la analítica. También revisé las ramas nuevas de Persona 3 y Persona 4 y las probé juntas con la mía.
- **Demo:** [`demo/tablero.html`](demo/tablero.html) reproduce un partido sintético con todo lo que calcula el motor.
- **Siguiente:** acordar los contratos con Persona 3, desplegar en Azure, recibir las observaciones reales de vídeo de Persona 1 y cerrar la integración con Persona 4.
- **Bloqueos:**
  - Falta una suscripción de Azure con permisos para desplegar.
  - Falta un vídeo permitido (Persona 1).
  - Los contratos de Persona 3 todavía no aceptan las salidas del motor (ver más abajo).

## Novedades desde el último daily

### Adaptación a Persona 1

| Antes | Ahora |
|---|---|
| La analítica de seguimiento tenía su propio formato de entrada (`TrackingFrame`) | Consume lo que Persona 1 ya definió: `VisualTrackObservation`, `ResolvedVisualIdentity` y `PredictionOrigin` |
| Persona 2 tenía un conversor de Roboflow Sports | Se eliminó: convertir la salida del detector es de Persona 1 (DV-US-19) |
| La identidad del jugador venía en las posiciones | Solo se usa una identidad confirmada por Persona 1 (DV-US-12); si hay dos contradictorias, se descarta |
| El origen se marcaba `synthetic_mock` / `video_model` | Se usa el vocabulario de Persona 1: `simulated_fixture` / `actual_model` |
| El escenario de prueba, los datos simulados y los generadores de ejemplos estaban en `src/.../adapters/sources/` | Están en `apps/backend/tests/`; `adapters/sources/` queda solo con el generador de Persona 1 |

Los cálculos (velocidad, distancia, sprints, presión por cercanía y forma del equipo) no cambiaron. Las observaciones simuladas ya tienen el formato de Persona 1 y resuelven la identidad con su `PlayerIdentityResolver`. Con datos de prueba, la analítica recorre el mismo camino que con vídeo real.

### Revisión de las ramas del equipo

- **`main`:** sin cambios desde que se creó la rama de Persona 2.
- **`feat/persona-4-api-frontend`:** mismo contenido que la rama que ya probé. Integrando `MatchAnalytics`, pasan 240 de 242 pruebas; las 2 restantes necesitan ajustes pequeños en su rama.
- **`feat/persona-3-agentes-narrativa`:** trae narrativa con CrewAI y Azure OpenAI, un filtro y enrutamiento de agentes y una colección de Postman. Hay cuatro puntos que tocan la analítica:
  1. **Requisitos nuevos para Persona 2.** Editó el plan de Persona 2 y le asignó los requisitos RF-40 a RF-45: un servicio filtro (`RoutingDecision v1`) y un catálogo de jugadas (`PlayContext v1`).
  2. **Filtro y catálogo duplicados.** Su rama ya trae ese filtro y ese catálogo, que vuelven a contar métricas. Sus reglas de peligro y de progresión no tienen en cuenta hacia qué lado ataca cada equipo, así que fallan para el visitante en el primer período y para todos en el segundo.
  3. **Contratos incompatibles.** Definió sus propios `MatchSnapshot` e `InsightCandidate`, más estrictos. Ninguna salida del motor pasa su validación:
     - no acepta cifras «no disponibles»;
     - exige al menos un evento de origen incluso en un cero observado;
     - pide que las fuentes de cada hecho estén en la lista del momento;
     - espera un solo texto de motivo, no la lista con puntos.
  4. **Canal de eventos reabierto.** Propone comparar Redis, RabbitMQ y Kafka, cuando el equipo ya eligió Azure Event Hubs (decisión 10) y Persona 1 y Persona 2 lo usan.
- **Merge de prueba de las tres ramas:**
  - Aparecen 4 conflictos y se resuelven conservando ambos lados.
  - Pasan 294 pruebas, 1 se omite y 1 falla.
  - La que falla es la colección de Postman de Persona 3: no incluye las rutas de Persona 4.

**Propuesta para Persona 3:**
- Un solo filtro y un solo catálogo, dentro del motor de Persona 2, que ya normaliza la dirección de ataque.
- Un solo contrato: que importe los modelos de Persona 2, como hará Persona 4.
- Mantener Event Hubs.

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

Observaciones de visión de Persona 1 (VisualTrackObservation + identidad resuelta)
  → seguimiento: distancia, velocidad, sprints, velocidad del balón y del tiro,
                 presión por cercanía, forma del equipo y avisos por umbral
```

Cuatro ideas para explicarlo:

1. **Toda cifra se puede comprobar.** Cada número lleva fórmula, unidad, versión y los eventos o pistas de donde sale. Si faltan datos, aparece como «no disponible», nunca como cero.
2. **La IA no calcula cifras.** El motor calcula; los agentes de Persona 3 explican. Así un agente no puede inventar un dato.
3. **La prioridad se explica.** Es una suma visible de motivos: tipo de momento, fuerza del hecho, novedad, repetición y preferencias. Los momentos descartados también quedan registrados con su motivo.
4. **Personalización sin cambiar los hechos.** Casual, analista, club favorito y modo jugador cambian qué momentos salen y con qué prioridad, pero no las cifras. Los goles del rival salen siempre.

Con el partido de prueba de 178 eventos: el perfil casual recibe 14 momentos, el analista 33 y el modo jugador de L. Sol 9.

## Qué está acoplado hoy

| Con quién | Qué se conectó | Estado |
|---|---|---|
| Persona 1 (datos) | Uso su contrato `MatchEvent 1.0`, su validación, su deduplicación y su detector de eventos tardíos. Cuando llega un evento tardío, el motor reconstruye el estado; eso cierra lo pendiente en DV-US-05 cuando ella acepte la política. | Probado en local |
| Persona 1 (vídeo) | El motor cumple su interfaz `MatchStateRebuilder`: al adelantar o retroceder el vídeo, el estado se reconstruye. | Probado en local |
| Persona 1 (visión) | La analítica de seguimiento consume sus `VisualTrackObservation`, `ResolvedVisualIdentity` y `PredictionOrigin`. | Probado con observaciones simuladas en su formato |
| Persona 1 (Azure) | Un puente lee los eventos que su consumidor de Event Hubs ya validó, sin modificar su código. | Probado con dobles de Azure |
| Persona 4 (API) | `MatchAnalytics` implementa su `AnalyticsPort` (`snapshot` y `candidates`). En una copia de su rama pasan 240 de 242 pruebas. | Faltan 2 ajustes en su rama |
| Persona 3 (agentes) | Tiene los contratos y ejemplos de Persona 2. | Bloqueado: sus contratos no aceptan las salidas del motor |

Los 2 ajustes de Persona 4 son pequeños. Uno es cambiar `moment-evt-006` por `moment-evt-009` en una prueba. El otro es añadir textos para los tipos de momento nuevos en su narración provisional.

## Qué usa datos simulados (mocks)

Todos los datos simulados están en `apps/backend/tests/`, fuera del código de producción.

| Parte | Qué se simula | Por qué | Qué lo reemplaza |
|---|---|---|---|
| Posiciones de jugadores y balón | Observaciones generadas desde los eventos con una cinemática simple, 5 por segundo, con el formato de Persona 1 (`VisualTrackObservation`) | No hay vídeo permitido procesado | Las observaciones reales de vídeo de Persona 1, sin cambiar la analítica |
| Distancias, velocidades y avisos por umbral | El cálculo es real, pero sobre posiciones simuladas | Depende de lo anterior | Lo mismo: con observaciones reales, el cálculo no cambia |
| Frases de los momentos en el tablero | Plantillas de ejemplo | La narración es de Persona 3 | Los agentes de Persona 3 |
| Azure en las pruebas | Clientes simulados de Event Hubs y Blob Storage | No hay suscripción desplegada | El despliegue y la prueba de humo ya están escritos |
| Partido | Escenario sintético de 178 eventos con fases diseñadas (`tests/analytics_scenarios.py`) | El reto exige datos sintéticos | Partidos más largos de Persona 1 |

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

**Qué hay que acordar con Persona 3:**
- Usar estos contratos en lugar de sus copias.
- Si conserva las suyas, ajustar las cuatro reglas que hoy rechazan las salidas.
- Quién implementa el filtro y el catálogo de jugadas que le asignó a Persona 2.

Ejemplos listos en [`ejemplos/`](ejemplos/), con un caso válido, uno mínimo y uno inválido de cada contrato.

## Qué recibe cada una de las demás personas

| Persona | Qué recibe | Qué necesito de ella |
|---|---|---|
| **Persona 4 (API y pantalla)** | `MatchAnalytics`, que ya cumple su `AnalyticsPort`, y los mismos dos contratos. Opcional: cifras de seguimiento en el snapshot con `tracking_provider`. | Aplicar los 2 ajustes y acordar dónde se aloja el procesador en Azure |
| **Persona 1 (datos y vídeo)** | La política de reconstrucción de eventos tardíos y una analítica de seguimiento que ya consume sus observaciones de visión | Confirmar la política de tardíos, definir un mensaje de «corrección» de eventos, indicar en sus observaciones qué pista es el balón y cuál un portero, un vídeo permitido y un partido sintético más largo |
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
- Cerrar con Persona 3 que el canal sigue siendo Event Hubs (decisión 10). Su rama propone comparar otras opciones.

Medido en local: unos 3 ms de procesamiento por evento; el snapshot más grande pesa 106 KB, por debajo del límite de 1 MB de Event Hubs.

## Para profundizar

- [README de Persona 2](README.md)
- [Catálogo de métricas](catalogo-de-metricas.md)
- [Reglas de patrones y atención](reglas-de-patrones-y-atencion.md)
- [Analítica de seguimiento](analitica-de-seguimiento.md)
- [Integración con Azure](integracion-azure.md)
- [Informe de xT, VAEP y xG](informe-modelos-de-valor.md)
- [Evidencias](evidencias/README.md)
