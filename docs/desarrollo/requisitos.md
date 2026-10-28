# Requisitos y criterios de aceptación

Este catálogo conserva los identificadores RF y RNF y los criterios de la documentación anterior. Es una base de especificación heredada: su presencia no significa que el código ya cumpla cada punto. Las prioridades P0, P1 y P2 mantienen su significado histórico de esencial, siguiente y opcional.

Para saber qué está implementado, consultar las [especificaciones por módulo](README.md) y la [validación actual](validacion.md). Los cambios de interfaz del 28 de octubre se registran en la especificación de experiencia; no se atribuyen al plan cerrado el día 27. Las propuestas de investigación web, narración avanzada y operación de alta disponibilidad requieren trabajo adicional.

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

**RF-40 · P0.** El sistema debe clasificar cada evento aceptado antes de llamar a un agente. Debe separar al menos eventos de solo métricas, candidatos narrativos, peligro inmediato, tiempo muerto y acumulación para resumen. Se verifica reproduciendo los escenarios sintéticos y comprobando su ruta.

**RF-41 · P0.** Los eventos sin valor narrativo inmediato deben actualizar el estado y el acumulado sin llegar al orquestador de agentes. Se verifica contando las llamadas al orquestador durante una secuencia de pases normales.

**RF-42 · P0.** El sistema debe preparar para cada agente un contexto reducido con hechos, métricas, patrones, preferencias y referencias necesarias para su tarea. Se verifica comparando el contexto preparado con el registro completo del partido y comprobando que conserva la evidencia usada.

**RF-43 · P1.** El sistema debe reconocer jugadas mediante un catálogo versionado de señales y datos mínimos. Debe indicar cuándo una coincidencia es incompleta. Se verifica con un caso positivo y uno incompleto de cada patrón elegido.

**RF-44 · P1.** Ante una situación de peligro, el sistema puede producir escenarios contrafactuales sobre cambios concretos de la jugada. Cada escenario debe mostrar el supuesto, el método y una marca visible de simulación. Se verifica comprobando que no modifica el estado real ni se presenta como hecho o predicción.

**RF-45 · P1.** El sistema debe seleccionar momentos durante el partido mediante ventanas configurables y permitir una salida anticipada en goles, peligro alto o pausas adecuadas. Se verifica con un candidato que espera contexto y una alerta que se publica sin esperar la ventana.

**RF-46 · P1.** El sistema debe mantener una base previa al partido con datos externos, fuente, fecha, vigencia y estado de aprobación. El narrador solo puede usar contenido aprobado. Se verifica intentando narrar un dato aprobado y otro pendiente.

**RF-47 · P1.** El sistema debe generar un resumen de medio tiempo con una duración editorial objetivo de tres a cuatro minutos y un resumen final más amplio. Ambos deben usar el acumulado y los momentos verificados. Se verifica midiendo una lectura o voz de prueba y contrastando sus cifras con el estado.

**RF-48 · P1.** El sistema debe separar la investigación previa, la validación de fuentes y la confirmación humana. Se verifica siguiendo un dato desde su propuesta hasta su aprobación o rechazo.

**RF-49 · P0.** La captura de visión debe poder registrar una observación por segundo con tiempo de partido, tiempo de vídeo, fotograma, clase o evento, confianza y procedencia. Las observaciones de acción y seguimiento deben conservar contratos separados hasta su fusión. Se verifica validando registros completos y rechazando valores fuera de rango.

**RF-50 · P1.** Las observaciones espaciales deben conservar caja limitadora, `track_id`, equipo estimado, color de camiseta, posición de campo, identidad opcional y retraso de procesamiento. La confianza del detector no debe confirmar por sí sola la identidad nominal. Se verifica con un seguimiento identificado y otro sin evidencia de identidad.

**RF-51 · P0.** El flujo debe separar tres rutas lógicas: ingreso de todos los eventos, métricas tolerantes a pérdida y eventos importantes durables. Una pérdida de telemetría no debe descartar una jugada importante. Se verifica simulando fallos independientes de cada consumidor.

