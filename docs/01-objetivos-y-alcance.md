# **Objetivos y alcance**

## **Problema**

El marcador muestra el resultado, pero deja fuera el contexto del partido. El reto pide transformar eventos de fútbol sintéticos en estadísticas, momentos importantes y explicaciones que ayuden a entender lo que ocurre.

## **Objetivo principal**

Construir una solución basada en IA que reciba eventos sintéticos a medida que ocurren, mantenga el contexto del partido y produzca narraciones en directo, información apta para pantalla y un resumen automático al terminar.

La misma información debe dar lugar a experiencias diferentes según las preferencias del espectador. Un analista debe poder ver datos y contexto más detallados. Un aficionado ocasional debe recibir explicaciones breves y claras.

## **Resultado mínimo que proponemos demostrar**

**1.** Reproducimos un partido sintético como flujo de eventos con tiempo de partido y metadatos.

**2.** Calculamos un estado verificable del partido y al menos algunas estadísticas derivadas de esos eventos.

**3.** Detectamos momentos relevantes y explicamos su importancia con evidencia de los eventos que los originaron.

**4.** Emitimos una salida estructurada con tiempo, duración sugerida, contenido y referencias a eventos para mostrarla como superposición junto al partido.

**5.** Mostramos diferencias reales entre los modos de analista y aficionado casual, permitimos elegir idioma y club favorito, y seguimos a un jugador favorito durante el partido con los eventos disponibles.

**6.** Generamos un resumen final a partir de los eventos y el estado acumulado del mismo partido.

Este resultado mínimo es una propuesta de trabajo para la demo. No fija todavía una tecnología ni un número de idiomas, partidos o métricas.

## **Alcance del reto**

El flujo pedido tiene cinco etapas: ingerir, interpretar, explicar, traducir a una salida para pantalla y personalizar. La narración debe servir durante el partido y para resúmenes posteriores. El reto también menciona narración en varios idiomas e innovación en datos sintéticos.

Se sugieren capacidades como identificar jugadores, medir calidad y dificultad de pases, velocidad de balón y tiros, y generar eventos desde vídeo. El texto las presenta como características a considerar. Su inclusión y prioridad se decidirán según tiempo, datos disponibles y valor para la demo.

## **Límites conocidos**

Usaremos datos sintéticos realistas. Los organizadores no entregarán datos reales de partidos de la Premier League y el proyecto no debe redistribuirlos.

La integración con el sistema real de producción de una transmisión no está definida. Podemos demostrar el formato y la sincronización de las salidas con una simulación local hasta conocer una interfaz oficial.

No afirmaremos que una métrica viene de vídeo si fue calculada o incluida en eventos sintéticos.
