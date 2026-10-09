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

**Estado:** implementada y verificada localmente mediante compilación de Bicep. El despliegue, `what-if` y la prueba con dos suscripciones o prefijos están pendientes de una cuenta Azure autenticada.

**Evidencia:** [informe técnico de DV-US-06](evidencias/DV-US-06.md), plantilla y guía en `infra/azure/`, y pruebas de contrato en `apps/backend/tests/test_azure_infrastructure.py`.

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

**Estado:** productor, consumidor, sobre, diagnósticos y prueba de ida y vuelta implementados y verificados localmente con dobles del SDK. La ejecución contra Azure está pendiente de recursos desplegados y roles RBAC.

**Evidencia:** [informe técnico de DV-US-07](evidencias/DV-US-07.md), contrato en `apps/backend/src/match_intelligence/application/transport.py`, adaptadores en `apps/backend/src/match_intelligence/adapters/messaging/azure_event_hubs.py`, prueba manual en `apps/backend/scripts/event_hubs_smoke.py` y pruebas automatizadas en `apps/backend/tests/test_azure_event_hubs.py`.

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

**Estado:** implementada y verificada localmente mediante configuración y dobles de Event Hubs. El cambio contra un servicio Azure real queda pendiente del despliegue y RBAC de DV-US-06 y DV-US-07.

**Evidencia:** [informe técnico de DV-US-08](evidencias/DV-US-08.md), configuración y fábricas en `apps/backend/src/match_intelligence/adapters/messaging/configuration.py`, ejemplo en `apps/backend/.env.example` y pruebas en `apps/backend/tests/test_transport_configuration.py`.

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

**Estado:** implementada y verificada localmente con dobles del SDK. La carga y recuperación en una cuenta Azure real quedan pendientes del despliegue y de RBAC.

**Evidencia:** [informe técnico de DV-US-09](evidencias/DV-US-09.md), contrato en `apps/backend/src/match_intelligence/application/artifacts.py`, adaptador en `apps/backend/src/match_intelligence/adapters/storage/azure_blob.py`, prueba manual en `apps/backend/scripts/blob_storage_smoke.py` y pruebas automatizadas en `apps/backend/tests/test_azure_blob_storage.py`.

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

**Estado:** sincronización por posición, pausa, salto y reinicio implementados y verificados localmente con eventos sintéticos. La integración con el reproductor visual y un vídeo permitido queda pendiente.

**Evidencia:** [informe técnico de DV-US-10](evidencias/DV-US-10.md), coordinador en `apps/backend/src/match_intelligence/application/video_sync.py` y pruebas en `apps/backend/tests/test_video_sync.py`.

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

**Estado:** evaluador, contrato y comando reproducible implementados y verificados localmente. La historia sigue en progreso porque aún no se seleccionó un vídeo autorizado ni se ejecutaron versiones fijadas de Roboflow Sports y SoccerNet.

**Evidencia:** [informe técnico de DV-US-11](evidencias/DV-US-11.md), evaluador en `apps/backend/src/match_intelligence/application/vision_evaluation.py`, comando en `apps/backend/scripts/evaluate_vision_predictions.py`, guía en `docs/persona-1-datos-y-vision/experimentos-vision/` y pruebas en `apps/backend/tests/test_vision_evaluation.py`.

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

**Estado:** regla de identidad visual implementada y verificada localmente. La asociación real mediante revisión o mapeo externo sigue pendiente de un vídeo y evidencia reales.

**Evidencia:** [informe técnico de DV-US-12](evidencias/DV-US-12.md), contratos y resolvedor en `apps/backend/src/match_intelligence/application/visual_identity.py`, y pruebas en `apps/backend/tests/test_visual_identity.py`.

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

**Estado:** política y servicio de fusión implementados y verificados localmente con observaciones sintéticas. La ejecución con salidas reales de vídeo queda pendiente de DV-US-11.

**Evidencia:** [informe técnico de DV-US-13](evidencias/DV-US-13.md), fusión en `apps/backend/src/match_intelligence/application/observation_fusion.py` y pruebas en `apps/backend/tests/test_observation_fusion.py`.

**Criterios de aceptación:**

- La fusión aplica tolerancias temporales y espaciales documentadas.
- Las observaciones originales permanecen disponibles.
- Una contradicción no produce un hecho con certeza falsa.
- Cuando no hay evidencia suficiente, no se emite el evento o se marca la limitación acordada.

**Requisitos relacionados:** DV-RF-19 y DV-RNF-03.

## Épica E: pruebas con servicios y medios reales

Estas historias no reemplazan las pruebas locales. Elevan una capacidad desde “verificada localmente” hasta “verificada en integración” usando recursos desplegados, un medio permitido o ejecuciones reales de modelos. El orden operativo está en [plan de pruebas con servicios reales](plan-pruebas-servicios-reales.md).

