# **Análisis de requisitos**

Cada punto describe una capacidad pequeña que puede verificarse. P0 indica lo necesario para una primera demo completa. P1 amplía el valor si hay tiempo. P2 queda como opción. Estas prioridades son una propuesta inicial del equipo y no cambian el texto del reto.

## **Datos e ingesta**

**RF-01 · P0.** El sistema debe aceptar metadatos de un partido sintético con identificador, equipos, jugadores y reloj. Se verifica al iniciar una reproducción y consultar ese contexto.

**RF-02 · P0.** El sistema debe recibir eventos sintéticos de al menos pases, tiros, entradas, cambios de posesión y presión. Se verifica con un partido de ejemplo que contenga cada tipo.

**RF-03 · P0.** Cada evento debe conservar un identificador, su tipo y su tiempo de partido. Se verifica siguiendo un evento desde la entrada hasta cualquier salida que lo use.

**RF-04 · P0.** El sistema debe rechazar o marcar eventos inválidos y duplicados sin contarlos dos veces. Se verifica con entradas repetidas e incompletas.

**RF-05 · P1.** El sistema debe admitir eventos tardíos según una política documentada. Se verifica al enviar eventos fuera de orden y comparar el estado resultante con la política elegida.

**RF-06 · P1.** El conjunto sintético debe incluir escenarios creíbles de control, presión, transición y momentos decisivos. Se verifica revisando partidos de prueba y los campos que permiten calcular cada historia.

## **Interpretación del partido**

**RF-07 · P0.** El sistema debe actualizar un estado del partido a partir de los eventos aceptados. Se verifica comparando marcador, posesión y reloj con la secuencia de entrada.

**RF-08 · P0.** El sistema debe calcular estadísticas cuya fórmula y datos de entrada estén documentados. Se verifica recalculando una muestra de eventos.

**RF-09 · P0.** El sistema debe identificar al menos un patrón contextual, como presión sostenida o cambio de ritmo, con evidencia visible. Se verifica con secuencias que cumplen y que no cumplen la regla.

**RF-10 · P1.** El sistema debe calcular distancia, precisión o dificultad del pase cuando existan los datos necesarios. Se verifica con pases de ejemplo y resultados reproducibles.

**RF-11 · P1.** El sistema debe mostrar información del jugador cuando exista una identificación fiable en el evento. Se verifica siguiendo al mismo jugador durante varios eventos.

**RF-12 · P2.** El sistema puede calcular velocidad del balón, del tiro, del jugador o distancia recorrida si la fuente proporciona posiciones y tiempos adecuados. Se verifica con datos de prueba y unidades definidas.

**RF-13 · P2.** El sistema puede generar eventos o métricas desde vídeo sintético o autorizado. Solo se acepta como implementado si se prueba con una señal de vídeo entrante.

## **Momentos y explicaciones**

**RF-14 · P0.** El sistema debe seleccionar momentos que merezcan atención y limitar mensajes repetidos. Se verifica con una secuencia que contiene varios eventos parecidos.

**RF-15 · P0.** Cada explicación debe incluir el hecho, el contexto que lo vuelve relevante y los identificadores de los eventos que la sustentan. Se verifica inspeccionando una salida y sus fuentes.

**RF-16 · P0.** El sistema debe separar hechos calculados de inferencias narrativas. Se verifica revisando un caso en que los datos no permitan afirmar una causa táctica.

**RF-17 · P1.** El sistema debe permitir comparar el momento actual con un tramo anterior del mismo partido cuando esa comparación mejore la explicación. Se verifica con un cambio claro de ritmo o presión.

**RF-28 · P1.** El espectador debe poder pedir una explicación adicional de un momento mostrado. La respuesta debe usar los eventos y métricas que lo sustentan. Se verifica abriendo un momento y contrastando la respuesta con sus fuentes.

**RF-29 · P1.** El sistema debe agrupar eventos relacionados en una jugada para explicar la secuencia completa. Se verifica con una recuperación, varios pases y un tiro que aparezcan como un solo momento sin perder sus eventos de origen.

**RF-30 · P1.** El sistema debe identificar hitos de un jugador dentro del partido, como su mejor registro o un número de acciones alcanzado, cuando existan datos suficientes. Se verifica con una secuencia que alcanza el hito y otra que no lo alcanza.

**RF-31 · P1.** El sistema debe permitir comparar el control de ambos equipos entre tramos del mismo partido mediante una medida definida. Se verifica con dos tramos de dominio opuesto y con el cálculo documentado.

**RF-32 · P2.** El sistema puede mostrar un índice de caos calculado con cambios de posesión y otras transiciones disponibles. Se verifica con tramos estables y tramos de cambios frecuentes, sin presentar el índice como una estadística oficial.

**RF-33 · P1.** El sistema debe reconocer patrones tácticos concretos solo cuando los eventos tengan posición y tiempo suficientes. Se verifica con una secuencia positiva y otra negativa para cada patrón elegido.

