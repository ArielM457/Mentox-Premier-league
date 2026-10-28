# Agentes, enrutamiento y narrativa

## Qué significa «agente» en este proyecto

El código contiene reglas deterministas, generadores de simulación, solicitudes de tareas y una cadena opcional de CrewAI. No todas las clases llamadas agente ejecutan un modelo de lenguaje. Esta distinción permite explicar qué aporta IA y qué se calcula directamente.

## Etapas antes de la narrativa

| Componente | Función | Implementación actual |
|---|---|---|
| Filtro | Separar métricas, candidato, peligro, tiempo muerto, resumen y rechazo | Reglas en `application/routing/filter.py` |
| Catálogo | Reconocer señales y límites de una jugada | Reglas versionadas en `routing/catalog.py` |
| Refinador | Reducir ventana y evidencia a una solicitud | `routing/refinement.py` |
| Orquestador | Crear destino, prioridad, TTL y clave de idempotencia | `routing/orchestrator.py`; `FixtureDispatchGateway` predeterminado |
| Worker importante | Consumir y confirmar despachos | `important_event_worker.py`; el manejador base registra el despacho |

Los destinos del contrato son peligro/simulación, selector de momentos, narrador y resumen. Para afirmar que un agente se ejecuta desde una cola se debe comprobar el manejador conectado, no solo el `target_agent` de un mensaje.

## Proveedores narrativos

| Valor de `NARRATIVE_PROVIDER` | Comportamiento |
|---|---|
| `provisional` | Texto y respuestas locales mediante plantillas; no hace una llamada LLM |
| `fixture` | Adaptador de Persona 3 con gateway repetible sin red, para probar contratos |
| `azure` | Adaptador de Persona 3 con CrewAI y despliegues Azure configurados |

`adapters/http/registry.py` elige el proveedor. La configuración predeterminada es provisional. Instalar el extra `agents` solo habilita las dependencias; no activa Azure ni crea modelos.

## Cadena de CrewAI

`adapters/agents/crewai_gateway.py` crea una secuencia de cuatro etapas:

1. **Observador de evidencia:** selecciona índices de hechos aportados.
2. **Analista:** propone una interpretación prudente y señala lo que falta.
3. **Selector narrativo:** elige hechos y ángulo adecuados para el espectador.
4. **Verificador:** rechaza selecciones no respaldadas.

Las salidas se validan con modelos estructurados (`ObservedFacts`, `AnalysisProposal`, `SelectionProposal`, `ReviewProposal`). El servicio narrativo comprueba afirmaciones contra los hechos disponibles. El modelo no calcula el marcador ni genera estadísticas nuevas.

Las etapas rápidas usan el despliegue de router; analista y selector, el de narrativa. El código configura temperatura cero, límites de tokens, timeout y ausencia de reintentos automáticos en ese gateway.

## Configuración de Azure

Las variables están en `apps/backend/.env.example`:

```text
NARRATIVE_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://<recurso>.cognitiveservices.azure.com
AZURE_OPENAI_DEPLOYMENT=<despliegue-base>
AZURE_OPENAI_ROUTER_DEPLOYMENT=<despliegue-rapido>
AZURE_OPENAI_NARRATIVE_DEPLOYMENT=<despliegue-narrativo>
AZURE_OPENAI_API_VERSION=<version-compatible-con-el-recurso>
AZURE_OPENAI_API_KEY=<secreto-del-backend>
```

En el código actual el despliegue base sigue siendo obligatorio; los otros dos pueden heredar su valor si no se definen. Los nombres de despliegue son configuración del recurso, no una garantía sobre el modelo comercial disponible. Verificar región, cuotas y compatibilidad en el entorno antes de declarar la integración operativa.

La documentación histórica proponía modelos distintos según dificultad. En esta consolidación se conserva el principio: cálculos y validaciones exactas sin LLM, tareas breves con un despliegue rápido y explicaciones complejas con uno de mayor calidad. No se cambia ni recomienda un modelo nuevo como parte de esta reorganización.

## Respaldos y límites

`Persona3NarrativeAdapter` mantiene `ProvisionalNarrative`. Su generación de overlays puede conservar redacción local incluso después de seleccionar evidencia con el proveedor; resumen y verificación delegan a métodos locales. Una interfaz que muestra texto no demuestra por sí sola que ese texto haya sido redactado por Azure.

`PrematchTacticsAgent` genera formaciones y secuencias sintéticas con código. Las comparaciones de `what_if.py` son simulaciones locales. La investigación web previa, contraste de fuentes externas y aprobación de contexto no están conectados como una cadena completa de agentes operativa.

## Cómo evaluar una modificación

Probar esquema, afirmaciones sin soporte, fuentes, preferencias, comportamiento sin proveedor, latencia y coste por tarea. Registrar proveedor y despliegues sin claves. Usar las pruebas de narrativa/enrutamiento y añadir un caso reproducible cuando cambie el comportamiento. Los resultados actuales están en [validación](../desarrollo/validacion.md).
