# **Persona 3: agentes y narración**

## **Objetivo**

Convertir hechos y momentos candidatos en explicaciones verificables para cada usuario. Esta persona coordina los agentes con CrewAI y define cómo se revisan, corrigen y preparan las narraciones. No calcula el marcador ni las métricas base.

## **Módulos a cargo**

**1. Flujo de agentes.** Implementar la coordinación del observador, analista táctico, selector, narrador, personalizador, verificador y agente de resumen definidos en [el diseño de agentes](../10-arquitectura-agentes.md). Combinar responsabilidades si las pruebas muestran que varios agentes retrasan la salida sin mejorarla.

**2. Explicaciones en directo.** Recibir `MatchSnapshot v1` e `InsightCandidate v1`. Producir una explicación breve de qué pasó y por qué importa, con fuentes y una marca clara para cualquier inferencia. El agente puede responder que los datos no alcanzan para afirmar una causa.

**3. Personalización.** Producir versiones realmente diferentes para casual y analista. Aplicar club favorito, jugador favorito y nivel simple, normal o avanzado a la selección y redacción. Mantener los hechos y las cifras iguales entre versiones.

**4. Inglés y español.** Generar o adaptar mensajes, respuestas y resúmenes en ambos idiomas. Conservar nombres propios, valores, unidades y tiempo de partido. Revisar términos futbolísticos con la persona de UX/UI.

**5. Preguntas y respuestas.** Responder preguntas sobre el partido desde estado y eventos disponibles. Las respuestas deben citar los identificadores internos de la evidencia y reconocer lo que no se puede determinar.

**6. Resúmenes y revisión.** Generar un resumen del partido y variantes por club o jugador. Entregarlo en estado pendiente. Definir con Persona 4 los estados de revisión y el paso que impide publicar el análisis final antes de la aprobación acordada.

**7. Reportes de error.** Cuando llega un reporte, el verificador contrasta la afirmación original con métricas y eventos. Registra si había error, si la evidencia es insuficiente o si la afirmación era correcta. Propone corrección o retirada y vuelve a verificar antes de publicarla.

## **Entregables**

**1.** Flujo CrewAI con entradas y salidas estructuradas, límites de tiempo y comportamiento cuando un agente falla.

**2.** `NarrativeDraft v1` con texto, idioma, modo, preferencias, fuentes y resultado de verificación.

**3.** Colección de ejemplos en inglés y español para los mismos momentos, incluidos casos con datos insuficientes.

**4.** Flujo de preguntas, resumen final, revisión y tratamiento de reportes.

**5.** Registro de decisiones de los agentes que permita entender por qué se eligió o descartó una narración.

## **Trabajo independiente**

Puede comenzar con snapshots y momentos de ejemplo escritos según los contratos compartidos. No necesita que Roboflow, SoccerNet ni las métricas avanzadas funcionen para construir y evaluar los agentes. Usa un proveedor de modelos intercambiable hasta que el equipo confirme credenciales y costes.

Sus archivos principales estarán en la aplicación de narración y los adaptadores de CrewAI dentro del backend. Persona 4 consume borradores y estados mediante interfaces, sin llamar directamente a los agentes desde React.

## **Comprobación de entrega**

Cada cifra y afirmación debe coincidir con la evidencia recibida. Los dos idiomas deben conservar datos iguales. Los modos casual y analista deben cambiar contenido y detalle. Un reporte falso no debe cambiar una conclusión correcta; un reporte válido debe producir una corrección trazable. Un resumen sin revisión no debe publicarse.

Requisitos principales: RF-15, RF-16, RF-18, RF-21 a RF-28 y RF-34 a RF-39. Persona 4 implementa los controles visibles de estos requisitos.
