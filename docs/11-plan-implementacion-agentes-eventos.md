# **Plan de implementación de agentes por eventos**

Este plan convierte la arquitectura acordada en entregas pequeñas y comprobables. Todavía es una propuesta de implementación. Comenzamos con eventos sintéticos y un proveedor local para medir el flujo antes de conectar modelos externos.

## **Avance actual**

Implementamos la base local de las fases 1 y 2. Incluye seis escenarios sintéticos, filtro sin estado local, cambios de métricas, control de duplicados conocidos, dos patrones iniciales, refinamiento y despacho reproducible. La API permite probar este recorrido. El canal durable, el acumulador persistente y GPT-4.1 mini en el orquestador siguen pendientes.

## **Objetivo de la primera entrega**

Procesar una secuencia sintética durante el partido, actualizar todas las métricas, enviar solo los momentos relevantes a los agentes y producir una salida verificada sin detener el procesamiento cuando un agente falle.

La primera demostración debe incluir un evento de solo métricas, una secuencia candidata, una situación de peligro, un tiempo muerto, un resumen de medio tiempo y un resumen final pendiente de aprobación.

## **Contratos nuevos propuestos**

**1. `RoutingDecision v1`.** Resultado del filtro con ruta, prioridad, motivos, referencias y versión de reglas.

**2. `PlayContext v1`.** Coincidencia con el catálogo de jugadas, señales presentes, señales faltantes y límites.

**3. `AgentRequest v1`.** Contexto reducido para una tarea, preferencias, vencimiento y enlaces de evidencia.

**4. `AgentDispatch v1`.** Destino, prioridad, correlación, clave idempotente y tiempo máximo.

**5. `CounterfactualScenario v1`.** Escenario simulado, cambio supuesto, resultado posible, evidencia usada, método y aviso de simulación.

**6. `PregameFact v1`.** Dato externo con fuente, fecha del hecho, fecha de consulta, vigencia, derechos de uso y aprobación.

**7. `RecapRequest v1`.** Tipo `halftime` o `final`, duración objetivo, estado acumulado, momentos y métricas disponibles.

Los contratos deben tener ejemplos válidos, mínimos e inválidos antes de conectar servicios.

## **Fase 1. Simulador y medición base**

Creamos un reproductor de solicitudes sintéticas con los casos de `tests/fixtures/agent-routing-scenarios.json`. Debe controlar el reloj del partido, la velocidad de reproducción y el orden de los eventos.

Medimos eventos recibidos, eventos por ruta, tamaño de contexto, tiempo del filtro, tiempo total de la narración y solicitudes descartadas. Esta fase no necesita CrewAI ni Azure.

La fase termina cuando la misma entrada produce las mismas decisiones en dos ejecuciones y ningún duplicado modifica dos veces las métricas.

## **Fase 2. Estado, filtro y catálogo**

Implementamos el estado acumulado y el servicio filtro como código de dominio. Las reglas iniciales cubren tiro, gol, recuperación cerca del área, secuencia de progresión, falta o pausa y eventos normales de posesión.

Creamos un catálogo pequeño de jugadas versionadas. Cada regla requiere datos mínimos, caso positivo, caso negativo y explicación permitida. Una coincidencia incompleta debe registrar qué señal falta.

La fase termina cuando los eventos de solo métricas no llegan al orquestador y los candidatos conservan todos sus identificadores de origen.

## **Fase 3. Canal de eventos y orquestador**

Introducimos un canal durable con contratos independientes del proveedor. Proponemos estos canales lógicos:

- `match.events.accepted`
- `match.metrics.updated`
- `match.moments.candidate`
- `match.danger.detected`
- `match.dead_ball.detected`
- `agents.requests`
- `narratives.proposed`
- `narratives.verified`
- `recaps.requested`
- `processing.dead_letter`

La clave de partición es `match_id`. Cada mensaje lleva `message_id`, `correlation_id`, versión, hora de creación y vencimiento. Los consumidores deben ser idempotentes.

El orquestador usa GPT-4.1 mini para clasificar solicitudes refinadas. Las rutas evidentes, los límites y la recuperación usan reglas para evitar una llamada innecesaria. Registramos la ruta propuesta, la elegida, el motivo y el tiempo de decisión.

Antes de implementar los tiempos muertos debemos resolver una brecha del contrato. `MatchEvent 1.0` no incluye faltas ni estado de juego detenido. Debemos añadir un evento versionado o una señal de control procedente del reloj y del reproductor.

## **Fase 4. Agentes durante el partido**

Adaptamos el módulo actual para consumir `AgentRequest v1`. Implementamos primero peligro, selección de momentos, narración y preguntas. Los agentes independientes pueden ejecutarse en paralelo. La validación sigue siendo una barrera obligatoria antes de publicar.

