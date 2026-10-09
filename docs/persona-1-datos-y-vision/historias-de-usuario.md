# Historias de usuario de datos, visión e ingesta

Las personas usuarias de este módulo son principalmente integrantes técnicos que producen o consumen eventos. Las historias no implican que todas las capacidades ya estén implementadas.

## Épica A: partido sintético reproducible

### DV-US-01 · Generar el partido de aceptación

**Como** integrante del equipo,
**quiero** generar el mismo partido sintético a partir de una semilla,
**para** comparar resultados y repetir la demo.

**Prioridad:** P0.

**Estado:** implementada y verificada localmente con Python 3.12.

**Evidencia:** [informe técnico de DV-US-01](evidencias/DV-US-01.md), generador en `apps/backend/src/match_intelligence/adapters/sources/synthetic.py`, contratos con `StrEnum` en `apps/backend/src/match_intelligence/domain/contracts.py` y pruebas en `apps/backend/tests/test_synthetic_match.py`.

**Criterios de aceptación:**

- Dada la misma configuración y semilla, dos ejecuciones producen los mismos metadatos, eventos e identificadores.
- El partido contiene todos los tipos de evento exigidos por RF-02.
- El partido contiene una secuencia de control, una transición y un momento decisivo.
- El conjunto no contiene datos reales de partidos de la Premier League.

**Requisitos relacionados:** DV-RF-01 a DV-RF-03.

### DV-US-02 · Reproducir el flujo

**Como** desarrollador de analítica,
**quiero** recibir los eventos progresivamente,
**para** construir y probar el estado del partido sin esperar al detector de vídeo.

**Prioridad:** P0.

**Estado:** implementada y verificada localmente con Python 3.12.

**Evidencia:** [informe técnico de DV-US-02](evidencias/DV-US-02.md), reproductor en `apps/backend/src/match_intelligence/application/replay.py`, publicador local en `apps/backend/src/match_intelligence/adapters/messaging/memory.py` y pruebas en `apps/backend/tests/test_match_replay.py`.

**Criterios de aceptación:**

- Se puede iniciar, pausar, reiniciar y acelerar la reproducción.
- Cambiar la velocidad no modifica el contenido ni el orden lógico de los eventos.
- La reproducción local no necesita una cuenta de Azure.

**Requisitos relacionados:** DV-RF-09 y DV-RF-11.

## Épica B: calidad de ingesta

### DV-US-03 · Recibir únicamente eventos válidos

**Como** consumidor del flujo,
**quiero** que los eventos sean validados antes de procesarlos,
**para** no construir estadísticas sobre datos incompletos.

**Prioridad:** P0.

**Estado:** implementada y verificada localmente con Python 3.12.

**Evidencia:** [informe técnico de DV-US-03](evidencias/DV-US-03.md), validador en `apps/backend/src/match_intelligence/application/validation.py`, endpoint por lotes en `apps/backend/src/match_intelligence/adapters/http/router.py` y pruebas en `apps/backend/tests/test_event_validation.py`.

**Criterios de aceptación:**

- Un evento válido se entrega sin cambiar sus identificadores ni tiempos.
- Un evento sin un campo obligatorio se rechaza con un motivo estructurado.
- La presencia de un evento inválido no impide procesar los eventos válidos posteriores.

**Requisitos relacionados:** DV-RF-04, DV-RF-05 y DV-RF-07.

### DV-US-04 · Evitar el doble conteo

**Como** desarrollador del estado del partido,
**quiero** que los reintentos no dupliquen un evento,
**para** conservar cifras correctas.

**Prioridad:** P0.

**Estado:** implementada y verificada localmente para el núcleo y el transporte en memoria. La integración real con Event Hubs queda pendiente de DV-US-07.

**Evidencia:** [informe técnico de DV-US-04](evidencias/DV-US-04.md), deduplicador en `apps/backend/src/match_intelligence/application/deduplication.py`, consumidor local en `apps/backend/src/match_intelligence/adapters/messaging/memory.py` y pruebas en `apps/backend/tests/test_event_deduplication.py`.

**Criterios de aceptación:**

- Dos mensajes con el mismo `match_id` y `event_id` producen un solo evento aceptado.
- El duplicado queda registrado para diagnóstico.
- La regla funciona tanto con transporte local como con Event Hubs.

**Requisitos relacionados:** DV-RF-06, DV-RF-11 y DV-RF-13.

### DV-US-05 · Reconocer un evento tardío

**Como** desarrollador de analítica,
**quiero** conocer cuándo un evento llegó fuera de orden,
**para** aplicar la política de reconstrucción acordada.

**Prioridad:** P1.

**Estado:** detección y registro verificados localmente. La política provisional reenvía el evento marcado sin reordenarlo; falta acordar con Persona 2 cómo reconstruir el estado.

**Evidencia:** [informe técnico de DV-US-05](evidencias/DV-US-05.md), seguimiento de orden en `apps/backend/src/match_intelligence/application/event_order.py` y pruebas en `apps/backend/tests/test_event_order.py`.

**Criterios de aceptación:**

- El sistema detecta que el reloj del evento es anterior al último evento procesado.
- El evento no se descarta silenciosamente.
- El comportamiento coincide con la política acordada con Persona 2.

**Requisitos relacionados:** DV-RF-08.

## Épica C: infraestructura Azure repetible

### DV-US-06 · Desplegar recursos en una cuenta propia

**Como** integrante del equipo,
**quiero** desplegar la infraestructura desde comandos usando mi suscripción,
**para** reproducir la integración sin depender de la cuenta de otra persona.

