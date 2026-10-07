# **Casos de uso de la plataforma de inteligencia de partidos**

Este documento describe quién usa la información del partido y qué hace con ella. Los objetivos generales, las responsabilidades del sistema y las reglas de evaluación están en los otros documentos de `docs`. Los casos son propuestas de experiencia. Sus referencias indican los requisitos que ya los cubren o que añadimos al análisis.

## **Usuarios**

**1. Aficionado casual.** Quiere entender los cambios del partido sin tener que interpretar muchas cifras.

**2. Aficionado de un club.** Quiere seguir cómo juega su equipo y recibir avisos relevantes para él.

**3. Aficionado de un jugador.** Quiere seguir al mismo jugador durante todo el encuentro, incluso cuando el juego se desarrolla lejos de él.

**4. Analista.** Quiere comparar tramos, consultar métricas y revisar la evidencia de una lectura táctica.

**5. Comentarista o equipo de estudio.** Quiere encontrar historias y momentos que pueda explicar al público durante y después del partido.

**6. Plataforma de transmisión.** Quiere recibir mensajes con tiempo y estructura definidos para mostrarlos junto a la transmisión.

Una persona puede combinar preferencias. Por ejemplo, puede ser aficionada de un club, seguir a un jugador y elegir el nivel avanzado de explicación.

## **Casos durante el partido**

### **CU01. Consultar el estado actual**

Un espectador abre el partido mientras se reproduce una secuencia de eventos sintéticos. Ve el marcador, el tiempo y las estadísticas disponibles en ese instante. Los datos cambian cuando llegan nuevos eventos. Este caso sirve de base a los demás y está cubierto por RF-01, RF-02, RF-07 y RF-08.

### **CU02. Reconocer una jugada completa**

Después de una recuperación, varios pases y un tiro, el sistema agrupa los eventos en una sola secuencia ofensiva. El espectador ve el inicio, la duración, los participantes y el resultado de la jugada cuando esos datos están disponibles. Puede revisar los eventos que la componen. Este comportamiento concreta la detección de momentos de RF-14 y añade RF-29.

### **CU03. Pedir una explicación de un momento**

Un espectador ve el aviso de que aumentó la presión de un equipo y selecciona la opción para saber por qué importa. La respuesta muestra el tramo observado y hechos como recuperaciones en campo rival o pérdidas del contrario. Si esos hechos no bastan para explicar una causa táctica, el sistema lo indica. Este caso añade la interacción de RF-28 a la explicación de RF-15 y RF-16.

### **CU04. Cambiar el nivel de explicación**

Un aficionado casual recibe una frase breve sobre una jugada. Puede pedir una explicación normal o avanzada del mismo momento. Las tres versiones mantienen los mismos hechos y cambian la cantidad de datos y el vocabulario. Este caso amplía los modos de RF-23 con RF-36.

### **CU05. Revisar tendencias como analista**

Un analista abre un tramo del partido y consulta cifras, patrones y eventos de origen. Puede comparar la presión, las progresiones o las zonas de ataque con otro tramo cuando existan posiciones y tiempos suficientes. El sistema presenta la interpretación como tal y permite comprobarla. Este caso se relaciona con RF-08, RF-09, RF-17 y RF-33.

### **CU06. Seguir un club favorito**

Un aficionado elige el Equipo A. Los avisos dan prioridad a su ataque, defensa y jugadores, pero siguen mostrando goles o momentos decisivos del Equipo B. La preferencia cambia el contenido que recibe, no solo su aspecto. Este caso está cubierto por RF-24.

### **CU07. Seguir a un jugador**

Un aficionado elige al Jugador 7 y activa el modo centrado en él. Ve sus acciones, su evolución durante el partido y los momentos en los que participa. Cuando no hay nuevos eventos del jugador, la vista conserva el último estado y comunica que no hay novedades. Solo muestra velocidad o distancia si la fuente permite calcularlas. Este caso está cubierto por RF-11, RF-12, RF-25 y RF-26.