### DV-US-14 · Desplegar y autorizar el entorno real

**Como** responsable de integración,
**quiero** desplegar Bicep en una suscripción seleccionada y asignar los roles mínimos,
**para** probar Event Hubs y Blob Storage con identidad real.

**Prioridad:** P0.

**Estado:** pendiente.

**Criterios de aceptación:**

- La cuenta y suscripción activas se comprueban antes de desplegar.
- `validate` y `what-if` terminan correctamente y se revisan antes de `create`.
- Event Hubs, Storage y los tres contenedores existen en Azure.
- La identidad de prueba tiene `Azure Event Hubs Data Owner` y `Storage Blob Data Contributor` en el alcance acordado.
- Las salidas se registran sin tokens, claves, cadenas de conexión, identificadores personales ni datos sin anonimizar.
- Se documentan región, prefijo, versiones de Azure CLI y Bicep, costo esperado y procedimiento de eliminación.

**Dependencias:** acceso a una suscripción, permiso para desplegar y asignar roles.

**Eleva:** DV-US-06.

### DV-US-15 · Probar Event Hubs de extremo a extremo

**Como** integrador del backend,
**quiero** publicar y consumir el partido sintético mediante el Event Hub desplegado,
**para** comprobar transporte, idempotencia y latencia reales.

**Prioridad:** P0.

**Estado:** pendiente.

**Criterios de aceptación:**

- La prueba usa `DefaultAzureCredential`, sin cadenas de conexión.
- Un evento publicado se recupera sin cambiar `MatchEvent 1.0`.
- Publicar dos veces el mismo evento produce un aceptado y un duplicado registrado.
- Se guardan tiempos de producción, publicación y recepción, además de latencia calculada.
- Un fallo de permisos o red aparece como error observable y no altera el evento original.
- La misma muestra continúa funcionando con `EVENT_TRANSPORT=memory` después de la prueba.

**Dependencias:** DV-US-14 y propagación de RBAC.

**Eleva:** DV-US-04, DV-US-07 y DV-US-08.

### DV-US-16 · Probar Blob Storage de extremo a extremo

**Como** responsable de datos,
**quiero** cargar y recuperar artefactos sintéticos en la cuenta real,
**para** comprobar contenedores, procedencia e integridad.

**Prioridad:** P0.

**Estado:** pendiente.

**Criterios de aceptación:**

- Un partido sintético llega a `matches` con nombre y metadatos trazables.
- Una observación experimental llega a `observations`.
- `authorized-videos` solo se prueba cuando exista un vídeo con permiso documentado.
- La descarga conserva exactamente los bytes y el SHA-256.
- Intentar sobrescribir el mismo identificador falla de forma visible.
- Ningún artefacto de prueba contiene datos reales de la Premier League.

**Dependencias:** DV-US-14; DV-US-17 para probar el contenedor de vídeos.

**Eleva:** DV-US-09.

### DV-US-17 · Preparar el paquete de vídeo permitido

**Como** responsable de la muestra,
**quiero** registrar un vídeo propio, generado o autorizado y su anotación manual,
**para** ejecutar sincronización y visión con una referencia válida.

**Prioridad:** P0.

**Estado:** pendiente.

**Criterios de aceptación:**

- La base del permiso y su referencia comprobable están documentadas.
- Se registran SHA-256, duración, resolución, FPS y origen sin confirmar el vídeo si no puede redistribuirse.
- Existe una tabla manual con tiempos, clases y cajas necesarias para las pruebas seleccionadas.
- El archivo no contiene datos reales de la Premier League salvo autorización explícita compatible con el proyecto.
- Se define si el archivo puede entrar en Git, Blob privado o solo mantenerse local.

**Dependencias:** decisión humana sobre material y licencia.

**Eleva:** DV-US-10 y habilita DV-US-11 a DV-US-13.

### DV-US-18 · Validar sincronización mediante una interfaz mínima

**Como** revisor de integración,
**quiero** reproducir el vídeo y ver los eventos asociados en una página de diagnóstico,
**para** comprobar visualmente pausa, salto, reinicio y tramo activo.

**Prioridad:** P0.

**Estado:** pendiente; historia compartida con Persona 4.

**Criterios de aceptación:**

- La página usa un vídeo permitido y muestra `currentTime`, `clock_ms`, `video_time_ms`, `event_id` y procedencia.
- Pausar impide que aparezcan eventos futuros.
- Saltar hacia adelante o atrás reconstruye el estado sin mostrar mensajes históricos como nuevos.
- Reiniciar vuelve a cero sin conservar mensajes del tramo anterior.
- La interfaz diferencia alineación suministrada de detección automática.
- Se conserva una grabación o secuencia de capturas y un registro JSON sin datos sensibles.

