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

## Épica F: seguimiento y demostración

### EA-US-10 · Medir velocidad y distancia desde posiciones

**Como** espectador que sigue a un jugador,
**quiero** ver su distancia recorrida, su velocidad y un aviso cuando supera un umbral,
**para** entender su esfuerzo durante el partido.

**Prioridad:** P2 (RF-12). **Estado:** verificada con trayectorias conocidas y seguimiento simulado; posiciones reales de vídeo pendientes. **Evidencia:** [EA-US-10](evidencias/EA-US-10.md).

**Criterios de aceptación:**

- Distancia y velocidad coinciden con trayectorias de resultado conocido.
- Los saltos imposibles y las pistas perdidas no cuentan.
- Los avisos por umbral se emiten una vez por episodio o hito.
- Cada cifra indica si viene de seguimiento simulado o de un modelo de vídeo.
- Se usan las observaciones de visión de Persona 1 tal como las entrega, sin inventar identidad.

**Requisitos relacionados:** RF-11, RF-12 y la sugerencia del reto de indicadores de velocidad y distancia por umbral.

### EA-US-11 · Presentar la analítica en un tablero

**Como** equipo,
**quiero** un tablero que reproduzca el partido con lo que calcula el motor,
**para** presentar avances sin depender de la interfaz final.

**Prioridad:** P1. **Estado:** verificada localmente. **Evidencia:** [EA-US-11](evidencias/EA-US-11.md).

**Criterios de aceptación:**

- Todas las cifras, momentos y motivos salen del motor real.
- Lo simulado (posiciones y frases) está marcado en la página.
- El archivo se regenera desde el código y una prueba detecta si quedó viejo.

### EA-US-12 · Desplegar la analítica en Azure con datos ficticios en Supabase

**Como** equipo,
**quiero** que la API use la analítica real con partidos guardados en una base y que un script despliegue todo en Azure,
**para** dejar de depender de adaptadores provisionales y mostrar el flujo completo en la nube.

**Prioridad:** P1. **Estado:** verificada en local y en Azure; falta probar el flujo continuo en Azure. **Evidencia:** [EA-US-12](evidencias/EA-US-12.md).

**Criterios de aceptación:**

- La API responde con el motor de Persona 2 y los contratos de Persona 4; sin variables se comporta como antes.
- Los partidos, eventos y observaciones se guardan y se leen iguales a sus contratos.
- La carga de datos se puede repetir sin duplicar y todo lo simulado lleva su origen.
- Un script despliega Event Hubs, Storage, el registro, la identidad y las Container Apps, sin escribir la cadena de la base en la línea de comandos.
- Otro script apaga o borra el despliegue para cuidar los créditos.

### EA-US-13 · Explicar un momento con datos en el resumen

**Como** aficionado o analista,
**quiero** ver por qué un momento es importante y comparar alternativas con cifras medidas,
**para** entender la jugada sin depender de un texto genérico.

**Prioridad:** P1. **Estado:** verificada localmente. **Evidencia:** [EA-US-13](evidencias/EA-US-13.md).

**Criterios de aceptación:**

- El resumen muestra la prioridad, los motivos con sus puntos y los hechos con unidades del momento.
- La cancha usa las posiciones reales del instante y marca a los jugadores de la alternativa elegida.
- Cada alternativa del laboratorio muestra el valor real y el alternativo, o explica por qué no aplica.
- Todo usa solo eventos ocurridos hasta el momento y declara el origen de las posiciones.
