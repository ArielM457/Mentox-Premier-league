# Flujo del programa

## 1. Arranque

Uvicorn importa `match_intelligence.main:app`. FastAPI registra rutas de sistema, partidos, narrativa, analítica, comunidad e integración. El ciclo de vida prepara el runtime de observaciones y cierra conexiones al terminar.

Cuando se necesita el registro de partidos, `registry.py` selecciona narrativa, motor analítico y fuente según las variables de entorno. En modo sintético prepara tres escenarios: aceptación, analítica y directo. Con Supabase configurado puede cargar partidos guardados y mantiene el escenario en vivo cuando corresponde. Si la lectura remota falla, el código registra el fallo y conserva una alternativa sintética.

## 2. Configuración del espectador

React carga las preferencias desde `localStorage` mediante `PreferencesProvider`. La configuración inicial permite elegir idioma, club, jugador y modo. Preferencias permite además cambiar el nivel de explicación y opciones de comentarios.

El modo jugador necesita un jugador seleccionado. El modo profesional fija nivel avanzado y comentarios. Los valores modifican las solicitudes y la selección de contenido; no alteran los hechos del partido.

## 3. Descubrimiento y previa

La interfaz consulta los partidos y separa disponibles/en vivo, último y próximo según la información recibida. El detalle puede abrir una previa con formaciones y simulaciones tácticas sintéticas. Estas secuencias muestran alternativas reproducibles y no actualizan el estado real de la sesión.

## 4. Reproducción y estado

El centro del partido conserva un reloj. A partir de ese tiempo consulta eventos, estado, seguimiento y overlays. El motor usa solo los datos ocurridos para preparar cifras y candidatos.

Los mensajes en directo llegan por SSE. La interfaz decide qué mensaje corresponde al instante actual y conserva el historial. Pausar, saltar o reiniciar debe cerrar/reconstruir el canal y las consultas necesarias sin mezclar futuro e historial.

El campo interpola posiciones y mantiene la procedencia del seguimiento. El tiempo de vídeo, el reloj deportivo y el tiempo de procesamiento son conceptos distintos.

## 5. Del evento a la explicación

El motor analítico calcula estado, estadísticas y patrones. El filtro puede clasificar una ventana en seis rutas; el refinador prepara una solicitud corta y el orquestador determina el despacho.

La experiencia HTTP también puede pedir narración directamente a su `NarrativePort`. No debe suponerse que toda llamada de la interfaz atraviesa siempre la cola de eventos importantes. La integración de workers es un camino separado.

El proveedor narrativo elige evidencia, produce o adapta una explicación y aplica controles. En local se usan plantillas. En Azure/CrewAI hay selección estructurada y respaldos locales; el [detalle de agentes](agentes.md) explica qué sigue siendo determinista.

## 6. Momento y preguntas

Seleccionar un momento abre su explicación, métricas y referencias. Las preguntas se envían con el tiempo actual y las preferencias. Una respuesta debe apoyarse en el estado disponible; si no hay evidencia suficiente, debe indicarlo.

Las comparaciones «qué pasaría si» cambian supuestos dentro de una simulación local, sin reescribir el marcador ni presentar el resultado como un hecho ocurrido.

## 7. Resumen y editorial

La API prepara variantes de resumen y puede enfocarlas en club o jugador. El contenido final permanece sujeto al estado editorial. Aprobar o rechazar es una operación explícita; la consulta de publicación rechaza borradores pendientes.

Los reportes se contrastan con hechos y fuentes. Las propuestas de highlight contienen intervalos y referencias; una aprobación de propuesta no demuestra que se haya cortado y almacenado un vídeo.

## 8. Comunidad y persistencia

Los usuarios pueden votar, sugerir o comentar en salas de revisión. La moderación filtra contenido y se aplican límites de frecuencia. El canal comunitario comunica cambios a sus suscriptores.

La persistencia es opcional. Sin configuración remota, la sesión vive en memoria y las preferencias en el navegador. Con Supabase se pueden guardar entidades de experiencia y comunidad; eso no convierte automáticamente todos los estados locales y buses en servicios distribuidos.

## 9. Visión

El camino de visión puede reproducir resultados precalculados o enviar fotogramas a un servicio configurado. El runtime publica observaciones y la interfaz las sincroniza con el cursor. Su salida sigue siendo detección, acción o candidato, hasta que una conversión validada confirme eventos deportivos. Consultar [datos y visión](datos-y-vision.md).