**Dependencias:** DV-US-17, API de integración de Persona 4 y `VideoSynchronizedReplay` de DV-US-10.

**Eleva:** DV-US-10.

### DV-US-19 · Ejecutar Roboflow Sports sobre la muestra

**Como** responsable de visión,
**quiero** ejecutar una revisión fijada de Roboflow Sports sobre el vídeo permitido,
**para** medir detección espacial y seguimiento con nuestro material.

**Prioridad:** P2.

**Estado:** pendiente.

**Criterios de aceptación:**

- Se fijan commit, modelos, pesos, clases, dispositivo y parámetros.
- Se revisan y registran licencias de código, pesos y datos.
- Las predicciones reales se exportan con `prediction_origin=actual_model`.
- El evaluador informa calidad espacial, tiempo, falsos positivos y omisiones.
- Se revisan al menos un falso positivo y una omisión con evidencia visual.
- El resultado produce `candidate` o `rejected`, nunca integración automática.

**Dependencias:** DV-US-17, hardware suficiente y descargas autorizadas.

**Eleva:** la parte espacial de DV-US-11.

### DV-US-20 · Ejecutar SoccerNet sobre la muestra

**Como** responsable de visión,
**quiero** ejecutar una revisión fijada de SoccerNet Team Ball Action Spotting,
**para** medir detección temporal de acciones con nuestro material.

**Prioridad:** P2.

**Estado:** pendiente.

**Criterios de aceptación:**

- Se fijan commit, checkpoint, clases, dispositivo, preprocesamiento y parámetros.
- Se revisan y registran licencias de código, pesos, dataset y condiciones del vídeo.
- Las predicciones reales se exportan con `prediction_origin=actual_model`.
- El evaluador informa calidad temporal, tiempo, falsos positivos y acciones omitidas.
- Se revisan al menos un falso positivo y una omisión con su instante de vídeo.
- El resultado produce `candidate` o `rejected` sin bloquear el partido sintético.

**Dependencias:** DV-US-17, hardware suficiente y acceso permitido a pesos y herramientas.

**Eleva:** la parte temporal de DV-US-11.

### DV-US-21 · Calibrar identidad y fusión con observaciones reales

**Como** revisor de datos,
**quiero** aplicar las reglas de identidad y fusión a exportaciones reales,
**para** decidir tolerancias sin crear certeza falsa.

**Prioridad:** P2.

**Estado:** pendiente.

**Criterios de aceptación:**

- Las tolerancias temporal y espacial se justifican con FPS, error observado y ejemplos manuales.
- Una observación sin evidencia nominal conserva `track_id` y omite `player_id`.
- Cada evento fusionado conserva las observaciones de acción, seguimiento e identidad usadas.
- Casos contradictorios y sin evidencia no producen `MatchEvent`.
- Se documentan aciertos, falsos emparejamientos y casos no fusionados.
- El flujo sintético sigue operativo aunque ningún modelo resulte candidato.

**Dependencias:** DV-US-19 y DV-US-20 cuando estén disponibles; DV-US-12 y DV-US-13.

**Eleva:** DV-US-12 y DV-US-13.

### DV-US-22 · Ejecutar el ensayo de aceptación integrado

**Como** equipo de la demo,
**quiero** repetir un recorrido documentado desde un entorno limpio,
**para** conocer qué está realmente listo y qué debe permanecer como experimento.

**Prioridad:** P0.

**Estado:** pendiente.

**Criterios de aceptación:**

- Las 134 pruebas locales continúan aprobadas o se registra justificadamente el nuevo total.
- Se ejecutan las pruebas reales habilitadas de Azure, vídeo y modelos en el orden documentado.
- Cada historia conserva evidencia anonimizada, versiones, comandos, resultados y limitaciones.
- Se prueba al menos un fallo controlado de permisos, red o modelo sin detener el modo local.
- Se registra costo, duración, recursos creados y decisión de conservar o eliminar Azure.
- El informe final separa `verificada localmente`, `verificada en integración`, `rechazada` y `pendiente`.

**Dependencias:** DV-US-14 a DV-US-21 según el alcance confirmado para la demo.

**Eleva:** el módulo completo de Persona 1.

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
14. DV-US-14: despliegue y RBAC reales.
15. DV-US-15: Event Hubs real.
16. DV-US-16: Blob Storage real.
17. DV-US-17: vídeo y anotación permitidos.
18. DV-US-18: interfaz mínima de sincronización.
19. DV-US-19: experimento real de Roboflow Sports.
20. DV-US-20: experimento real de SoccerNet.
21. DV-US-21: calibración de identidad y fusión.
22. DV-US-22: ensayo integrado y cierre de evidencias.
