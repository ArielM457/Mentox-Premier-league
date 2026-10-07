# **Persona 5: diseño UX/UI**

## **Objetivo**

Diseñar una experiencia clara para aficionados, analistas, comentaristas y la persona que revisa contenido antes de publicarlo. Esta persona entrega decisiones de interacción y diseños editables para que Persona 4 los implemente. El diseño debe funcionar con datos reales del producto y estados incompletos, no solo con una pantalla ideal.

## **Módulos de diseño a cargo**

**1. Recorridos de usuario.** Dibujar el recorrido del aficionado casual, del analista, del seguidor de club, del seguidor de jugador, del comentarista y de quien revisa el análisis final. Definir qué cambia al elegir idioma, modo o preferencia durante un partido.

**2. Experiencia durante el vídeo.** Diseñar la posición de marcador, reloj, controles y superposiciones sin tapar acciones importantes. Definir jerarquía entre gol, momento táctico, hito de jugador y aviso de baja prioridad. Incluir el estado en que llegan varios mensajes a la vez.

**3. Explicación y evidencia.** Diseñar cómo abrir la razón de un momento y cómo ver las cifras y eventos que la respaldan. Crear niveles simple, normal y avanzado. Mostrar de forma clara cuándo el sistema no tiene datos suficientes para una conclusión.

**4. Personalización.** Diseñar selección de español o inglés, club favorito, jugador favorito y modo centrado en el jugador. Mostrar la diferencia entre vista casual y analista sin perder continuidad al cambiar de modo.

**5. Preguntas y resúmenes.** Diseñar la consulta al partido, respuestas con fuentes, resumen general y variantes por club o jugador. Incluir resultados sin respuesta, carga lenta y errores.

**6. Revisión y corrección.** Diseñar la vista para aprobar o rechazar un análisis final, revisar evidencia y registrar un motivo. Diseñar el recorrido para reportar un error, ver el resultado de la verificación y distinguir contenido corregido o retirado.

**7. Sistema visual.** Entregar componentes, tipografía, colores, espaciados, iconos y reglas de movimiento. Preparar versiones para pantalla ancha y móvil. Definir estados de foco, contraste y lectura sin depender solo del color. Las superposiciones deben poder leerse en fondos de vídeo claros y oscuros.

## **Entregables**

**1.** Mapa de recorridos y estructura de navegación.

**2.** Bocetos y diseños editables de las pantallas y superposiciones principales.

**3.** Biblioteca de componentes y estados con medidas y comportamiento para implementación.

**4.** Textos de interfaz en español e inglés, con criterios para términos de fútbol, cifras y unidades.

**5.** Prototipo navegable para probar tareas reales y lista de ajustes tras revisarlo con el equipo.

## **Trabajo independiente**

Puede empezar con los casos de uso y datos de ejemplo de este plan. No necesita esperar a Roboflow, SoccerNet ni CrewAI. Comparte primero recorridos y componentes base con Persona 4; entrega las pantallas avanzadas por partes para que el desarrollo continúe.

El diseño no decide cifras ni reglas tácticas. Si una pantalla necesita un dato que los contratos no incluyen, lo señala en el documento compartido antes de convertirlo en requisito nuevo.

## **Comprobación de entrega**

Otra persona debe poder completar en el prototipo estas tareas: seguir un club, activar el seguimiento de un jugador, entender por qué apareció una superposición, cambiar de idioma, consultar el resumen y aprobar o rechazar un análisis. Persona 4 debe poder construir cada pantalla a partir de los diseños y estados entregados, sin adivinar el comportamiento.

Sus casos principales son CU03 a CU07, CU12 y CU14 a CU17. Apoya la experiencia de todos los requisitos visibles.