**RF-52 · P0.** La interfaz debe permitir iniciar una simulación sintética y mostrar las seis decisiones del filtro: solo métricas, candidato narrativo, peligro inmediato, tiempo muerto, resumen e inválido o duplicado. Se verifica desde el centro del partido sin cargar datos reales.

**RF-53 · P1.** El sistema debe proponer límites temporales para recortes destacados, conservar sus eventos de origen y exigir confirmación o rechazo humano antes de publicarlos. Se verifica revisando un recorte pendiente.

**RF-54 · P1.** El perfil profesional analista debe poder habilitar comentarios en vivo y consultar decisiones de ruta, agentes llamados, mensajes generados y recortes pendientes. Se verifica comparando el perfil analista con el perfil casual.

**RF-55 · P1.** “Mi experiencia” debe conservar en el navegador el historial de partidos y resúmenes abiertos, además de mostrar contenido disponible del jugador seguido. Se verifica cerrando y abriendo la interfaz sin perder el historial local.

**RF-56 · P0.** El centro del partido debe mantener una única sesión de reproducción al cambiar entre Partido, Resumen, Estadísticas y Vista táctica. Debe permitir iniciar, pausar, continuar y reiniciar sin perder el tiempo actual al cambiar de pestaña. Se verifica iniciando la demo, recorriendo todas las vistas y comprobando que el reloj no se reinicia.

**RF-57 · P1.** El campo debe mostrar todos los jugadores registrados y permitir enfocar uno sin ocultar a los demás. La posición observada más reciente tiene prioridad; cuando no exista, la interfaz debe distinguir una posición sintética de demostración. Se verifica seleccionando jugadores con y sin eventos posicionales.

**RF-58 · P1.** La vista Partido debe mostrar un selector de un solo momento y abrir el momento elegido en Resumen. Se verifica avanzando y retrocediendo por los momentos ya ocurridos.

**RF-59 · P1.** La vista Resumen debe reunir el análisis del momento seleccionado y la lista de explicaciones importantes. El análisis debe permitir comparar cambios concretos de una jugada conforme a RF-44. Mientras no exista un agente contrafactual integrado, cualquier estimación local debe identificarse de forma visible y no presentarse como un hecho ni como salida de IA. Se verifica cambiando cada supuesto y comprobando que no modifica el estado real.

**RF-60 · P1.** Las estadísticas deben actualizarse cuando el reloj cruce nuevos eventos y representar visualmente qué equipo tiene mayor valor, sin convertir datos ausentes en cero. Se verifica pausando antes y después de eventos que cambien el estado.

**RF-61 · P1.** La vista táctica debe mostrar ambos equipos inicialmente, permitir enfocar uno y nombrar patrones solo cuando los eventos ocurridos aporten evidencia suficiente. Se verifica con la selección de ambos equipos y de cada equipo individual.

**RF-62 · P1.** Resumen debe listar situaciones de gol o alta prioridad con una vista previa y acceso al análisis breve. Partido debe ofrecer una palanca para mostrar u ocultar comentarios sincronizados debajo del campo, sin crear una pestaña separada ni reiniciar la reproducción. Durante intervalos sin narración solo puede usar contenido contextual respaldado por los metadatos o el estado del partido. Se verifica activando y desactivando la palanca durante un tramo con momento narrativo y otro sin mensaje visible.

**RF-63 · P0.** La representación del campo debe actualizar el movimiento con intervalos de un segundo o menos y mostrar una secuencia sintética coherente entre pasador, receptor, balón y remate. Durante la posesión, el balón debe coincidir con la posición de su jugador; durante un pase debe salir del pasador y terminar en el receptor; durante el remate debe terminar sin poseedor dentro del arco. Se verifica reproduciendo una táctica propuesta y una jugada ocurrida, comprobando cada cambio de posesión y sus coordenadas.

**RF-64 · P1.** El backend debe poder guardar partidos, eventos, momentos y conversaciones del asistente en Supabase mediante una clave exclusiva del servidor. La falta temporal de la base no debe detener la reproducción en memoria. Se verifica con escrituras repetidas, eventos de origen conservados y una prueba de Supabase deshabilitado.

