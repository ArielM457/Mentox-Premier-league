# **Persona 2: estado y analítica del partido**

## **Objetivo**

Transformar eventos normalizados en estado, estadísticas y momentos candidatos explicables. Esta persona es dueña de los cálculos y reglas reproducibles. No redacta mensajes finales ni controla la publicación.

## **Módulos a cargo**

**1. Estado del partido.** Mantener marcador, período, reloj, posesión y conteos por equipo y jugador. Definir cómo se reconstruye el estado cuando llega un evento tardío o corregido. Entregar `MatchSnapshot v1`.

**2. Estadísticas básicas.** Calcular tiros, goles, pases intentados y completados, recuperaciones y cambios de posesión. Documentar denominadores, unidades, ventanas y casos sin datos. Conservar los eventos de origen de cada cifra.

**3. Secuencias y patrones.** Agrupar acciones en jugadas. Detectar al menos un patrón con regla comprobable, como presión sostenida o progresión rápida. Agregar comparaciones entre tramos, hitos de jugador y señales de cambio de control cuando los datos lo permitan.

**4. Modelos de valor.** Investigar y adaptar xT, VAEP y xG desde bibliotecas o modelos que acepten datos comparables. Para cada modelo, revisar entradas requeridas, pesos, licencia, calibración y validación con eventos sintéticos. Si faltan campos o un modelo no se puede validar, la métrica queda desactivada y no se presenta como xT, VAEP o xG.

**5. Selección de atención.** Crear el motor que puntúa momentos según hechos medidos, novedad, repetición y relevancia para preferencias. Entregar `InsightCandidate v1` con prioridad, razones y eventos de origen. Los agentes de Persona 3 pueden revisar o adaptar esa propuesta sin alterar las cifras.

**6. Indicadores propios.** Probar control, impulso y caos como fórmulas versionadas. Mostrar sus componentes y evitar que una escala creada por el equipo parezca una métrica oficial.

## **Entregables**

**1.** Motor de estado con reconstrucción reproducible desde un partido sintético.

**2.** Catálogo de métricas elegidas con fórmula, datos necesarios, unidad y ejemplos.

**3.** Detectores de secuencias y patrones con ejemplos positivos y negativos.

**4.** Motor de atención con motivos visibles para emitir o descartar un momento.

**5.** Informe de viabilidad y, cuando corresponda, adaptadores probados para xT, VAEP y xG.

## **Trabajo independiente**

Puede desarrollar todo con eventos fijos basados en `MatchEvent v1`. Para probar el motor de atención puede crear preferencias de ejemplo sin esperar a Persona 3. Entrega snapshots y candidatos como archivos de prueba para que Persona 3 y Persona 4 trabajen en paralelo.

Sus archivos principales estarán en `domain` y `application` dentro del backend. Las bibliotecas de modelos entran por adaptadores separados; el dominio sigue funcionando si no están instaladas.

## **Comprobación de entrega**

Dos ejecuciones del mismo partido deben generar las mismas estadísticas y momentos. Una cifra debe poder recalcularse desde sus eventos. Las secuencias que no cumplen un patrón no deben activarlo. Cada métrica avanzada requiere comparación con una referencia o una prueba de plausibilidad documentada.

Requisitos principales: RF-07 a RF-12, RF-14, RF-17 y RF-29 a RF-33. Apoya RF-15, RF-16 y RNF-01 a RNF-03.