## **Narración y pantalla**

**RF-18 · P0.** El sistema debe producir mensajes durante la reproducción de eventos sin esperar al final del partido. Se verifica observando una salida antes del último evento.

**RF-19 · P0.** Cada mensaje para pantalla debe ser legible por máquina e incluir identificador, tiempo de partido, idioma, modo, texto, prioridad, duración sugerida y eventos de origen. Se verifica leyendo la salida desde una interfaz sin extraer datos del texto libre.

**RF-20 · P0.** La interfaz debe mostrar el mensaje junto al vídeo de ejemplo y respetar su tiempo de aparición. Se verifica durante la reproducción de la demo.

**RF-21 · P0.** El sistema debe producir un resumen al finalizar el partido con momentos y cifras consistentes con el estado final. Se verifica comparándolo con el flujo de eventos.

**RF-22 · P0.** El sistema debe generar narraciones claras en español e inglés, con nombres propios y cifras consistentes. Se verifica comparando mensajes del mismo momento en ambos idiomas.

**RF-34 · P1.** El usuario debe poder hacer preguntas sobre el partido en curso y recibir respuestas basadas en el estado y los eventos disponibles. Se verifica con preguntas sobre equipo, jugador y comparación entre tramos, incluida una pregunta que los datos no permitan responder.

**RF-35 · P1.** El resumen final debe poder enfocarse en un club o jugador seleccionado sin cambiar los hechos ni las cifras del partido. Se verifica generando resúmenes del mismo partido con preferencias distintas.

**RF-37 · P0.** El sistema debe sincronizar los eventos y mensajes con el tiempo del vídeo de ejemplo durante su reproducción. Se verifica adelantando y pausando el vídeo sin mostrar mensajes de un momento distinto.

**RF-38 · P0.** El sistema debe retener los análisis finales hasta que se complete la revisión acordada. Se verifica intentando publicar un análisis sin revisión y otro aprobado.

**RF-39 · P1.** Cuando un reporte señale un posible error de análisis, el sistema debe contrastarlo con sus eventos y métricas, registrar el resultado y corregir o retirar la conclusión si corresponde. Se verifica con un reporte válido y otro que no lo sea.

## **Personalización**

**RF-23 · P0.** El sistema debe ofrecer un modo de analista y uno casual con diferencias de contenido y nivel de detalle. Se verifica comparando el mismo momento en ambos modos.

**RF-24 · P0.** El sistema debe permitir elegir un club favorito y dar prioridad a información relevante para ese club sin ocultar hechos decisivos del rival. Se verifica con ambos clubes como favoritos.

**RF-25 · P0.** El sistema debe permitir elegir un jugador favorito y seguir su participación cuando haya datos suficientes. Se verifica con un jugador que interviene y otro que no interviene en una secuencia.

**RF-26 · P0.** El sistema debe ofrecer un modo centrado en un jugador durante todo el partido y comunicar cuando no haya novedades sobre él. Se verifica durante una reproducción completa.

**RF-27 · P0.** El sistema debe aplicar la preferencia de idioma a mensajes en directo y resúmenes. Se verifica cambiando el idioma y generando ambos tipos de salida.

**RF-36 · P1.** El usuario debe poder elegir entre niveles simple, normal y avanzado de explicación para un mismo momento. Se verifica comparando longitud y detalle sin alterar los hechos.

## **Calidad y operación**

**RNF-01 · P0.** Los resultados deben poder reproducirse con el mismo partido sintético y la misma configuración. Se verifica ejecutando dos veces la misma secuencia y comparando estadísticas y momentos seleccionados.

**RNF-02 · P0.** La salida debe estar disponible durante la reproducción a un ritmo útil para la demo en directo. La meta numérica de latencia queda pendiente de medir y acordar.

**RNF-03 · P0.** El sistema debe registrar el origen de métricas y narraciones para que puedan revisarse. Se verifica rastreando una explicación hasta eventos y cálculo.

**RNF-04 · P0.** Los componentes, datos de ejemplo y pasos de ejecución deben estar documentados para que otra persona pueda repetir la demo. Se verifica siguiendo las instrucciones desde un entorno limpio.

**RNF-05 · P1.** La interfaz debe mantener los mensajes legibles y evitar que varios compitan por el mismo espacio. Se verifica durante escenas con muchos eventos.

**RNF-06 · P1.** El sistema debe manejar la falta de respuesta de la parte de IA sin detener la ingesta ni corromper el estado. Se verifica simulando un fallo en la generación de narraciones.

## **Criterio de alcance**

Una capacidad opcional solo se dará por terminada si tiene datos de entrada, cálculo o modelo, salida visible y una prueba que demuestre lo que afirma. Las métricas de velocidad y el análisis de vídeo requieren especial cuidado porque no pueden deducirse de un evento sin tiempos y posiciones adecuados.
