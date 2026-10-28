# **Decisiones tomadas**

Este documento registra lo acordado por el equipo el 6 y el 8 de octubre de 2026. Describe elecciones de diseño, no funciones ya terminadas.

## **Identidad del producto**

**1.** El nombre de marca del producto es The Prime Moment. Debemos usarlo en la interfaz, la documentación y las instrucciones de agentes. Los nombres del repositorio, módulos, paquetes y claves internas se mantienen como identificadores técnicos, salvo que se acuerde cambiarlos por separado.

## **Datos y eventos**

**1.** Definimos un formato interno común para los eventos. El contrato inicial y sus campos están en [formato de eventos](08-formato-de-eventos.md). Los adaptadores de cualquier fuente deben entregar ese mismo formato al núcleo del sistema.

**2.** Usaremos dos vías para obtener datos sintéticos: generaremos partidos propios y adaptaremos conjuntos adecuados como referencia. Antes de incorporar una fuente revisaremos sus condiciones de uso. No distribuiremos datos reales de la Premier League.

## **Tecnologías y repositorio**

**3.** El proyecto es un monorepo. El frontend estará en `apps/frontend` con JavaScript y React. El backend estará en `apps/backend` con Python, FastAPI y Uvicorn. FastAPI expondrá su documentación OpenAPI mediante Swagger UI en `/docs`.

**4.** Usaremos un monolito modular con límites hexagonales. El dominio del partido y sus reglas no deben depender de FastAPI, CrewAI, del origen de eventos ni de la interfaz. Los adaptadores conectarán vídeo, conjuntos sintéticos, agentes y API con el núcleo.

**4.1.** El backend usará Python 3.12. La versión se fija mediante `.python-version`, el paquete declara compatibilidad `>=3.12,<3.14` y `uv.lock` conserva las dependencias resueltas. Python 3.14 queda excluido mientras CrewAI no lo admita.

Para el flujo continuo mantendremos esos límites y añadiremos comunicación por eventos. El filtro, refinador, orquestador y trabajadores podrán desplegarse en varias instancias. Podemos iniciar dentro del monorepo y separar procesos sin cambiar los contratos del dominio.

## **Agentes y publicación**

**5.** Usaremos CrewAI en Python para coordinar tareas que necesiten interpretación. El 11 de octubre de 2026 refinamos el diseño: un servicio filtro, un catálogo de jugadas y un servicio de refinamiento prepararán la información antes de cualquier modelo. Un orquestador ligero enviará solo las solicitudes relevantes a agentes especializados mediante eventos.

La personalización será una política compartida y no un agente independiente en la primera versión. Las métricas y el estado seguirán un camino directo sin llamar a la IA. Los agentes principales cubrirán peligro y simulación, selección de momentos, narración, preguntas, resúmenes e investigación previa. La validación será obligatoria antes de publicar.

La distribución inicial de trabajo y el flujo de revisión están en [equipo de agentes](10-arquitectura-agentes.md).

El 11 de octubre de 2026 acordamos una asignación por demanda. GPT-4.1 mini será la base para clasificación, selección breve y validación semántica. GPT-4.1 se usará en narración, explicación de peligro, redacción de simulaciones, respuestas complejas, resúmenes e investigación. Los servicios deterministas no usarán modelos. La política completa está en [política de modelos de IA](12-politica-modelos-ia.md).

La investigación previa usará GPT-4.1 con una herramienta de búsqueda web. Los embeddings se reservan para recuperación semántica dentro de información aprobada y no reemplazan la búsqueda en Internet.

La previa táctica usa un agente independiente del narrador en vivo. En la primera versión funciona con reglas deterministas y datos sintéticos para que las formaciones y simulaciones sean reproducibles. El agente entrega un contrato con posiciones y fotogramas; React se limita a representarlos. Esta salida se marca como simulación y no se presenta como predicción del resultado.

La información editorial de la previa parte de un documento JSON local aprobado y sintético. Su estructura toma como referencia las secciones habituales de una previa periodística —forma reciente, bajas, jugadores clave, duelo táctico y alineación probable— sin copiar datos reales. El contrato conserva la procedencia para sustituir el lector local por Blob Storage sin cambiar la interfaz.