**RF-65 · P1.** Descubrir debe separar los partidos en vivo, el partido más reciente y el próximo partido. La sección de partidos en vivo no debe mostrarse cuando no existan partidos con ese estado. Se verifica con un catálogo sin partidos en vivo y otro con al menos uno.

**RF-66 · P1.** Un partido próximo debe abrir una previa con una presentación de ambos equipos y permitir elegir posibles formaciones. Cada selección debe actualizar la ubicación de los jugadores en la cancha. Se verifica eligiendo al menos dos formaciones de cada equipo.

**RF-67 · P1.** La previa debe ofrecer una simulación táctica para el equipo local y otra para el visitante. Cada simulación debe entregar fotogramas ordenados con posiciones de jugadores, balón, fase y resultado simulado. Se verifica reproduciendo ambas jugadas hasta su último fotograma.

**RF-68 · P1.** Un agente de previa debe producir los datos estructurados de alineaciones y simulaciones sin generar la interfaz ni modificar el estado real del partido. La salida debe indicar de forma visible que es sintética y que no representa un hecho ni una predicción. Se verifica validando el contrato y comparando el estado antes y después de generar la previa.

**RF-69 · P1.** Las tarjetas del partido más reciente y el próximo partido deben mostrar su contexto completo, mantener una jerarquía visual clara y aprovechar el ancho disponible sin espacios que oculten información. Se verifica en escritorio y móvil con textos de distinta longitud.

**RF-70 · P1.** Cada equipo debe ofrecer varias tácticas ofensivas seleccionables. El conjunto debe incluir ataque posicional, contraataque desde campo propio, progresión mediante pases hacia adelante y una jugada que libere a un delantero para rematar desde fuera del área. Cada táctica debe incluir al menos diez contactos de balón, la participación directa de cinco jugadores y una secuencia ordenada de apoyos, pases y finalización simulada. Cada fotograma debe conservar a los once jugadores de cada equipo. Los participantes directos deben distinguirse visualmente, pero los demás jugadores también deben desplazarse para sostener apoyos, coberturas, marcas y ajustes del bloque rival. El balón debe mostrarse junto al poseedor y viajar hasta el siguiente receptor. Los jugadores deben conservar su función y continuar desde su posición anterior: el portero interviene en el inicio, los defensores sostienen la cobertura, los mediocampistas conectan líneas y los atacantes ocupan los espacios de finalización. El siguiente receptor debe preparar su apoyo o desmarque antes del pase. El rival debe responder como en el seguimiento del partido: el jugador más cercano presiona, los demás ajustan marcas por carril y el bloque repliega o avanza sin quedarse inmóvil. La transición debe mantener jugadores repartidos en zonas defensivas, medias y ofensivas, sin desarmar el bloque ni devolver jugadores de forma instantánea a su posición inicial. Se verifica reproduciendo todas las opciones de local y visitante, comprobando 22 jugadores con movimiento, al menos una táctica que recorra el campo, una progresión mayoritariamente hacia adelante, un remate con poseedor atacante antes de entrar al área, el resaltado de participantes directos, la presión del rival y la continuidad entre fotogramas hasta el gol simulado.

**RF-71 · P1.** La previa debe consumir un documento aprobado con procedencia, fecha de actualización y marca de datos sintéticos. Mientras no exista Storage, el adaptador puede leer un archivo local intercambiable. Se verifica consultando el documento local y comprobando su metadato de origen.

**RF-72 · P1.** Debajo de las tácticas, cada equipo debe tener un resumen extensible y buscable con forma reciente, disponibilidad del plantel, jugadores clave, claves tácticas y alineación probable. Se verifica abriendo ambos equipos y buscando un dato de cada sección.

**RF-73 · P1.** La vista táctica del partido en vivo debe separar dos modos. Repetir reconstruye jugadas ocurridas hasta el tiempo actual a partir de sus eventos. Simular propone posibles jugadas siguientes sin modificar el partido. Se verifica avanzando el reloj, reproduciendo una secuencia de cada equipo y cambiando al modo de simulación.