**Prioridad:** P0.

**Criterios de aceptación:**

- El integrante inicia sesión con Azure CLI y selecciona explícitamente su suscripción.
- Puede previsualizar cambios antes de desplegar.
- Puede suministrar grupo, región y prefijo sin editar la plantilla Bicep.
- El despliegue crea Event Hubs y Blob Storage.
- Dos prefijos distintos no generan nombres incompatibles entre sí.
- Ninguna credencial personal se guarda en Git.

**Requisitos relacionados:** DV-RF-15, DV-RF-16, DV-RNF-04 y DV-RNF-05.

### DV-US-07 · Publicar eventos en Event Hubs

**Como** integrador del backend,
**quiero** consumir eventos desde Azure Event Hubs,
**para** probar el recorrido distribuido de la demo.

**Prioridad:** P0.

**Criterios de aceptación:**

- El productor publica el sobre de transporte documentado.
- El consumidor recupera la carga `MatchEvent 1.0` sin alterar sus valores.
- Los errores de publicación son visibles.
- Los reintentos no causan doble conteo.
- Se registran tiempos suficientes para medir la latencia del transporte.

**Requisitos relacionados:** DV-RF-12, DV-RF-13, DV-RNF-06 y DV-RNF-07.

### DV-US-08 · Cambiar entre transporte local y Azure

**Como** desarrollador,
**quiero** seleccionar el transporte mediante configuración,
**para** trabajar sin nube y ejecutar la integración sin cambiar el dominio.

**Prioridad:** P0.

**Criterios de aceptación:**

- La misma secuencia puede publicarse en memoria o en Event Hubs.
- El generador no importa directamente el SDK de Azure.
- Los consumidores reciben objetos equivalentes en ambos modos.

**Requisitos relacionados:** DV-RF-11 a DV-RF-13 y DV-RNF-02.

### DV-US-09 · Conservar artefactos autorizados

**Como** responsable de datos,
**quiero** guardar partidos, vídeos autorizados y observaciones en Blob Storage,
**para** repetir las pruebas y revisar su procedencia.

**Prioridad:** P1.

**Criterios de aceptación:**

- Cada tipo de artefacto se guarda en el contenedor definido.
- El nombre o metadato permite relacionarlo con el partido y su origen.
- Se puede recuperar el mismo contenido.
- Los datos reales de la Premier League no forman parte de los artefactos entregados.

**Requisitos relacionados:** DV-RF-14 y DV-RNF-03.

## Épica D: sincronización y percepción experimental

### DV-US-10 · Sincronizar eventos con vídeo

**Como** desarrollador del reproductor,
**quiero** recibir eventos asociados al tiempo del vídeo,
**para** mostrar información del momento correcto.

**Prioridad:** P0.

**Criterios de aceptación:**

- Cada evento sincronizado conserva reloj de partido y tiempo de vídeo.
- Al pausar no se emiten eventos futuros.
- Al adelantar se reconstruye la posición sin mostrar mensajes de un tramo incorrecto.
- El tiempo de vídeo no se presenta como prueba de detección automática.

**Requisitos relacionados:** DV-RF-05 y DV-RF-10.

### DV-US-11 · Evaluar modelos sin comprometer el MVP

**Como** responsable de visión,
**quiero** comparar Roboflow Sports y SoccerNet contra una muestra manual,
**para** decidir con evidencia si deben entrar en la demo.

**Prioridad:** P2.

**Criterios de aceptación:**

- El vídeo utilizado tiene permiso documentado.
- Se registran modelo, versión, clases y configuración.
- Se informa calidad y tiempo de procesamiento por separado.
- Se documentan falsos positivos y acciones no detectadas.
- Un resultado insuficiente no bloquea el flujo sintético.

**Requisitos relacionados:** DV-RF-17 y DV-RF-18.

### DV-US-12 · No inventar identidad de jugadores

**Como** revisor de los datos,
**quiero** distinguir un seguimiento visual de una identidad confirmada,
**para** evitar atribuir acciones al jugador equivocado.

**Prioridad:** P2.

**Criterios de aceptación:**

- Una detección sin asociación comprobada conserva `track_id` y omite `player_id`.
- La confianza del detector no se usa como prueba de identidad nominal.
- La regla queda cubierta por al menos una prueba negativa.

**Requisitos relacionados:** DV-RF-20.

### DV-US-13 · Fusionar observaciones con trazabilidad

**Como** consumidor de eventos de vídeo,
**quiero** conocer las observaciones que originaron un evento fusionado,
**para** revisar una asociación dudosa.

**Prioridad:** P2.

**Criterios de aceptación:**

- La fusión aplica tolerancias temporales y espaciales documentadas.
- Las observaciones originales permanecen disponibles.
- Una contradicción no produce un hecho con certeza falsa.
- Cuando no hay evidencia suficiente, no se emite el evento o se marca la limitación acordada.

**Requisitos relacionados:** DV-RF-19 y DV-RNF-03.

## Orden sugerido del backlog

1. DV-US-01: partido sintético.
2. DV-US-03: validación.
3. DV-US-04: deduplicación.
4. DV-US-02: reproducción local.
5. DV-US-06: infraestructura Azure.
6. DV-US-08: adaptadores intercambiables.
7. DV-US-07: integración con Event Hubs.
8. DV-US-10: sincronización con vídeo.
9. DV-US-05: política de eventos tardíos.
10. DV-US-09: Blob Storage.
11. DV-US-11: evaluación de visión.
12. DV-US-12: identidad visual.
13. DV-US-13: fusión experimental.