La vista táctica en vivo reutiliza la alineación inicial y las propuestas del agente de previa. Mantiene separados dos resultados. Repetir se calcula de forma determinista con los eventos que ya ocurrieron y conserva sus identificadores de origen. Simular usa las jugadas sintéticas del agente como posibilidades futuras y no cambia el estado ni el marcador.

Las propuestas tácticas comparten los principios de movimiento del seguimiento en vivo. El defensor más cercano sale a presionar y el resto ajusta marcas y coberturas por carril según el balón y los atacantes. Además de los ataques posicionales, cada equipo tiene una transición desde campo propio y una progresión vertical para mostrar desplazamientos de campo completo y pases hacia adelante.

El conjunto de cinco propuestas por equipo incluye una jugada que libera al delantero frente al área. El último contacto se mantiene fuera del área y el fotograma siguiente representa el recorrido del remate hasta el arco.

Las tarjetas reutilizables de partidos comparten la presentación de dos colores y el rayo central en todos los estados. En vivo se distingue mediante un icono de transmisión y luces ambientales suaves. Estas animaciones son decorativas y se desactivan con la preferencia de movimiento reducido del sistema.

El Centro del Partido organiza la experiencia en Partido, Resumen, Estadísticas y Vista táctica. Resumen reúne el análisis de momentos y las explicaciones importantes. Los comentarios en vivo se activan dentro de Partido mediante una palanca y dejan de ocupar una pestaña propia. El agente solo aparece junto al campo en un panel derecho controlado por una flecha; la vista del partido puede pasar a pantalla completa sin crear otra sesión de reproducción.

Los agentes podrán proponer interpretaciones y deducir conclusiones desde evidencia disponible. Los cálculos de cifras y el estado del partido serán reproducibles. La verificación contrastará cualquier conclusión con eventos y métricas. Si detecta un error, el flujo debe registrar el reporte, corregir o retirar la conclusión y volver a verificarla.

Los análisis finales tendrán una revisión antes de publicarse. La persona o mecanismo exacto de esa revisión sigue pendiente. Ningún resultado generado por agentes debe saltarse ese paso.

## **Vídeo e idiomas**

**6.** La demo usará vídeo como ejemplo de transmisión. La experiencia debe actualizarse durante su reproducción. No llamaremos tiempo real a un proceso hasta medir el retraso entre vídeo, evento y salida. La extracción automática de eventos desde vídeo se investigará y probará por separado.

**7.** La salida admitirá inglés y español. El idioma afectará mensajes en directo, explicaciones y resúmenes.

## **Investigación y aplazamientos**

**8.** Investigaremos qué métricas aportan valor, cómo se obtienen hoy y qué bibliotecas o modelos abiertos compatibles con Python pueden ayudarnos. Los primeros hallazgos están en [investigación de métricas y herramientas](09-investigacion-metricas-y-herramientas.md).

**9.** La meta numérica de latencia, el contrato con sistemas externos y el alcance de funciones opcionales siguen pendientes. Se tratarán después de estabilizar el formato, el flujo de datos y la primera demo.

## **Infraestructura Azure para datos e ingesta**

**10.** El flujo integrado de datos usará Azure Event Hubs para transportar eventos normalizados y Azure Blob Storage para conservar partidos sintéticos, vídeos autorizados y observaciones de prueba. El flujo local seguirá funcionando sin Azure mediante adaptadores intercambiables.

La infraestructura de esta parte se definirá con Bicep y se desplegará mediante Azure CLI. Los nombres, la región, el grupo de recursos y la suscripción serán configurables para que cada integrante pueda desplegar los servicios en su propia cuenta sin editar la plantilla ni compartir credenciales. El [plan detallado de datos y visión](persona-1-datos-y-vision/plan-general.md) describe el alcance inicial.

**11.** El 18 de octubre de 2026 se refinó el transporte en tres rutas lógicas. Event Hubs recibirá todos los eventos y alimentará el filtro. La telemetría y las métricas no críticas usarán un flujo de retención corta y aceptarán pérdida controlada. Las decisiones importantes usarán Azure Service Bus con reintentos, deduplicación y cola de mensajes no procesables. Esta decisión reemplaza la idea de usar un único canal para todo.