**RF-74 · P1.** La vista táctica en vivo debe tomar la alineación inicial como base estable al menos hasta el medio tiempo. La cancha y las propuestas de ambos equipos deben usar los mismos jugadores y posiciones iniciales. Se verifica comparando la alineación mostrada antes y después de varias jugadas del primer tiempo.

**RF-75 · P1.** Todas las tarjetas de partidos deben usar una altura compacta, diferenciar los colores de ambos equipos y separarlos mediante un rayo oscuro en el centro. Un partido en vivo debe usar un icono reconocible de transmisión y un efecto ambiental animado en el fondo, sin reducir la legibilidad. El movimiento decorativo debe detenerse cuando el sistema indique que el usuario prefiere menos animaciones. Se verifica en Descubrir y Partidos con estados En vivo, Próximo y Finalizado, ambos equipos visibles, texto completo y la preferencia de movimiento reducido activa.

**RF-76 · P1.** El centro del partido debe mostrar el agente únicamente en Partido, como un panel lateral derecho que se abre o cierra mediante una flecha sin texto y sin perder la sesión. Con el agente oculto, el campo debe aprovechar todo el ancho disponible sin desbordarse. Partido también debe ofrecer una acción para entrar y salir de pantalla completa, conservando campo, comentarios y controles de reproducción. Se verifica alternando el agente y la pantalla completa en escritorio y móvil.

**RF-77 · P0.** El campo del partido en vivo debe representar once jugadores identificados por equipo y el balón mediante `TrackingFrame v1` a intervalos de 200 ms o menos. Todos los jugadores activos deben desplazarse con límites de velocidad y aceleración; el equipo con balón debe conservar su estructura de apoyo y el equipo sin balón debe asignar un presionante cercano y coberturas o marcas por carril, sin enviar a todos hacia el balón. La interfaz debe interpolar entre cuadros, conservar pausa, velocidad y saltos del reloj, y declarar si la fuente es sintética o estimada desde vídeo. Se verifica durante una ventana continua, al pausar, al cambiar la velocidad y al adelantar el partido.

**RF-78 · P0.** El partido en vivo debe coordinar eventos, balón y jugadores mediante situaciones reproducibles. Cada pase debe identificar un receptor distinto, llevar el balón hasta su zona y declarar su propósito cuando sea un cambio de orientación, pase al espacio, apoyo, salida segura o pase atrás. Una recuperación debe cambiar la posesión. Las faltas, tarjetas, lesiones y reanudaciones deben detener o reactivar el movimiento de forma visible y conservar sus eventos de origen. Se verifica con una secuencia que incluya recuperación y contraataque, pase largo, falta con tarjeta, paro por lesión y reanudación.

**RF-79 · P1.** La revisión comunitaria debe mostrar siempre varios partidos en una sola lista de tarjetas, sin separar Revisar resumen y Comunidad. Cada tarjeta debe incluir equipos, marcador, un resumen breve, likes, dislikes y acceso al detalle. La lista debe permitir buscar y filtrar por estado. Se verifica con al menos tres partidos y búsquedas por equipo y texto del resumen.

**RF-80 · P1.** El detalle comunitario de un resumen debe mostrar el equipo destacado, el marcador, el resumen completo, tácticas respaldadas por la información sintética del partido, un agente de preguntas, aprobación mediante like o dislike y comentarios sobre qué mejorar. Se verifica abriendo una tarjeta, votando, preguntando y publicando una sugerencia y un comentario.

**RF-81 · P1.** Los resúmenes, decisiones editoriales, likes, dislikes, sugerencias y comentarios deben poder persistirse en Supabase mediante la clave exclusiva del backend. Cuando Supabase esté deshabilitado o falle, la interfaz debe conservar el flujo en memoria sin detenerse. Se verifica reiniciando el backend con la base activa y con una prueba separada sin base.

**RF-82 · P1.** Los controles de tema y sesión de invitado deben estar dentro del sidebar izquierdo en escritorio. En el centro del partido, la línea de tiempo y sus controles deben quedar dentro del contenedor de Partido, debajo de los comentarios cuando estén visibles. Se verifica alternando el sidebar y los comentarios sin reiniciar el reloj.

