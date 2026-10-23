# **Persona 3: agentes e inteligencia narrativa**

## **Objetivo**

Convertir solicitudes refinadas en explicaciones verificables durante el partido, respuestas, contenido contextual y resúmenes. Esta persona mantiene la narrativa, la coordinación de agentes y la validación previa a la publicación.

El módulo no calcula el marcador ni reemplaza el estado oficial del partido. Los eventos de solo métricas deben terminar antes del orquestador. Persona 2 mantiene las reglas del filtro y el catálogo. Persona 3 consume sus decisiones y prepara el trabajo de IA.

La arquitectura completa está en [arquitectura de eventos y agentes](../10-arquitectura-agentes.md). La secuencia de entregas está en [plan de implementación](../11-plan-implementacion-agentes-eventos.md) y la selección de modelos está en [política de modelos de IA](../12-politica-modelos-ia.md).

## **Flujo acordado**

**1.** `MatchEvent 1.0` entra al filtro determinista.

**2.** El filtro actualiza métricas y produce `RoutingDecision v1`.

**3.** El catálogo aporta `PlayContext v1` con patrones, señales y datos faltantes.

**4.** El refinador construye `AgentRequest v1` con contexto reducido, preferencias, prioridad y vencimiento.

**5.** El orquestador crea `AgentDispatch v1` y envía la tarea al agente correspondiente.

**6.** El agente propone una explicación, respuesta, narración o resumen.

**7.** El validador comprueba cifras, evidencia, fuentes y separación entre hechos y simulaciones.

**8.** Persona 4 recibe solamente resultados aprobados o pendientes de revisión editorial.

## **Responsabilidades del módulo**

**1. Orquestador ligero.** Recibir `AgentRequest v1` y elegir el trabajador. Las rutas evidentes usan reglas. GPT-4.1 mini se reserva para solicitudes ambiguas. No recibe eventos de solo métricas.

**2. Servicio de refinamiento.** Preparar un contexto pequeño con decisión, métricas relacionadas, jugada reconocida, preferencias y referencias. Aplicar límites de tamaño y no copiar todo el partido.

**3. Peligro y simulación.** Explicar por qué una ocasión fue peligrosa y producir escenarios contrafactuales opcionales. Cada escenario indica el cambio supuesto, conserva evidencia y se marca como simulación. No modifica el estado real ni se presenta como predicción.

**4. Selección de momentos.** Evaluar candidatos durante el partido con ventanas configurables. Puede reunir hasta dos minutos de contexto para un candidato normal. Las alertas urgentes no esperan esa ventana.

**5. Narración y preguntas.** Generar guiones en español e inglés desde hechos del partido y contenido previo aprobado. Aplicar modo, nivel, club y jugador como configuración compartida. Reconocer cuando la evidencia no permite responder.

**6. Investigación previa.** Proponer datos de jugadores, estadio, cuerpo técnico, contexto del fútbol, sucesos recientes y próximos contenidos autorizados. Validar fuentes y enviar los datos a confirmación humana antes de almacenarlos.

**7. Resúmenes y revisión.** Generar un resumen de medio tiempo con objetivo de tres a cuatro minutos y un resumen final más amplio. Usar el acumulado completo, incluidos datos que no se narraron en directo. El resumen final queda pendiente de aprobación.

**8. Validador rápido.** Revisar cifras, evidencia, fuentes, vigencia, estructura y separación entre hechos y simulaciones. Devolver aprobación, corrección o rechazo. Toda corrección vuelve a validarse.

**9. Reportes de error.** Contrastar el reporte con métricas, eventos y fuentes. Registrar el resultado y conservar la relación entre el borrador original y la corrección.

## **Estado implementado en esta rama**

### **Narrativa basada en evidencia**

El backend ya contiene `NarrativeService` y los contratos de narrativa. El servicio puede:

- crear una narración en directo
- responder preguntas
- crear un resumen final pendiente de aprobación
- resolver reportes de error
- producir español e inglés
- diferenciar modos casual, analista, club y jugador
- rechazar afirmaciones que no estén respaldadas por hechos recibidos

Existe un proveedor local reproducible para pruebas y un adaptador CrewAI para Azure OpenAI. El flujo CrewAI actual ejecuta observación, análisis, selección y verificación de forma secuencial. Esta implementación sirve como base y todavía debe adaptarse a trabajadores independientes por eventos.

### **Filtro, refinamiento y despacho**

Se implementó una primera versión local de `AgentRoutingService`. Su recorrido es:

```text
RoutingEvaluationRequest
  -> EventFilterService
  -> PlayCatalog
  -> AgentRequestRefiner
  -> AgentOrchestrator
  -> RoutingOutcome
```

El filtro realiza estas acciones sin llamar a un modelo:

- ordena los eventos por período, reloj e identificador
- ignora identificadores ya procesados
- calcula cambios de métricas por equipo
- separa métricas, candidatos, peligro, pausa, resumen y rechazo
- conserva los identificadores de origen

El catálogo reconoce dos patrones iniciales:

- tiro desde una zona peligrosa
- recuperación seguida de dos pases y progresión rápida

El refinador solo crea una solicitud para rutas narrativas. Asigna estas tareas y tiempos de vigencia iniciales:

| Ruta | Agente | Tiempo de vigencia |
|---|---|---:|
| `danger_immediate` | `danger_simulation` | 8 segundos |
| `moment_candidate` | `moment_selector` | 120 segundos |
| `dead_ball_context` | `narrator` | 15 segundos |
| `recap` | `recap` | 300 segundos |

`metrics_only` y `rejected` no crean `AgentRequest` ni `AgentDispatch`.

El orquestador usa por ahora `FixtureDispatchGateway`. Produce siempre el mismo resultado para la misma solicitud, incluye correlación y clave de idempotencia, y bloquea un cambio de agente que no esté respaldado por la ruta. GPT-4.1 mini todavía no está conectado.

## **Contratos creados**

**1. `RoutingEvent`.** Copia de aplicación de `MatchEvent 1.0` para no acoplar el caso de uso al adaptador HTTP.

**2. `ControlSignal`.** Representa pausa, final de período y final del partido mientras se define la siguiente versión del contrato de eventos.

**3. `MetricUpdate`.** Registra métrica, equipo, valor, unidad, versión de fórmula y eventos de origen.

**4. `RoutingDecision v1`.** Contiene ruta, prioridad, motivos, regla aplicada y eventos de origen.

**5. `PlayContext v1`.** Contiene patrón, nivel de coincidencia, señales presentes, señales faltantes y evidencia.

**6. `AgentRequest v1`.** Contiene tarea, prioridad, reloj, tiempo de vigencia, métricas pequeñas, contexto de jugada y preferencias.

**7. `AgentDispatch v1`.** Contiene destino, correlación, idempotencia, prioridad y motivo del despacho.

**8. `RoutingOutcome`.** Reúne la decisión, actualizaciones de métricas, contexto, solicitud, despacho e identificadores ignorados.

Los contratos anteriores complementan `MatchSnapshot v1`, `InsightCandidate v1`, `NarrativeDraft v1` y los contratos de preguntas, resúmenes y reportes del módulo de narrativa.

## **API disponible**

### **Enrutamiento**

`POST /api/v1/agent-routing/evaluate`

Recibe el partido, una ventana de eventos, una señal de control opcional, identificadores ya procesados y preferencias. Devuelve `RoutingOutcome`. Esta operación es reproducible, no usa Azure y actualmente no conserva estado entre peticiones.

### **Narrativa**

- `POST /api/v1/narratives/live`
- `POST /api/v1/narratives/questions`
- `POST /api/v1/narratives/summaries`
- `POST /api/v1/narratives/reports/resolve`

Las tres primeras operaciones permiten `provider=fixture` para pruebas locales. Sin ese parámetro usan el adaptador de Azure OpenAI. El reporte de error se resuelve contra la evidencia y no necesita que React llame directamente a CrewAI.

## **Escenarios sintéticos agregados**

El archivo `apps/backend/tests/fixtures/agent-routing-scenarios.json` contiene seis solicitudes:

**1. Pase de solo métricas.** Actualiza pases y no llama agentes.

**2. Progresión candidata.** Reconoce recuperación y progresión, y prepara al selector con una ventana de dos minutos.

**3. Tiro peligroso.** Activa `danger_simulation` con prioridad alta.

**4. Pausa del juego.** Prepara al narrador para usar contexto previo aprobado.

**5. Medio tiempo.** Solicita un resumen con objetivo de tres a cuatro minutos.

**6. Final del partido.** Solicita un resumen amplio que deberá quedar pendiente de aprobación editorial.

## **Política de modelos**

La selección se realiza por demanda:

| Trabajo | Modelo inicial |
|---|---|
| Filtro, métricas, catálogo y refinamiento | Sin modelo |
| Orquestación, selección y validación semántica breve | GPT-4.1 mini |
| Peligro, simulación redactada, narración y resúmenes | GPT-4.1 |
| Preguntas directas | GPT-4.1 mini |
| Preguntas con varias evidencias | GPT-4.1 |
| Researcher y validación de fuentes | GPT-4.1 con `web_search` |

Los embeddings solo se evaluarán para recuperar información interna aprobada. No reemplazan la búsqueda web. GPT-4o mini queda como alternativa de contingencia después de medir calidad y carga.

## **Archivos principales**

### **Narrativa existente**

