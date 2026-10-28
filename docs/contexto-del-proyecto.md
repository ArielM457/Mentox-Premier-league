# Contexto del proyecto

## Producto y problema

**The Prime Moment** convierte eventos de fútbol en una experiencia explicable: muestra qué acaba de pasar, por qué merece atención y qué datos sostienen la explicación. Está pensado para espectadores casuales, analistas y personas que siguen a un club o jugador, dentro de una demostración de transmisión o streaming.

El reto original organiza el flujo en cinco etapas: recibir datos, interpretar el partido, producir explicaciones, presentar mensajes temporizados y adaptar la experiencia. También pide un resumen consistente con el partido. La implementación trabaja principalmente con partidos sintéticos para poder repetir las pruebas sin redistribuir datos reales de la Premier League.

## Experiencia disponible

El frontend ofrece inicio, configuración inicial, descubrimiento de partidos, listado, previa táctica, centro del partido, detalle de momentos, resumen, preferencias y revisión editorial con comunidad. La navegación utiliza rutas hash; las preferencias se guardan en el navegador.

El centro del partido combina reloj de reproducción, campo con jugadores y balón, momentos, estadísticas, vista táctica, preguntas, narración y una integración de observaciones de visión. Los modos disponibles son casual, analista, analista profesional y jugador. El catálogo de idiomas incluye español, inglés, alemán, chino, hindi, francés y portugués; la presencia de una traducción no sustituye una revisión lingüística de calidad.

El backend crea sesiones a partir de los escenarios `acceptance`, `analytics` y `live`, calcula o adapta estadísticas, selecciona candidatos y produce salidas estructuradas. Permite usar un motor analítico provisional o el motor de Persona 2. La narrativa puede ser provisional, fixture o Azure/CrewAI. El modo local predeterminado usa plantillas y memoria.

## Componentes y responsabilidades

| Área | Responsabilidad | Ubicación |
|---|---|---|
| Datos y visión, antes Persona 1 | Contratos, validación, deduplicación, orden, reproducción, observaciones y adaptadores de modelos | `apps/backend/src/match_intelligence/domain/`, `application/`, `experiments/`, `deploy/` |
| Estado y analítica, antes Persona 2 | Estado, estadísticas, patrones, atención, seguimiento y modelos de valor | `domain/analytics/`, `application/analytics/` dentro del backend |
| Agentes y narrativa, antes Persona 3 | Selección de evidencia, interpretación, respuestas y validación de narraciones | `application/narrative/`, `adapters/agents/` |
| API y experiencia, antes Persona 4 | Sesiones, rutas, canales en directo, reproducción, preferencias y editorial | `adapters/http/`, `application/match_session.py`, `apps/frontend/` |
| Diseño, antes Persona 5 | Marca, estilos, navegación, accesibilidad y adaptación a tamaños de pantalla | `apps/frontend/src/components/`, `screens/`, `styles/` |
| Operación | Persistencia, imágenes, infraestructura y procesos de integración | `supabase/`, `infra/`, Dockerfiles y scripts del backend |

Las rutas abreviadas de backend de esta tabla son relativas a `apps/backend/src/match_intelligence/`.

## Alcance comprobable y límites

El núcleo sintético puede ejecutarse sin cuentas externas. Azure Event Hubs, Blob Storage, Service Bus, Supabase y los modelos remotos tienen adaptadores o infraestructura en el repositorio; su existencia no demuestra que un servicio esté activo o correctamente configurado hoy.

El despacho de agentes utiliza un gateway determinista por defecto. El worker de eventos importantes puede confirmar despachos; eso no equivale a ejecutar todos los agentes narrativos. La previa táctica y las comparaciones «qué pasaría si» tienen implementaciones reproducibles; no deben presentarse como predicciones reales de un modelo.

Las observaciones de visión y los candidatos de fusión se mantienen separados de los eventos deportivos confirmados. Identificar un objeto o un `track_id` no prueba el nombre de un jugador. La investigación previa con búsqueda web, la aprobación de fuentes externas, la generación completa de eventos desde cualquier vídeo y la alta disponibilidad necesitan validación o desarrollo adicional.

## Fechas y fuentes

El [plan de octubre](plan-octubre.md) termina el día 27. El ajuste de preferencias solicitado el día 28 —cuatro tarjetas cuadradas, imágenes de club/jugador y eliminación de la barra de resumen— pertenece al estado actual, fuera de ese intervalo. La organización documental también se realizó el día 28.

Esta consolidación se basa en los archivos del repositorio, su historial y las comprobaciones de [validación](desarrollo/validacion.md). Las cifras históricas de avance y los despliegues registrados en documentos antiguos no se reutilizan como resultados actuales.