**RF-83 · P1.** Cada momento narrativo debe mostrar un llamado breve y visible para abrir “Por qué importa”. La frase debe corresponder al tipo de acción, conservar el vínculo con los eventos de origen y mantenerse estable para la misma jugada. El catálogo debe poder leerse desde Supabase y contar con una alternativa local cuando la base esté deshabilitada. Se verifica con goles, remates, pases, faltas, tarjetas, recuperaciones y pérdidas, además de una ejecución sin Supabase.

**RF-84 · P1.** Al salir del centro de un partido y volver, la experiencia debe recuperar el minuto y velocidad guardados, la pestaña activa, la jugada y el jugador seleccionados, el tipo de resumen, el jugador del resumen personalizado, el estado de la simulación y la posición vertical. La reproducción debe volver pausada para no avanzar sin que la persona la vea. Se verifica navegando a otra pantalla y regresando al mismo partido.

**RF-85 · P1.** Los controles del partido deben usar una barra compacta pegada al borde inferior del estadio, sin encabezado de momentos ni un contador que aumente su altura. Las marcas de jugadas pueden mantenerse como puntos sobre la línea. Se verifica en escritorio y móvil sin espacio entre la barra y el borde inferior del campo.

**RF-86 · P1.** El selector de velocidad debe estar oculto en el punto en directo y aparecer solo después de retroceder. La barra debe ofrecer una acción para volver al punto en directo y recuperar automáticamente la velocidad normal al alcanzarlo. Se verifica reproduciendo en directo, retrocediendo, acelerando y regresando al borde en vivo.

**RF-87 · P1.** Partido debe narrar cada evento ocurrido mediante los datos disponibles. Un pase debe nombrar al pasador y al receptor. Remates, recuperaciones, presiones, faltas, tarjetas, interrupciones y reanudaciones deben tener una frase propia. Un momento importante debe aparecer encima de la barra con su minuto y una acción para cerrarlo, sin cubrir los controles. Se verifica con una secuencia sintética que incluya cada tipo de evento.

**RF-88 · P1.** La experiencia debe ofrecer un cuarto perfil llamado “Analista profesional”. Este perfil debe activar el nivel avanzado, mantener los comentarios del partido y permitir más hechos respaldados por la evidencia disponible. Se verifica seleccionándolo durante la configuración, desde Preferencias y dentro del Centro del Partido.

**RF-89 · P1.** Los perfiles Analista y Analista profesional deben mostrar el campo con una inclinación media en Partido, Resumen y detalle de un momento. Aficionado y Centrado en jugador deben conservar la vista plana. Los controles, comentarios y textos no deben inclinarse con el campo. Se verifica cambiando el perfil sin recargar la página en escritorio y móvil.

**RF-90 · P1.** En escritorio, Partido debe alinear el estadio a la izquierda y usar una columna derecha para los comentarios en vivo y los momentos. Los comentarios no deben cubrir el campo. Los momentos deben tener un espacio propio debajo de los comentarios. En pantallas pequeñas, ambos espacios deben pasar debajo del estadio sin producir desplazamiento horizontal. Se verifica con comentarios y momentos de distinta longitud.

**RF-91 · P1.** La barra de reproducción sobre el estadio debe permanecer oculta cuando no se usa y aparecer al pasar el cursor por el reproductor o enfocar uno de sus controles con teclado. En dispositivos sin cursor debe permanecer visible. Se verifica con ratón, navegación por teclado y una pantalla táctil.

**RF-92 · P1.** En pantalla completa, el panel derecho debe dedicar más espacio al momento actual. La acción que abre el análisis debe mostrar únicamente la frase vinculada a la jugada, sin una etiqueta adicional, usar todo el ancho disponible y tener una animación de atención que se desactive cuando la persona prefiera menos movimiento. Se verifica con mensajes de distinta longitud, pantalla completa y la preferencia de movimiento reducido.

