# **Investigación inicial de métricas y herramientas**

Revisión realizada el 6 de octubre de 2026. Esta investigación orienta la selección de métricas y bibliotecas. Ninguna herramienta de análisis de vídeo o métrica avanzada está integrada todavía.

## **Métricas para empezar con eventos**

**1. Tiros, goles y pases completados.** Se obtienen contando eventos y resultados. Su utilidad es clara para el estado del partido y permite verificar el cálculo fácilmente. La [glosa de StatsBomb](https://stats-portal.statsbomb.com/glossary) muestra ejemplos de definiciones basadas en tipos y resultados de eventos. Debemos fijar nuestras propias reglas para evitar diferencias entre proveedores.

**2. Precisión de pases.** Se calcula como pases completados entre pases intentados, con una regla explícita para excluir o incluir acciones especiales. Requiere evento de pase y resultado. La distancia del pase necesita posiciones inicial y final, además de dimensiones del campo. La dificultad no es una distancia: requiere más contexto, como presión, ángulo, zona o posición de rivales.

**3. Recuperaciones y presión.** Podemos contar recuperaciones y eventos de presión, y mostrar su tendencia por intervalos. Para explicar una presión alta hacen falta posiciones del campo y ventanas de tiempo. [StatsBomb](https://statsbomb.com/what-we-do/soccer-data/) destaca que la presión registrada por evento añade contexto que un simple conteo de entradas no ofrece.

**4. Pases progresivos y entradas al último tercio.** Requieren posición de inicio y fin, dimensiones del campo y dirección de ataque por período. Debemos declarar una regla propia antes de calcularlos. Un [ejemplo publicado por StatsBomb](https://blogarchive.statsbomb.com/articles/soccer/line-breaking-passes-to-progressive-actions-in-the-bundesliga/) define acción progresiva según cuánto acerca el balón a la portería rival. Esto muestra que el umbral forma parte de la definición y no debe ocultarse.

**5. Intensidad de presión.** PPDA compara pases permitidos al rival con acciones defensivas en una zona definida. Un valor menor suele indicar presión más intensa. [StatsBomb explica la fórmula y la zona de cálculo](https://blogarchive.statsbomb.com/articles/soccer/defensive-metrics-measuring-the-intensity-of-a-high-press/). Un tramo corto puede dar valores inestables, por lo que no lo proponemos como primer aviso en directo.

## **Métricas que necesitan modelos o datos más ricos**

**6. Calidad del tiro.** xG estima la probabilidad de gol de un tiro según características como distancia, ángulo, parte del cuerpo y jugada previa. Modelos más ricos incorporan posición del portero y defensores. [StatsBomb explica estas variables](https://statsbomb.com/soccer-metrics/expected-goals-xg-explained/). No llamaremos xG a una puntuación improvisada ni mostraremos un valor si faltan los datos o un modelo validado.

**7. Valor de acciones.** xT valora el avance del balón a zonas con distinta probabilidad de crear peligro. VAEP estima el cambio de probabilidad de marcar o recibir gol tras una acción. La biblioteca Python [socceraction documenta xT](https://socceraction.readthedocs.io/en/stable/documentation/valuing_actions/xT.html) y [VAEP](https://socceraction.readthedocs.io/en/stable/documentation/valuing_actions/vaep.html). Son candidatos para investigación posterior porque necesitan datos comparables, preparación y validación del modelo.

**8. Velocidad y distancia recorrida.** Necesitan posiciones sucesivas con tiempo y calibración del campo. Una posición aislada o un pase con punto inicial y final no bastan para medir la velocidad real del balón o de un jugador. La calidad del seguimiento y la frecuencia de cuadros condicionan el resultado.

**9. Control, impulso y caos.** Son indicadores propuestos por este proyecto, no métricas oficiales. Primero debemos definir fórmula, ventana temporal, escala y ejemplos en que el indicador ayude a explicar el partido. Nunca deben presentarse como hechos independientes de sus componentes.

## **Herramientas Python candidatas**

**socceraction.** Sirve para normalizar acciones de proveedores y calcular xT o VAEP. Su [documentación](https://socceraction.readthedocs.io/en/stable/index.html) describe esos módulos. Es útil para prototipos y comparación metodológica. Adaptar sus entradas a nuestro formato requiere trabajo; no se ha probado todavía con datos sintéticos del proyecto.

**statsbombpy y StatsBomb Open Data.** [statsbombpy](https://github.com/hudl/statsbombpy) permite explorar eventos y tramas de ejemplo. El [repositorio oficial de datos](https://github.com/hudl/open-data) explica el formato y las condiciones de atribución. Puede orientar definiciones y pruebas locales, pero sus partidos reales no deben entrar en el conjunto entregado ni confundirse con los eventos sintéticos del reto.

**SoccerNet.** El [kit de detección de acciones](https://github.com/SoccerNet/sn-spotting) contiene datos, evaluación y métodos de referencia para localizar acciones en vídeo. El [kit de reconstrucción del estado](https://github.com/SoccerNet/sn-gamestate) aborda seguimiento e identificación de atletas. Son candidatos de investigación para la vía de vídeo. La existencia de estos modelos no demuestra que funcionen con nuestra señal, en directo ni con la latencia deseada. Además, el acceso y los permisos de los vídeos deben revisarse por separado.

**CrewAI.** Sus [Flows y Crews](https://docs.crewai.com/en/concepts/flows) permiten coordinar pasos controlados y agentes especializados. La [documentación de instalación](https://docs.crewai.com/en/installation) indica compatibilidad con Python 3.10 a 3.13. Lo usaremos para interpretación, contraste y narración, con revisión antes de publicar análisis finales.

## **Prácticas para este proyecto**

**1.** Conservar el evento y su origen junto a cada estadística y explicación.

**2.** Calcular cifras con código verificable. Los agentes pueden interpretarlas, pero no reemplazar su cálculo.

**3.** Registrar versión de fórmula y umbrales para que una métrica pueda reproducirse.

**4.** Evaluar por separado precisión de detección de vídeo, precisión de métricas y calidad de narración.

**5.** Medir el retraso de cada etapa con el mismo vídeo y hardware que se usarán en la demo.

**6.** Comprobar licencia de código, pesos de modelos, conjuntos de datos y vídeos antes de incorporarlos.

## **Selección inicial propuesta**

Para la primera fase proponemos tiros, goles, precisión de pases, recuperaciones y cambios de posesión. Después añadiremos progresión y presión si el conjunto sintético incluye posiciones fiables. xG, VAEP, velocidades y detección automática desde vídeo quedan como investigación hasta demostrar datos, calidad y tiempo de respuesta suficientes.
