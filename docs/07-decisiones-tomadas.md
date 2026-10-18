# **Decisiones tomadas**

Este documento registra lo acordado por el equipo el 6 y el 8 de octubre de 2026. Describe elecciones de diseño, no funciones ya terminadas.

## **Datos y eventos**

**1.** Definimos un formato interno común para los eventos. El contrato inicial y sus campos están en [formato de eventos](08-formato-de-eventos.md). Los adaptadores de cualquier fuente deben entregar ese mismo formato al núcleo del sistema.

**2.** Usaremos dos vías para obtener datos sintéticos: generaremos partidos propios y adaptaremos conjuntos adecuados como referencia. Antes de incorporar una fuente revisaremos sus condiciones de uso. No distribuiremos datos reales de la Premier League.

## **Tecnologías y repositorio**

**3.** El proyecto es un monorepo. El frontend estará en `apps/frontend` con JavaScript y React. El backend estará en `apps/backend` con Python, FastAPI y Uvicorn. FastAPI expondrá su documentación OpenAPI mediante Swagger UI en `/docs`.

**4.** Usaremos un monolito modular con límites hexagonales. El dominio del partido y sus reglas no deben depender de FastAPI, CrewAI, del origen de eventos ni de la interfaz. Los adaptadores conectarán vídeo, conjuntos sintéticos, agentes y API con el núcleo.

**4.1.** El backend usará Python 3.12. La versión se fija mediante `.python-version`, el paquete declara compatibilidad `>=3.12,<3.14` y `uv.lock` conserva las dependencias resueltas. Python 3.14 queda excluido mientras CrewAI no lo admita.

Para el flujo continuo mantendremos esos límites y añadiremos comunicación por eventos. El filtro, refinador, orquestador y trabajadores podrán desplegarse en varias instancias. Podemos iniciar dentro del monorepo y separar procesos sin cambiar los contratos del dominio.

## **Agentes y publicación**

**5.** Usaremos CrewAI en Python para coordinar tareas que necesiten interpretación. El 11 de octubre de 2026 refinamos el diseño: un servicio filtro, un catálogo de jugadas y un servicio de refinamiento prepararán la información antes de cualquier modelo. Un orquestador ligero enviará solo las solicitudes relevantes a agentes especializados mediante eventos.

La personalización será una política compartida y no un agente independiente en la primera versión. Las métricas y el estado seguirán un camino directo sin llamar a la IA. Los agentes principales cubrirán peligro y simulación, selección de momentos, narración, preguntas, resúmenes e investigación previa. La validación será obligatoria antes de publicar.

La distribución inicial de trabajo y el flujo de revisión están en [equipo de agentes](10-arquitectura-agentes.md).

El 11 de octubre de 2026 acordamos una asignación por demanda. GPT-4.1 mini será la base para clasificación, selección breve y validación semántica. GPT-4.1 se usará en narración, explicación de peligro, redacción de simulaciones, respuestas complejas, resúmenes e investigación. Los servicios deterministas no usarán modelos. La política completa está en [política de modelos de IA](12-politica-modelos-ia.md).

La investigación previa usará GPT-4.1 con una herramienta de búsqueda web. Los embeddings se reservan para recuperación semántica dentro de información aprobada y no reemplazan la búsqueda en Internet.

Los agentes podrán proponer interpretaciones y deducir conclusiones desde evidencia disponible. Los cálculos de cifras y el estado del partido serán reproducibles. La verificación contrastará cualquier conclusión con eventos y métricas. Si detecta un error, el flujo debe registrar el reporte, corregir o retirar la conclusión y volver a verificarla.

Los análisis finales tendrán una revisión antes de publicarse. La persona o mecanismo exacto de esa revisión sigue pendiente. Ningún resultado generado por agentes debe saltarse ese paso.

## **Vídeo e idiomas**

**6.** La demo usará vídeo como ejemplo de transmisión. La experiencia debe actualizarse durante su reproducción. No llamaremos tiempo real a un proceso hasta medir el retraso entre vídeo, evento y salida. La extracción automática de eventos desde vídeo se investigará y probará por separado.

**7.** La salida admitirá inglés y español. El idioma afectará mensajes en directo, explicaciones y resúmenes.

## **Investigación y aplazamientos**

**8.** Investigaremos qué métricas aportan valor, cómo se obtienen hoy y qué bibliotecas o modelos abiertos compatibles con Python pueden ayudarnos. Los primeros hallazgos están en [investigación de métricas y herramientas](09-investigacion-metricas-y-herramientas.md).

**9.** La meta numérica de latencia, el contrato con sistemas externos y el alcance de funciones opcionales siguen pendientes. Se tratarán después de estabilizar el formato, el flujo de datos y la primera demo.

## **Infraestructura Azure para datos e ingesta**

**10.** El flujo integrado de datos usará Azure Event Hubs para transportar eventos normalizados y Azure Blob Storage para conservar partidos sintéticos, vídeos autorizados y observaciones de prueba. El flujo local seguirá funcionando sin Azure mediante adaptadores intercambiables.

La infraestructura de esta parte se definirá con Bicep y se desplegará mediante Azure CLI. Los nombres, la región, el grupo de recursos y la suscripción serán configurables para que cada integrante pueda desplegar los servicios en su propia cuenta sin editar la plantilla ni compartir credenciales. El [plan detallado de datos y visión](persona-1-datos-y-vision/plan-general.md) describe el alcance inicial.

## **Estado actual**

El monorepo y los proyectos iniciales de frontend y backend están preparados. La ingesta sintética y la analítica de Persona 2 tienen módulos y pruebas propios. Existe un módulo de narrativa con un flujo CrewAI secuencial de cuatro tareas y un proveedor local de prueba. El filtro, el catálogo inicial de jugadas y el despacho reproducible están implementados de forma local. La conexión entre módulos, el canal durable, la investigación previa, la simulación contrafactual, los resúmenes de medio tiempo y la alta disponibilidad todavía están pendientes.