**RF-93 · P1.** Resumen debe usar un único desplegable compacto para elegir entre resumen corto, extendido y personalizado. Cada opción debe incluir su descripción. El jugador solo debe elegirse cuando el tipo sea personalizado. Debajo, “Momento seleccionado” debe permitir elegir entre los momentos filtrados: solo goles en el resumen corto, varias jugadas relevantes en el extendido y jugadas de peligro del jugador en el personalizado. La jugada elegida debe actualizar tanto el análisis como el resaltado de la lista inferior. Se verifica cambiando tipo, jugador y momento sin salir de Resumen.

**RF-94 · P1.** En el paso Visualización de la configuración inicial, la tarjeta del modo seleccionado debe expandirse y explicar qué contenido estará disponible. Las tarjetas no seleccionadas deben conservar su tamaño normal. El flujo no debe repetir las elecciones en una sección adicional antes de finalizar. Se verifica seleccionando los cuatro modos, comparando sus detalles y terminando la configuración directamente.

**RF-95 · P1.** La cabecera inicial y las cabeceras internas que permitan cambiar el idioma deben usar un único selector con español, inglés, alemán, chino, hindi, francés y portugués. Una sesión nueva o restablecida debe comenzar en inglés, sin reemplazar la elección ya guardada por una persona. Se verifica limpiando las preferencias, recorriendo las siete opciones y recargando después de guardar una selección.

**RF-96 · P1.** La interfaz de partidos debe presentar el encuentro como una experiencia en vivo y no mostrar la palabra “simulación”. La barra principal debe usar “Partido en vivo” e “Iniciar partido”. El perfil de visualización no debe poder cambiarse desde esa barra porque se elige durante la configuración. Se verifica en Partidos, la previa, el Centro del Partido y la Vista táctica en español e inglés.

**RF-97 · P1.** El asistente del Centro del Partido debe abrirse y cerrarse mediante una única flecha sin texto, alineada con las pestañas de Partido, Resumen, Estadísticas y Vista táctica. La flecha solo debe aparecer en Partido y debe conservar el estado del panel. Se verifica abriendo y cerrando el panel, cambiando de pestaña y regresando a Partido.

**RF-98 · P1.** Los filtros de Partidos y sus contadores deben mantener contraste suficiente sobre el tema oscuro. Sus etiquetas y números deben mostrarse en blanco o con una combinación equivalente que cumpla la misma legibilidad. Se verifica con los estados En vivo, Próximo y Resumen, tanto activos como inactivos.

**RF-99 · P1.** El resumen de un partido finalizado debe ofrecer el mismo selector de tipo, selector condicional de jugador, espacio de momento seleccionado, análisis y lista de situaciones que la pestaña Resumen del Centro del Partido. La cabecera debe usar una ilustración profesional guardada como recurso local, sin depender de una URL externa. Se verifica cambiando los tres tipos, el jugador y el momento en un partido finalizado.

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

**RNF-07 · P0.** Los consumidores de eventos deben procesar entregas repetidas sin duplicar métricas, decisiones ni narraciones. Se verifica reenviando el mismo identificador de mensaje.

**RNF-08 · P1.** El procesamiento debe conservar el orden dentro de cada partido y permitir partidos distintos en paralelo. Se verifica intercalando eventos de dos partidos y comparando sus estados finales.

**RNF-09 · P1.** Las solicitudes narrativas deben tener vencimiento y no publicarse cuando el momento ya perdió vigencia. Se verifica retrasando una respuesta más allá de su límite.

**RNF-10 · P1.** El filtro, refinador, orquestador y trabajadores deben poder ejecutarse en varias instancias sin guardar estado local obligatorio. Se verifica deteniendo una instancia durante una prueba de carga y comprobando la continuidad.

**RNF-11 · P1.** El sistema debe aplicar control de carga, reintentos limitados y una cola de errores sin detener las métricas. Se verifica superando temporalmente la capacidad de los agentes y recuperando el flujo.

## **Criterio de alcance**

Una capacidad opcional solo se dará por terminada si tiene datos de entrada, cálculo o modelo, salida visible y una prueba que demuestre lo que afirma. Las métricas de velocidad y el análisis de vídeo requieren especial cuidado porque no pueden deducirse de un evento sin tiempos y posiciones adecuados.