### **CU08. Descubrir un hito individual**

El Jugador 7 alcanza su décimo pase progresivo o supera su mejor registro del partido. El sistema comprueba el hito con sus eventos y muestra el aviso una sola vez. Una comparación con otros jugadores se limita al mismo encuentro y a los datos disponibles. Este caso añade RF-30.

### **CU09. Ver un cambio de control**

Un analista o aficionado compara dos tramos del encuentro. Un indicador muestra qué equipo tuvo más iniciativa según una fórmula definida y señala cuándo cambió la tendencia. La explicación muestra los factores que movieron el indicador. Es una medida propuesta por el proyecto, no un resultado oficial. Este caso añade RF-31.

### **CU10. Ver una fase de caos**

En pocos minutos ocurren varias pérdidas de balón, transiciones y tiros. El sistema puede señalar que el partido atraviesa una fase de cambios frecuentes y mostrar qué eventos influyeron en un índice de caos. El índice necesita una fórmula y umbrales propios antes de mostrarse. Este caso añade la opción RF-32.

### **CU11. Explorar un patrón táctico**

Un analista consulta si un equipo presiona alto, ataca más por un sector o genera oportunidades poco después de recuperar el balón. El sistema muestra el tramo, las acciones que cumplen la regla y una comparación útil. Solo afirma un patrón cuando los eventos incluyen posiciones y tiempos suficientes. Este caso concreta RF-09 y RF-33.

### **CU12. Preguntarle al partido**

Un espectador pregunta qué cambió después del descanso o cómo participa su jugador favorito. El asistente consulta el estado y los eventos del partido, responde con cifras verificables y señala sus fuentes. Si la pregunta exige datos ausentes, responde que no puede determinarlo. Esta experiencia conversacional añade RF-34.

### **CU13. Recibir una narración breve**

Un comentarista recibe una narración durante una secuencia importante, por ejemplo una recuperación que termina en gol. El mensaje explica la relación temporal entre las acciones sin inventar una causa, como una desorganización defensiva, si los eventos no la muestran. Puede usarlo como apoyo para su relato. Este caso está cubierto por RF-14 a RF-19.

## **Casos al terminar el partido**

### **CU14. Generar un resumen del encuentro**

Al finalizar la reproducción, un comentarista obtiene una historia ordenada por tramos y momentos clave. El resultado incluye el marcador final y cifras que coinciden con el estado acumulado. Puede abrir las fuentes de cada afirmación importante. Este caso está cubierto por RF-21 y RNF-03.

### **CU15. Recibir un resumen personalizado**

Dos espectadores solicitan el resumen del mismo partido. Uno recibe una versión breve centrada en su club. El otro recibe una versión más detallada centrada en un jugador. Cambian el enfoque y el detalle, pero no el marcador ni los hechos. Este caso añade RF-35.

## **Casos de entrega y presentación**

### **CU16. Elegir idioma**

Un espectador cambia el idioma de la narración en directo y del resumen. Los nombres, tiempos y cifras siguen siendo iguales. El nivel de explicación y las preferencias de club o jugador continúan aplicándose. Este caso está cubierto por RF-22 y RF-27.

### **CU17. Mostrar información en una transmisión**

Una plataforma de transmisión recibe un mensaje estructurado cuando ocurre un momento relevante. Usa su tiempo de partido, prioridad y duración sugerida para mostrarlo junto a la imagen. También puede consultar los eventos de origen. El contrato exacto con un sistema profesional sigue pendiente; la demo puede comprobar este recorrido con una transmisión simulada. Este caso está cubierto por RF-19 y RF-20.

Las capacidades nuevas están registradas como RF-28 a RF-36 en [el análisis de requisitos](03-requisitos.md). El asistente conversacional y los indicadores propios siguen siendo propuestas cuya prioridad y fórmula debemos cerrar antes de incluirlos en la demo.
