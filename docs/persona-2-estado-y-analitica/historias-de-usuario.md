# Historias de usuario de estado y analítica

Las personas usuarias de este módulo son sobre todo Persona 3 (narración) y Persona 4 (API y pantalla), que consumen sus contratos. El estado de cada historia distingue lo verificado en local de lo que falta probar en Azure.

## Épica A: estado reproducible

### EA-US-01 · Consultar el estado del partido

**Como** Persona 4,
**quiero** un `MatchSnapshot v1` con marcador, período, reloj, posesión y estadísticas,
**para** mostrar el estado en cualquier instante del vídeo.

**Prioridad:** P0. **Estado:** verificada localmente. **Evidencia:** [EA-US-01](evidencias/EA-US-01.md).

**Criterios de aceptación:**

- El marcador, la posesión y el reloj coinciden con la secuencia de entrada.
- Dos ejecuciones del mismo partido producen el mismo snapshot.
- El orden de llegada no cambia el resultado.
- Un evento que contradice los metadatos se excluye y se informa.

**Requisitos relacionados:** RF-07, RNF-01.

### EA-US-02 · Reconstruir el estado ante tardíos y correcciones

**Como** responsable de la ingesta,
**quiero** que un evento tardío o corregido reconstruya el estado,
**para** que las cifras no dependan del orden de llegada.

**Prioridad:** P1. **Estado:** verificada localmente. **Evidencia:** [EA-US-02](evidencias/EA-US-02.md).

**Criterios de aceptación:**

- Un tardío produce el mismo estado que si hubiera llegado a tiempo.
- Una corrección explícita y un retiro reconstruyen el estado y registran una revisión con el antes y el después.
- Un repetido idéntico no cambia nada; uno con contenido distinto se rechaza como conflicto.
- Saltar en el vídeo reconstruye el estado sin crear una revisión.

**Requisitos relacionados:** RF-05, DV-US-05.

## Épica B: cifras trazables

### EA-US-03 · Calcular estadísticas recalculables

**Como** verificador de Persona 3,
**quiero** que cada cifra lleve su fórmula, unidad y eventos de origen,
**para** comprobar cualquier afirmación.

**Prioridad:** P0. **Estado:** verificada localmente. **Evidencia:** [EA-US-03](evidencias/EA-US-03.md).

**Criterios de aceptación:**

- Cada conteo coincide con el número de sus eventos de origen.
- Una proporción sin denominador queda no disponible, no en cero.
- Las métricas espaciales respetan la dirección de ataque de cada período.
- Velocidad y distancia recorrida se declaran no disponibles con `MatchEvent 1.0`.
- Cada clave emitida figura en el catálogo con su versión.

**Requisitos relacionados:** RF-08, RF-10, RF-11, RF-12, RNF-03.

## Épica C: jugadas y patrones

### EA-US-04 · Agrupar jugadas y detectar patrones

**Como** analista,
**quiero** ver jugadas completas y patrones definidos por reglas,
**para** entender la secuencia y no solo el último evento.

**Prioridad:** P0 (patrón) y P1 (jugadas). **Estado:** verificada localmente. **Evidencia:** [EA-US-04](evidencias/EA-US-04.md).

**Criterios de aceptación:**

- Una recuperación, varios pases y un tiro forman una sola jugada sin perder sus eventos.
- Cada patrón tiene al menos un ejemplo positivo y uno negativo.
- Una secuencia que no cumple la regla no la activa.
- Sin posiciones o dirección, la regla no se afirma y queda una nota.

**Requisitos relacionados:** RF-09, RF-29, RF-33.

### EA-US-05 · Comparar tramos, hitos e indicadores propios

**Como** espectador,
**quiero** saber cuándo cambia el control, cuándo el partido se vuelve caótico y cuándo un jugador alcanza un hito,
**para** entender el ritmo del partido.

**Prioridad:** P1 (P2 para caos). **Estado:** verificada localmente. **Evidencia:** [EA-US-05](evidencias/EA-US-05.md).

