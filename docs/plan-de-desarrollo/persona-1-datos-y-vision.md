# **Persona 1: datos sintéticos y visión**

El [plan detallado de esta parte](../persona-1-datos-y-vision/README.md) contiene las fases, los requisitos funcionales, las historias de usuario y la integración reproducible con Azure.

## **Objetivo**

Entregar un flujo de eventos con procedencia clara. El mismo contrato debe servir para partidos sintéticos generados por el equipo y para eventos inferidos desde vídeo. Esta persona es dueña de la entrada de datos; no calcula narraciones ni decide qué momento mostrar.

## **Módulos a cargo**

**1. Generador y catálogo sintético.** Crear partidos con metadatos, equipos, jugadores y secuencias realistas de pases, tiros, entradas, presión y cambios de posesión. Preparar al menos un partido corto repetible que muestre control, transición y un momento decisivo. Si se adapta un conjunto externo, documentar origen, licencia y transformación. No incorporar datos reales de partidos de la Premier League a la entrega.

**2. Ingesta y normalización.** Convertir cada fuente a `MatchEvent v1`, validar campos, evitar duplicados y registrar eventos tardíos o incompletos. Mantener `event_id`, `match_id`, reloj de partido, tiempo de vídeo y procedencia. Las reglas de orden y rechazo deben poder probarse con eventos fuera de orden.

**3. Percepción espacial.** Probar Roboflow Sports sobre un vídeo permitido para detectar jugadores, balón y posiciones. Evaluar seguimiento, clasificación por equipo y transformación de coordenadas al campo. Un identificador de seguimiento no se presenta como identidad real del jugador sin una asociación comprobada.

**4. Detección de acciones.** Probar los métodos de SoccerNet para localizar acciones y tiempos. Verificar clases disponibles, acceso a pesos, permisos del vídeo, calidad con nuestro clip y retraso de procesamiento. Registrar los falsos positivos y las acciones que el método no detecta.

**5. Fusión de eventos.** Combinar una acción detectada con posiciones cercanas en el tiempo solo cuando exista evidencia suficiente. Evitar duplicar el mismo tiro o pase si aparece en varias fuentes. Emitir el evento normalizado con fuente y confianza; conservar las observaciones originales para revisión.

## **Entregables**

**1.** Generador, ejemplos y reproducción de eventos sintéticos con resultado estable.

**2.** Adaptador de entrada que entregue `MatchEvent v1` y reporte errores de validación.

**3.** Informe de Roboflow Sports y SoccerNet con vídeo usado, permisos, precisión observada, tiempo por tramo y decisión de integración.

**4.** Adaptador de vídeo y fusión cuando las pruebas justifiquen su uso. Si una capacidad falla, registrar el límite y mantener operativo el flujo sintético.

**5.** Documentación del formato, mapeo de clases externas y límites de identificación de jugadores.

## **Trabajo independiente**

Puede empezar con un partido generado localmente y con observaciones de vídeo guardadas como ejemplos. Persona 2 consume eventos de muestra y no espera al detector. Persona 4 usa el mismo reloj de vídeo para construir el reproductor, aunque la detección automática todavía no esté lista.

Los archivos principales estarán en adaptadores de fuentes y generadores bajo `apps/backend`, más ejemplos sintéticos en una carpeta de datos del repositorio. Los cambios al contrato compartido se acuerdan antes de cambiarlo.

## **Comprobación de entrega**

Repetir el partido sintético debe producir la misma secuencia y los mismos identificadores. Los eventos inválidos o duplicados no deben pasar como válidos. Para vídeo, se compara una muestra anotada manualmente con lo detectado y se mide el retraso en el equipo de la demo. Se informa por separado la calidad de acciones, posiciones y asociación de jugadores.

Requisitos principales: RF-01 a RF-06 y RF-13. Apoya RF-03, RF-12 y RF-37 al entregar tiempos y posiciones fiables.
