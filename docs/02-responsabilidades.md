# **Responsabilidades del sistema**

Este documento separa las tareas del programa. Son límites de responsabilidad, no servicios ni agentes ya elegidos.

## **Fuente de datos sintéticos**

Debe producir o cargar partidos con equipos, jugadores, reloj y eventos coherentes. Debe permitir repetir el mismo partido para comparar resultados. Debe indicar qué campos se generaron y cómo se obtuvieron las métricas.

## **Ingesta y validación**

Debe recibir los eventos en orden de llegada, comprobar su forma, detectar duplicados y tratar eventos incompletos o tardíos sin ocultarlos. Debe conservar el identificador y el tiempo de cada evento para poder rastrear cualquier salida.

## **Estado e interpretación**

Debe mantener el marcador, el reloj, la posesión y las estadísticas que puedan calcularse con los datos disponibles. Debe distinguir hechos observados, métricas calculadas e interpretaciones. Un patrón como presión alta o cambio de ritmo necesita una regla o evidencia explícita.

## **Filtro y preparación para agentes**

Debe actualizar las métricas de todos los eventos aceptados y separar los que necesitan análisis narrativo. Los eventos de solo métricas no deben llamar a los agentes. Los candidatos deben compararse con reglas y jugadas conocidas, reducirse al contexto necesario y conservar sus fuentes antes de llegar al orquestador.

## **Selección de momentos y explicación**

Debe decidir cuándo vale la pena mostrar una idea. Debe explicar por qué importa según el contexto del partido, por ejemplo una secuencia que cambia la presión o un tiro tras varias recuperaciones. Debe vincular cada explicación con los eventos y métricas que la sostienen y evitar afirmaciones sin respaldo.

## **Narración y personalización**

Debe convertir la idea en mensajes claros para distintos modos, idiomas y preferencias. El modo de analista debe aportar cifras y contexto. El modo casual debe expresar la idea con palabras más simples. Las preferencias por club o jugador deben cambiar la selección o el enfoque del contenido, no solo el color de la interfaz.

## **Salida para pantalla**

Debe entregar mensajes estructurados y sincronizables para que una interfaz los pueda mostrar junto al partido. Debe permitir controlar cuándo aparecen, cuánto tiempo se sugieren en pantalla y cuándo se reemplazan. La interfaz debe representar el contenido de forma legible.

## **Resúmenes del partido**

Debe producir un resumen de medio tiempo con las métricas y momentos disponibles hasta ese punto. Después del encuentro debe reunir el estado final y crear un resumen más amplio. Ambos usan datos acumulados, incluidos los eventos que no necesitaron una narración en directo.

## **Observación y control editorial**

Debe permitir revisar la salida, sus fuentes y los errores de procesamiento durante la demo. Los análisis finales deben pasar por la revisión acordada antes de publicarse. El responsable y la interfaz de esa revisión quedan pendientes.

## **Responsabilidad humana del equipo**

El equipo debe acordar las prioridades, revisar el realismo de los datos sintéticos, probar las explicaciones y preparar una demo que muestre entradas, transformación, salida y valor para cada tipo de usuario. No se asignan personas concretas porque aún no se conoce la composición del equipo.
