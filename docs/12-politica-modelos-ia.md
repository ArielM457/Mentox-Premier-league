# **Política de modelos de IA**

Esta política asigna cada tarea al modelo que necesita por su dificultad, latencia y calidad esperada. Es una decisión inicial para la implementación. Debe validarse con casos del proyecto antes de subir o bajar la capacidad de un modelo.

## **Criterios de selección**

**1.** Los cálculos, filtros, reglas, métricas, deduplicación y validaciones exactas no usan un modelo de lenguaje.

**2.** Las clasificaciones breves y con salida estructurada usan GPT-4.1 mini. Ofrece capacidad suficiente para seguir instrucciones y usar herramientas sin pagar el coste de un modelo mayor en cada solicitud.

**3.** Las tareas donde importan la naturalidad, el razonamiento sobre varias evidencias y la calidad editorial usan GPT-4.1.

**4.** Ningún agente recibe todo el partido por defecto. El refinador entrega la ventana, las métricas y las fuentes necesarias para su tarea.

**5.** Solo se cambia el modelo cuando una evaluación muestre errores de calidad, latencia o coste. La novedad del modelo no es una razón suficiente.

## **Asignación inicial**

| Componente | Modelo inicial | Motivo |
|---|---|---|
| Servicio filtro | Sin modelo | Aplica reglas reproducibles y debe responder por evento. |
| Estado y métricas | Sin modelo | Calcula cifras exactas y auditables. |
| Catálogo de jugadas | Sin modelo | Compara señales contra patrones versionados. |
| Servicio de refinamiento | Sin modelo | Reduce y organiza el contexto. |
| Orquestador | GPT-4.1 mini | Clasifica solicitudes ambiguas con salida estructurada. Las rutas evidentes usan reglas. |
| Selector de momentos | GPT-4.1 mini | Decide relevancia sobre candidatos ya filtrados y ventanas pequeñas. |
| Validador rápido | Reglas y GPT-4.1 mini | Las reglas comprueban cifras y fuentes. El modelo revisa coherencia y separación entre hechos y simulaciones. |
| Agente de peligro | GPT-4.1 | Necesita explicar causas con varias señales y lenguaje natural. |
| Simulación contrafactual | Reglas y GPT-4.1 | Las reglas construyen cambios permitidos. El modelo explica escenarios y supuestos sin inventar probabilidades. |
| Narrador | GPT-4.1 | Requiere una salida más humana, contextual y adaptada al momento. |
| Agente de respuesta | GPT-4.1 mini o GPT-4.1 | Usa mini para preguntas directas. Usa GPT-4.1 cuando debe relacionar varias jugadas o producir una explicación editorial. |
| Resumen de medio tiempo | GPT-4.1 | Debe seleccionar, ordenar y redactar una pieza coherente de tres a cuatro minutos. |
| Resumen final | GPT-4.1 | Procesa más contexto y necesita mayor calidad editorial. |
| Researcher previo al partido | GPT-4.1 con búsqueda web | Busca, compara y entrega propuestas con fuentes y fechas. |
| Validador de fuentes | GPT-4.1 con búsqueda web | Contrasta afirmaciones, fechas y fuentes antes de la aprobación humana. |
| Personalización | Configuración y modelo del agente | No necesita un modelo propio. Cambia instrucciones, tono, detalle e idioma. |

GPT-4o mini puede quedar como alternativa de contingencia para clasificación de gran volumen cuando las mediciones demuestren que mantiene la calidad. No será el modelo inicial del proyecto.

El modelo GPT-4 original no se usará. Está obsoleto para nuevas integraciones y no ofrece las capacidades actuales de herramientas y salidas estructuradas que necesita este flujo.

## **Búsqueda web e información previa**

La opción operativa recomendada es GPT-4.1 mediante Responses API con la herramienta `web_search`. El researcher debe usar búsqueda solo durante la preparación previa o una actualización controlada. Cada resultado conserva URL, título, fecha de consulta, fecha del hecho y fragmento que sostiene la afirmación.

| Opción formal | Uso en el proyecto | Decisión |
|---|---|---|
| GPT-4.1 con `web_search` | Investigación previa y validación de fuentes con búsqueda controlada | Opción inicial |
| `gpt-5-search-api` | Búsqueda obligatoria mediante Chat Completions | Alternativa si la integración lo requiere |
| Modelo vigente de investigación profunda | Informes extensos preparados con anticipación | Solo para casos excepcionales |
| Embeddings con índice interno | Recuperación de información aprobada | No realiza búsqueda web |

Si la integración se mantiene en Chat Completions y necesita un modelo especializado que siempre busque, se puede evaluar `gpt-5-search-api`. No es la opción inicial porque obliga a buscar incluso cuando la base aprobada ya contiene la respuesta.

Los modelos de investigación profunda se reservan para informes programados que admitan mayor tiempo y coste. No se usan para el partido en directo. Antes de incorporarlos se debe comprobar el modelo vigente en la documentación oficial, porque estas familias cambian con mayor frecuencia.

No se usarán `gpt-4o-search-preview` ni `gpt-4o-mini-search-preview` en una implementación nueva porque están retirados.

## **Uso de embeddings**

Un modelo de embeddings sirve para buscar por significado dentro de `PregameFact`, el catálogo de jugadas o documentos internos aprobados. No navega por Internet ni verifica que un hecho siga vigente.

La primera versión puede comenzar con filtros por metadatos y búsqueda de texto. Se añadirá un índice vectorial solo si las pruebas muestran que mejora la recuperación interna. El nombre concreto del modelo de embeddings queda como decisión de infraestructura y no forma parte de la búsqueda web.

## **Configuración propuesta**

Los nombres de despliegue deben estar separados del nombre comercial del modelo:

```text
AZURE_OPENAI_ROUTER_DEPLOYMENT=clasificacion-rapida
AZURE_OPENAI_NARRATIVE_DEPLOYMENT=narrativa-calidad
OPENAI_RESEARCH_MODEL=gpt-4.1
```

`clasificacion-rapida` apunta a GPT-4.1 mini y `narrativa-calidad` apunta a GPT-4.1. La búsqueda se implementa detrás de un adaptador para no acoplar el dominio a Responses API, Azure OpenAI o un proveedor concreto.

La disponibilidad de modelos, herramientas, regiones y cuotas debe comprobarse en el entorno que usará el equipo. Ninguna credencial se guarda en el repositorio.

## **Evaluación antes de fijar el modelo**

Cada agente tendrá un conjunto pequeño de solicitudes representativas con salida esperada. Mediremos:

- cumplimiento del esquema
- afirmaciones sin evidencia
- calidad y naturalidad del texto
- selección correcta de momentos
- conservación de fuentes e identificadores
- latencia y coste por solicitud

Primero probamos el modelo asignado en esta tabla. Si falla la calidad, ajustamos contexto e instrucciones y luego evaluamos GPT-4.1. Si supera ampliamente la prueba, evaluamos GPT-4.1 mini. El cambio se registra con los resultados y no se aplica a todos los agentes de forma automática.

## **Referencias oficiales**

- [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
- [GPT-4.1](https://developers.openai.com/api/docs/models/gpt-4.1)
- [GPT-4o mini](https://developers.openai.com/api/docs/models/gpt-4o-mini)
- [Búsqueda web](https://developers.openai.com/api/docs/guides/tools-web-search)
- [Investigación profunda](https://developers.openai.com/api/docs/guides/deep-research)