**12.** Los vídeos permitidos, las observaciones crudas y los recortes destacados se almacenarán en Blob Storage. Un recorte propuesto permanece pendiente hasta una decisión humana. La simulación local solo calcula sus límites y registra la decisión; no afirma que el archivo de vídeo ya haya sido cortado ni cargado.

**13.** La primera integración visible será local y sintética. El botón de simulación debe recorrer las seis rutas del filtro y permitir revisar recortes. El despliegue de las colas, contenedores y trabajadores en Azure se hará después de revisar costos y aprobar expresamente la ejecución del script.

**14.** Usaremos Supabase como base de datos de la experiencia para conservar partidos, eventos normalizados, momentos y conversaciones del asistente. React no recibe la clave secreta. El backend realiza las escrituras mediante un adaptador y conserva el modo en memoria cuando la base está deshabilitada o no responde. El esquema se administra con migraciones versionadas bajo `supabase/migrations`.

**15.** El movimiento del partido en vivo tendrá un flujo separado de los eventos narrativos. El backend entregará ventanas de hasta 30 segundos de `TrackingFrame v1` a 5 cuadros por segundo, con un cuadro anterior y otro posterior para interpolar sin saltos. React moverá los 22 jugadores y el balón con `requestAnimationFrame`, sincronizado con el mismo reloj que controla eventos y mensajes. El mock actual conserva una forma 4-3-3, asigna un presionante y marcas por carril cuando se defiende, limita velocidad y aceleración y declara `source=synthetic_mock`. Un adaptador de vídeo futuro podrá entregar el mismo contrato con `source=video_model` sin cambiar la cancha.

**16.** Los partidos marcados en vivo usarán un escenario propio con situaciones coordinadas. `MatchEvent 1.0` conserva campos opcionales para receptor, situación y duración del paro. Los pases hacia atrás mayores a ocho unidades requieren una razón táctica declarada; los cambios de orientación y pases al espacio tienen mínimos de distancia o progresión. Faltas, tarjetas, lesiones y reanudaciones siguen el mismo reloj y la interfaz muestra su estado sobre la cancha. Esta primera versión usa un guion sintético validado; el siguiente paso será sustituir la selección del pase por un motor que evalúe opciones en cada cuadro.

## **Decisión de demo del 27 de octubre de 2026**

Por decisión del usuario, GameState queda fuera de la demo con los renders
actuales de MESSI. La prueba completa funcionó técnicamente, pero produjo solo
4 detecciones, sin posiciones calibradas, y tardó unos 27 minutos para un vídeo
de 3 minutos. Se eliminó únicamente su Container App de Azure; se conservan el
código, la imagen y las evidencias para investigación posterior.

La dirección acordada es combinar Roboflow Suite (observaciones espaciales),
SoccerNet TeamSpotting (candidatos temporales) y los eventos, posiciones y
metadatos del mismo partido MESSI. Las salidas de los modelos siguen siendo
experimentales hasta contrastarlas; los datos del simulador no prueban que una
acción o identidad haya sido detectada desde vídeo.

La integración complementaria debe conservar el origen de cada campo, los
identificadores del partido y el mismo reloj de vídeo. No se sumará dos veces
una acción presente en varias fuentes ni se confirmará un jugador por mera
proximidad temporal. La integración ya tiene implementación y pruebas locales
con contratos HTTP y proveedores de inferencia dobles; falta ejecutar este
flujo modificado con ambos servicios Azure encendidos y revisar su calidad.
Véase [la evidencia de integración híbrida](persona-1-datos-y-vision/evidencias/messi-hibrido-20261027.md).

## **Estado histórico de la base del proyecto**

El monorepo y los proyectos iniciales de frontend y backend están preparados. La ingesta sintética y la analítica de Persona 2 tienen módulos y pruebas propios. El flujo de la experiencia usa el adaptador de narrativa de Persona 3 y puede seleccionar el proveedor provisional, fixture o Azure. El filtro, el catálogo inicial, el despacho reproducible, la simulación local de rutas, la revisión de recortes y la previa táctica determinista están implementados. El canal durable real, el corte físico del vídeo, la investigación previa con fuentes externas, la simulación contrafactual, los resúmenes de medio tiempo y la alta disponibilidad todavía están pendientes.