**Criterios de aceptación:**

- La presión sostenida se compara con el tramo anterior.
- El cambio de control se detecta en dos tramos de dominio opuesto y no en un dominio constante.
- El caos se detecta en un tramo de cambios frecuentes y no en uno estable.
- Un hito se emite una vez en el evento que lo alcanza y no se emite si no se alcanza.
- Los indicadores muestran componentes y se identifican como escalas del equipo.

**Requisitos relacionados:** RF-17, RF-30, RF-31, RF-32.

## Épica D: atención

### EA-US-06 · Seleccionar momentos con motivos visibles

**Como** Persona 3,
**quiero** momentos candidatos con prioridad, hechos, límites y motivos,
**para** narrar solo lo relevante sin inventar causas.

**Prioridad:** P0. **Estado:** verificada localmente. **Evidencia:** [EA-US-06](evidencias/EA-US-06.md).

**Criterios de aceptación:**

- Varios eventos parecidos no generan varios mensajes.
- La prioridad es la suma visible de sus motivos.
- Cada decisión de emitir o descartar queda registrada con motivos.
- Club y jugador favoritos cambian prioridad y selección, nunca hechos ni fuentes.
- Los goles del rival se emiten siempre.

**Requisitos relacionados:** RF-14. Apoya RF-15, RF-16 y RF-23 a RF-26.

## Épica E: modelos y Azure

### EA-US-07 · Evaluar xT, VAEP y xG sin presentar valores sin validar

**Como** equipo,
**quiero** saber qué modelos de valor son viables y tener adaptadores probados,
**para** activarlos solo cuando haya datos y validación.

**Prioridad:** P1. **Estado:** adaptadores verificados localmente; modelos desactivados. **Evidencia:** [EA-US-07](evidencias/EA-US-07.md).

**Criterios de aceptación:**

- Sin modelo validado, la métrica sale no disponible con su motivo.
- Cada adaptador se valida contra una referencia o con controles de plausibilidad documentados.
- Un modelo sin procedencia o entrenado solo con datos sintéticos no se activa.

**Requisitos relacionados:** módulo 4 del plan de Persona 2.

### EA-US-08 · Procesar el flujo en Azure

**Como** equipo,
**quiero** que la analítica consuma Event Hubs y publique sus salidas en Azure,
**para** que la demo funcione en la plataforma del hackathon.

**Prioridad:** P0. **Estado:** adaptadores y puente verificados localmente; despliegue y prueba de humo pendientes. **Evidencia:** [EA-US-08](evidencias/EA-US-08.md).

**Criterios de aceptación:**

- El procesador consume los eventos aceptados por la ingesta de Persona 1 y respeta la marca de tardío.
- Publica snapshots, momentos, retiros y revisiones con clave de partición por partido.
- Guarda un registro del análisis con hashes en Blob Storage.
- Los momentos recibidos desde Azure coinciden con el cálculo local.
- La infraestructura se despliega sin modificar `main.bicep` ni usar claves.

**Requisitos relacionados:** decisión 10 de [decisiones tomadas](../07-decisiones-tomadas.md), RNF-02, RNF-03.

### EA-US-09 · Entregar ejemplos e integrar con Persona 3 y 4

**Como** Persona 3 o Persona 4,
**quiero** ejemplos válidos, mínimos e inválidos y una implementación del `AnalyticsPort`,
**para** trabajar en paralelo y conectar los módulos sin reescribirlos.

**Prioridad:** P0. **Estado:** verificada localmente; integración probada en una copia de la rama de Persona 4. **Evidencia:** [EA-US-09](evidencias/EA-US-09.md).

**Criterios de aceptación:**

- Hay un ejemplo válido, uno sin opcionales y uno inválido de cada contrato.
- Los ejemplos se regeneran desde el código y una prueba detecta si quedaron viejos.
- `MatchAnalytics` cumple el `AnalyticsPort` de Persona 4.

**Requisitos relacionados:** contratos de trabajo, RNF-04.