GPT-4.1 mini se usa en selección de momentos y validación semántica rápida. GPT-4.1 se usa en peligro, narración y preguntas que necesitan relacionar varias evidencias. Las preguntas directas pueden usar GPT-4.1 mini. La decisión se toma por tipo de tarea y no por un único modelo global.

El selector trabaja con ventanas configurables. La ventana inicial de dos minutos es una propuesta para candidatos no urgentes. Debe cerrarse antes durante una pausa y omitirse para goles o peligro con prioridad alta.

La simulación de peligro empieza con escenarios basados en reglas sobre datos sintéticos. Por ejemplo, completar un pase, elegir un receptor alternativo o continuar un avance. La salida siempre separa el hecho observado del escenario posible. No se asigna una probabilidad hasta contar con un modelo calibrado y datos adecuados.

## **Fase 5. Base previa al partido**

Creamos un flujo separado para investigación. El researcher propone datos y el validador revisa fuentes, fechas y conflictos. Una persona aprueba el contenido que podrá usar la transmisión.

El researcher y el validador de fuentes usan GPT-4.1 con una herramienta de búsqueda web. Los embeddings solo se incorporan si necesitamos recuperar por significado información ya guardada y aprobada.

La base debe permitir fecha de vencimiento y retirada. Las promociones y próximos eventos del canal se cargan como contenido editorial aprobado, no como datos descubiertos libremente por el modelo.

El narrador consulta una vista pequeña según el momento. En tiempo muerto puede recibir datos del estadio o de un jugador. Durante una situación activa recibe primero la evidencia del partido.

## **Fase 6. Resúmenes**

El acumulador guarda métricas y candidatos descartados de la narración en directo. En el medio tiempo publica una solicitud con objetivo editorial de tres a cuatro minutos. El resumen final usa el estado cerrado, las métricas completas y los momentos verificados.

Probamos la duración con lectura o voz real. El sistema ajusta la cantidad de contenido usando palabras y tiempo medido. El resumen final queda pendiente hasta la aprobación editorial.

## **Fase 7. Alta disponibilidad y carga**

Ejecutamos el filtro, refinador, orquestador y trabajadores de agentes como procesos sin estado con al menos dos instancias en el entorno de demostración de disponibilidad. El canal, el estado y la base previa usan almacenamiento durable con respaldo y comprobación de salud.

La recuperación sigue estas reglas:

**1.** Una caída de IA no detiene eventos ni métricas.

**2.** Una entrega repetida no duplica cálculos ni narraciones.

**3.** Una solicitud vencida no aparece tarde en pantalla.

**4.** Los reintentos son limitados y luego pasan a la cola de errores.

**5.** El estado se puede reconstruir desde el registro de eventos del partido.

**6.** El escalado usa profundidad de cola, edad del mensaje, eventos por segundo y tiempo de respuesta.

Las metas numéricas se fijan después de la medición base. Antes de elegir tecnología probamos al menos el volumen esperado, un pico mayor y la pérdida de una instancia. La elección entre un canal administrado, Redis Streams, RabbitMQ o Kafka queda pendiente de esas pruebas y del entorno de despliegue.

## **Pruebas necesarias**

**1. Filtro.** Un pase normal actualiza métricas sin llamar IA. Un tiro peligroso crea una ruta prioritaria.

**2. Ventanas.** Varios eventos relacionados forman un solo momento y los urgentes no esperan.

**3. Catálogo.** Una triangulación completa coincide y una secuencia incompleta no se afirma como patrón confirmado.

**4. Simulación.** El escenario se marca como contrafactual y nunca modifica el estado real.

**5. Contexto previo.** El narrador solo usa datos aprobados y vigentes.

**6. Resumen.** Los datos no narrados en directo aparecen cuando son relevantes para el medio tiempo o el final.

**7. Fallos.** Con el modelo caído, el estado y las métricas continúan.

**8. Carga.** Varias instancias procesan partidos en paralelo sin perder el orden dentro de cada partido.

## **Orden recomendado de trabajo**

Primero implementamos simulador, estado, filtro y catálogo. Después añadimos el canal y el orquestador. Luego adaptamos los agentes y el validador. La base previa y los resúmenes pueden avanzar contra contratos de prueba. Cerramos con integración, carga, fallos y medición de latencia.

La configuración inicial y las reglas para evaluar cambios de modelo están en [política de modelos de IA](12-politica-modelos-ia.md).

No se considera terminado hasta mostrar el recorrido en ejecución y distinguir lo probado localmente de lo pendiente en un servicio externo o una transmisión real.
