# SDD-03 · Filtro, agentes y narrativa

## Especificación

**Objetivo:** gastar contexto y llamadas de IA solo donde aporten valor, y producir explicaciones respaldadas por hechos disponibles.

**Entradas:** ventanas de eventos, métricas, candidatos, preferencias y señales de control. **Salidas:** rutas, solicitudes reducidas, despachos, planes de evidencia, borradores y decisiones de validación.

Requisitos relacionados: RF-15, RF-16, RF-18, RF-21, RF-22, RF-34, RF-35 y RF-40 a RF-48. El catálogo incluye aspiraciones todavía pendientes, como investigación previa con fuentes externas; no se marcan cumplidas por disponer de un nombre de agente.

### Criterios de aceptación

1. Los eventos de solo métricas no invocan al orquestador narrativo.
2. Cada despacho conserva prioridad, TTL, correlación e idempotencia.
3. El contexto del agente contiene únicamente la evidencia y preferencias necesarias.
4. Una afirmación no sustentada se rechaza o se sustituye por una salida local identificable.
5. Un fallo del proveedor no altera marcador ni estadísticas ni bloquea toda la demo.
6. Se puede distinguir una plantilla, un fixture, una selección mediante CrewAI y una propuesta futura.

## Diseño implementado

`application/routing/` separa filtro, catálogo, refinador, orquestador y transporte. `AgentRoutingService` utiliza `FixtureDispatchGateway` por defecto. Ese gateway confirma de forma determinista la tarea recibida; no ejecuta una clasificación semántica remota.

`application/narrative/` define contratos, gateways y servicio de evidencia. `adapters/agents/crewai_gateway.py` compone cuatro etapas: observador, analista, selector narrativo y verificador. El modelo selecciona hechos/ángulos estructurados; no se le permite inventar estadísticas.

`Persona3NarrativeAdapter` conecta esa salida con la experiencia, humaniza identificadores y mantiene respaldos de `ProvisionalNarrative`. Resumen y verificación todavía delegan a métodos locales. `PrematchTacticsAgent` es un generador determinista independiente de la cadena CrewAI.

El worker de eventos importantes utiliza por defecto un manejador que registra despachos. Para ejecutar agentes reales detrás de la cola se necesita un manejador conectado, validación e idempotencia durable.

## Tareas y estado

- [x] Implementar seis rutas de filtro y solicitudes pequeñas con fuentes.
- [x] Definir contratos de despacho y una ejecución determinista de referencia.
- [x] Ofrecer proveedores `provisional`, `fixture` y `azure`.
- [x] Separar las etapas de CrewAI y sus despliegues configurables.
- [x] Implementar comprobaciones de afirmaciones y respaldo local.
- [ ] Conectar y verificar ejecutores de todas las tareas detrás de eventos importantes.
- [ ] Sustituir, cuando corresponda, el despacho fixture por un gateway semántico evaluado.
- [ ] Desarrollar investigación, validación de fuentes externas y aprobación de contexto previo.
- [ ] Verificar duración editorial de resúmenes de medio tiempo y calidad remota de narración.
- [ ] Medir latencia, coste y calidad por tarea con despliegues realmente disponibles.

## Validación

Pruebas principales: `test_agent_routing.py`, `test_routing_transport.py`, `test_important_event_worker.py`, `test_narrative.py` y `test_narrative_adapter_fallback.py`. Los fixtures viven en `apps/backend/tests/fixtures/`.

La prueba de parsing de CrewAI puede cargar el paquete real instalado y necesitar permisos para su almacenamiento local; se registra como fallo previo del entorno, sin afirmar validación de Azure. Consultar [agentes](../funcionamiento/agentes.md) y [resultados](validacion.md).