- `apps/backend/src/match_intelligence/application/narrative/contracts.py`
- `apps/backend/src/match_intelligence/application/narrative/service.py`
- `apps/backend/src/match_intelligence/application/narrative/gateway.py`
- `apps/backend/src/match_intelligence/adapters/agents/crewai_gateway.py`
- `apps/backend/src/match_intelligence/adapters/http/narrative_router.py`
- `apps/backend/tests/test_narrative.py`

### **Enrutamiento agregado**

- `apps/backend/src/match_intelligence/application/routing/contracts.py`
- `apps/backend/src/match_intelligence/application/routing/filter.py`
- `apps/backend/src/match_intelligence/application/routing/catalog.py`
- `apps/backend/src/match_intelligence/application/routing/refinement.py`
- `apps/backend/src/match_intelligence/application/routing/orchestrator.py`
- `apps/backend/src/match_intelligence/application/routing/service.py`
- `apps/backend/src/match_intelligence/adapters/http/routing_router.py`
- `apps/backend/tests/test_agent_routing.py`
- `apps/backend/tests/fixtures/agent-routing-scenarios.json`

### **Documentación y pruebas manuales**

- `apps/backend/README-narrativa.md`
- `docs/10-arquitectura-agentes.md`
- `docs/11-plan-implementacion-agentes-eventos.md`
- `docs/12-politica-modelos-ia.md`
- `postman/match-intelligence.postman_collection.json`

## **Comprobaciones cubiertas**

Las pruebas verifican:

- contratos estrictos y coincidencia del partido
- evidencia obligatoria para las afirmaciones
- idiomas y modos de usuario
- preguntas con evidencia suficiente e insuficiente
- resumen final pendiente de aprobación
- reportes válidos y reportes falsos
- bloqueo cuando un agente falla o inventa hechos
- selección de cada ruta sintética
- exclusión de métricas del orquestador
- deduplicación sin repetir métricas
- contexto reducido y trazable
- exposición del endpoint HTTP
- bloqueo de un despacho incompatible
- mismo resultado e idempotencia para la misma entrada

La colección de Postman incluye todas las operaciones públicas actuales y un caso de enrutamiento para cada escenario importante.

La validación local del 11 de octubre de 2026 completó 41 pruebas del backend. La colección generada contiene 16 solicitudes. También se comprobó la compilación de los módulos Python. Las nueve advertencias observadas proceden de CrewAI y Pydantic durante la prueba del adaptador y no causaron fallos.

## **Trabajo pendiente**

**1.** Conectar GPT-4.1 mini al orquestador y separar los despliegues de clasificación y narrativa.

**2.** Reemplazar el flujo CrewAI secuencial por trabajadores independientes que consuman solicitudes desde un canal durable.

**3.** Guardar eventos, progreso del consumidor, decisiones, contexto aprobado y resúmenes fuera de las instancias.

**4.** Implementar la simulación contrafactual con reglas sobre datos sintéticos y validación de supuestos.

**5.** Implementar ventanas persistentes para el selector de momentos.

**6.** Crear el researcher, la validación de fuentes, la aprobación humana y la base `PregameFact`.

**7.** Crear el resumen de medio tiempo y ajustar ambos resúmenes con lectura o voz medida.

**8.** Incorporar faltas, pausas y reanudaciones a una nueva versión de eventos o a una señal formal del reproductor.

**9.** Probar Azure OpenAI, búsqueda web, cuotas, latencia y disponibilidad en el entorno real.

**10.** Ejecutar pruebas de carga y fallos con varias instancias y varios partidos.

## **Trabajo independiente e integración**

Persona 3 puede continuar con snapshots, decisiones, solicitudes y momentos sintéticos. No necesita que Roboflow, SoccerNet ni las métricas avanzadas funcionen. Debe usar el proveedor local antes de conectar modelos externos.

Persona 2 entrega estado, métricas, `RoutingDecision v1` y `PlayContext v1`. Persona 3 entrega solicitudes, despachos y borradores. Persona 4 consume respuestas de la API y convierte narraciones aprobadas en `OverlayMessage v1`. React no llama directamente a los agentes.

## **Criterios para dar el módulo por terminado**

**1.** Cada cifra y afirmación coincide con su evidencia.

**2.** Los eventos de solo métricas nunca llaman a un modelo.

**3.** Los dos idiomas conservan los mismos datos.

**4.** Los modos casual y analista cambian enfoque y detalle.

**5.** Las simulaciones se distinguen de los hechos reales.

**6.** Un reporte válido produce una corrección trazable y un reporte falso no altera una conclusión correcta.

**7.** Un resumen final sin aprobación no se publica.

**8.** La caída de un modelo no detiene el estado ni las métricas.

**9.** La entrega incluye contratos, escenarios, pruebas automáticas, colección de Postman y demostración desde la API.

Requisitos principales: RF-15, RF-16, RF-18, RF-21 a RF-28 y RF-34 a RF-48.
