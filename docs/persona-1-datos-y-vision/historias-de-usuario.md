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

**Estado:** verificada en una cuenta Azure mediante DV-US-14. `validate`, `what-if` y el despliegue incremental aprobaron con parámetros externos a la plantilla. La prueba adicional con dos suscripciones o prefijos sigue siendo opcional y no se ejecutó.

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

**Estado:** verificada en integración mediante DV-US-15. La ida y vuelta real aceptó un evento, detectó su duplicado y terminó sin rechazos ni fallos.

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

**Estado:** verificada en integración mediante DV-US-15. Event Hubs real aprobó y el transporte en memoria mantuvo sus pruebas después de la ejecución.

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

**Estado:** verificada en integración mediante DV-US-16 para artefactos sintéticos y observaciones experimentales. `authorized-videos` continúa condicionado a un vídeo permitido en DV-US-17.

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

**Estado:** verificada en integración el 13 de octubre de 2026. El despliegue incremental terminó en `Succeeded`, los recursos se comprobaron y un principal temporal recibió únicamente los dos roles de datos en los alcances de recurso.

**Evidencia:** [informe técnico de DV-US-14](evidencias/DV-US-14.md).

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

**Estado:** verificada en integración el 13 de octubre de 2026. La prueba real publicó dos mensajes, aceptó uno, registró un duplicado y terminó sin rechazos ni fallos; el transporte en memoria continuó aprobando sus pruebas.

**Evidencia:** [informe técnico de DV-US-15](evidencias/DV-US-15.md).

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

**Estado:** verificada en integración el 13 de octubre de 2026. `matches` y `observations` conservaron bytes y SHA-256; una segunda carga fue rechazada con `ResourceExistsError` y no alteró el original. No se probó `authorized-videos` sin permiso.

**Evidencia:** [informe técnico de DV-US-16](evidencias/DV-US-16.md).

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

**Estado:** verificada localmente el 13 de octubre de 2026. Se generó e inspeccionó un MP4 sintético de 30 segundos, se verificaron sus metadatos e integridad y se creó una anotación manual mínima del balón.

**Evidencia:** [informe técnico de DV-US-17](evidencias/DV-US-17.md).

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

**Estado:** implementada y verificada automáticamente en una herramienta aislada, sin modificar el frontend oficial. Falta ejecutar el recorrido visual en navegador, exportar el registro y conservar las capturas antes de marcarla verificada en integración.

**Evidencia:** [informe técnico de DV-US-18](evidencias/DV-US-18.md).

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

**Estado:** verificada localmente como experimento; el modelo fue `rejected` para integración con esta muestra y configuración. Procesó los 300 cuadros, exportó seis predicciones reales y el evaluador registró F1 0,00 y factor de tiempo real 13,81 en CPU.

**Evidencia:** [informe técnico de DV-US-19](evidencias/DV-US-19.md).

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

**Estado:** verificada experimentalmente en CPU y GPU sobre vídeo permitido. La RTX 3060 Laptop de 6 GB produjo 127 observaciones en 5,66 segundos; la calidad sigue pendiente de anotaciones manuales completas.

**Evidencia:** [informe técnico de DV-US-20](evidencias/DV-US-20.md).

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

**Estado:** verificada experimentalmente con vídeo permitido; un candidato revisable, ningún `MatchEvent` publicado.

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

**Estado:** verificada en integración; aceptación local, Azure, vídeo, modelos, fusión y fallo controlado comprobados.

**Criterios de aceptación:**

- Las 134 pruebas locales continúan aprobadas o se registra justificadamente el nuevo total.
- Se ejecutan las pruebas reales habilitadas de Azure, vídeo y modelos en el orden documentado.
- Cada historia conserva evidencia anonimizada, versiones, comandos, resultados y limitaciones.
- Se prueba al menos un fallo controlado de permisos, red o modelo sin detener el modo local.
- Se registra costo, duración, recursos creados y decisión de conservar o eliminar Azure.
- El informe final separa `verificada localmente`, `verificada en integración`, `rechazada` y `pendiente`.

**Dependencias:** DV-US-14 a DV-US-21 según el alcance confirmado para la demo.

**Eleva:** el módulo completo de Persona 1.

### DV-US-23 · Integrar el pipeline en el backend oficial

**Como** integrante del equipo,
**quiero** consultar vídeo, observaciones y candidatos desde una sola API,
**para** validar datos y visión sin ejecutar scripts inconexos ni modificar el frontend de producto.

**Prioridad:** P0.

**Estado:** backend oficial verificado localmente mediante un recorrido HTTP
consolidado; el contenedor Compose y el frontend permanecen fuera de esta
prueba.

**Criterios de aceptación:**

- El backend oficial expone el estado de Roboflow, SoccerNet y fusión.
- Una ventana temporal devuelve detecciones, acciones y candidatos del mismo medio.
- Los candidatos conservan fuentes, `track_id` y ausencia de `player_id`.
- Ningún candidato se presenta ni publica como `MatchEvent`.
- La interfaz técnica consume la API oficial y se sincroniza con el vídeo permitido.
- El equipo puede iniciar la integración directamente o mediante Compose sin incorporar vídeo, resultados o secretos a la imagen.

**Ejecución consolidada:** `experiments/run-backend-integration.sh` procesa el
vídeo, recalcula la fusión, ejecuta las pruebas, inicia FastAPI, consulta los
endpoints reales y prepara evidencia. La guía se encuentra en la
[guía de integración del backend](guia-integracion-backend.md).

**Dependencias:** DV-US-18 a DV-US-22.

**Eleva:** el backend oficial de Persona 1 y el contrato para cualquier frontend.

### DV-US-24 · Transportar observaciones durante la transmisión

**Como** equipo de la transmisión,
**quiero** que los workers publiquen observaciones conforme procesan el vídeo,
**para** consumirlas, fusionarlas y mostrarlas aunque el procesamiento tenga retraso.

**Prioridad:** P0.

**Estado:** implementada y verificada localmente; infraestructura Azure desplegada y prueba de datos pendiente con la identidad autorizada.

**Criterios de aceptación:**

- `match-events` conserva únicamente hechos deportivos y `vision-observations` recibe resultados de percepción.
- El transporte cambia entre memoria y Azure mediante configuración.
- El consumidor valida, deduplica y conserva origen, tiempo, `track_id` y ausencia de identidad nominal.
- Una cola acotada evita que un navegador lento detenga al productor.
- El backend entrega al frontend por WebSocket después del transporte.
- Roboflow puede publicar cada detección al terminar el cuadro y registra su retraso respecto al vídeo.
- Una prueba real publica, consume y deduplica sin producir `MatchEvent`.

**Dependencias:** DV-US-15, DV-US-19, DV-US-20 y DV-US-23.

**Eleva:** el pipeline continuo de visión; no garantiza latencia de tiempo real en CPU.

### DV-US-25 · Controlar observaciones con la reproducción

**Como** revisor de la integración,
**quiero** iniciar, pausar y reposicionar la reproducción de observaciones desde el vídeo,
**para** comprobar el canal sin recibir resultados antes de comenzar el partido.

**Prioridad:** P0.

**Estado:** implementada y verificada localmente; recorrido visual con Compose pendiente.

**Criterios de aceptación:**

- Antes de pulsar Play no se publica ninguna observación precomputada.
- Pause impide publicar observaciones futuras y conserva la posición.
- Un salto mueve el cursor sin presentar el historial como observaciones nuevas.
- Reiniciar vuelve a cero, pausa la sesión y limpia la vista en vivo.
- La publicación conserva el transporte configurado: memoria o Event Hubs.
- El WebSocket continúa siendo únicamente la salida del backend hacia el navegador.

**Dependencias:** DV-US-18, DV-US-23 y DV-US-24.

**Eleva:** la validación reproducible del pipeline integrado.

### DV-US-26 · Ampliar la percepción espacial de fútbol

**Como** responsable de visión,
**quiero** ejecutar los tres pesos oficiales de fútbol de Roboflow Sports en CPU o GPU,
**para** detectar participantes, seguir trayectorias, localizar el balón y obtener puntos clave del campo.

**Prioridad:** P1.

**Estado:** verificada operativamente en una RTX 3060 Laptop de 6 GB. Los tres pesos procesaron 750 cuadros; la calidad y estabilidad de tracking siguen pendientes de anotaciones manuales.

**Evidencia:** [informe técnico de DV-US-26](evidencias/DV-US-26.md).

**Criterios de aceptación:**

- La imagen contiene los pesos oficiales de participantes, balón y campo fijados por identificador.
- Cada observación conserva modelo, cuadro, tiempo, confianza y procedencia.
- Las cajas de participantes usan ByteTrack sin inventar `player_id`.
- Los puntos del campo se exportan separados de las cajas y pueden viajar por el canal de observaciones.
- La ejecución automática conserva CPU y admite una GPU NVIDIA seleccionable con media precisión configurable.
- La evidencia distingue pesos ejecutables, datasets de entrenamiento y etapas compuestas todavía no integradas.

**Dependencias:** DV-US-19, DV-US-24 y una GPU NVIDIA con Container Toolkit para la verificación acelerada.

**Eleva:** DV-US-19 y la entrada espacial del pipeline integrado.

### DV-US-27 · Evaluar SoccerNet Game State Reconstruction en GPU

**Como** responsable de visión,
**quiero** ejecutar el baseline oficial de Game State Reconstruction en un contenedor GPU aislado,
**para** medir tracking, reidentificación, equipo, dorsal, calibración y posición sobre el campo antes de integrarlos.

**Prioridad:** P2.

**Estado:** implementada y ajustada para 6 GB, pendiente de ejecución. La primera prueba se omitió por una interpretación restrictiva del dataset; la documentación oficial confirma descarga automática de datos y pesos.

**Evidencia:** [informe técnico de DV-US-27](evidencias/DV-US-27.md).

**Criterios de aceptación:**

- El repositorio, TrackLab, Python, PyTorch y CUDA quedan fijados.
- El baseline corre en un contenedor separado del backend Python 3.12.
- La ejecución valida CUDA antes de descargar o procesar datos.
- Dataset, pesos, estado de tracking y vídeo quedan fuera de Git.
- La primera prueba usa una sola secuencia pública y un límite de cuadros.
- Dorsal y equipo permanecen como observaciones; no crean `player_id` automáticamente.
- La evidencia diferencia el smoke oficial del futuro adaptador para el MP4 autorizado.

**Dependencias:** GPU NVIDIA, NVIDIA Container Toolkit, espacio de disco y acceso a los artefactos públicos de SoccerNet GSR.

**Eleva:** DV-US-12, DV-US-17 y la futura fusión espacial de DV-US-21.

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
23. DV-US-23: pipeline integrado en backend e interfaz técnica.
24. DV-US-24: transporte continuo de observaciones mediante Event Hubs.
25. DV-US-25: control de observaciones mediante el reproductor de diagnóstico.
26. DV-US-26: suite espacial de Roboflow Sports en CPU o GPU.
27. DV-US-27: SoccerNet Game State Reconstruction aislado en GPU.

### DV-US-28 · Integrar visión con la aplicación oficial

**Como** integrante del equipo,
**quiero** usar las salidas de visión desde el backend y frontend oficiales,
**para** validar una sola experiencia sin mantener una interfaz paralela.

**Prioridad:** P0.

**Estado:** implementada en rama de integración y verificada para compilación del frontend y pruebas aisladas de Persona 1. La suite HTTP combinada y el transporte durable de eventos importantes siguen pendientes.

**Evidencia:** [informe técnico de DV-US-28](evidencias/DV-US-28.md).

**Criterios de aceptación:**

- El frontend oficial consulta las observaciones sincronizadas.
- Los controles de reproducción gobiernan también la reproducción de visión.
- La interfaz diferencia observaciones, candidatos y hechos confirmados.
- La falta de artefactos no interrumpe la experiencia sintética.

### DV-US-29 · Separar telemetría y eventos importantes

**Como** responsable del flujo en vivo,
**quiero** clasificar cada ventana después de conservar su ingreso y entregarla en un canal acorde con su criticidad,
**para** que una pérdida de telemetría no elimine una jugada importante ni llame agentes por cada evento.

**Prioridad:** P0.

**Estado:** verificada localmente. La topología en memoria, la API y la plantilla Bicep están comprobadas; el despliegue real de `match-metrics` y Service Bus queda pendiente de `what-if`, cuota, costo y RBAC.

**Evidencia:** [informe técnico de DV-US-29](evidencias/DV-US-29.md).

**Criterios de aceptación:**

- Toda ventana válida se publica primero en ingreso con `match_id` como clave de partición.
- Una decisión `metrics_only` se envía a telemetría reconstruible y nunca llama a los agentes.
- Las decisiones narrativas, de peligro, tiempo muerto o resumen usan una cola durable de importantes.
- Un fallo de métricas queda observable y no invalida el ingreso aceptado.
- Un fallo de importantes se propaga para permitir reintento; no se confirma silenciosamente.
- Los duplicados o inválidos se auditan mediante la decisión y no ocupan una cuarta cola.
- El botón de simulación del centro del partido recorre esta misma canalización.

**Dependencias:** RF-40, RF-41, RF-51, DV-US-28 y autorización de Azure para la verificación remota.

### DV-US-30 · Desplegar el primer detector en una GPU de Azure

**Como** responsable de visión,
**quiero** desplegar inicialmente un solo detector espacial en Azure Container Apps GPU,
**para** medir costo, memoria y latencia reales antes de incorporar los demás modelos.

**Prioridad:** P1.

**Estado:** implementada, pendiente de verificación en Azure. El servicio, la imagen y el script son comprobables localmente; falta cuota T4, construcción en ACR y prueba contra el endpoint real.

**Evidencia:** [informe técnico de DV-US-30](evidencias/DV-US-30.md).

**Criterios de aceptación:**

- La primera imagen incluye únicamente `football-player-detection.pt` y verifica su SHA-256.
- El modelo se carga una sola vez, realiza calentamiento CUDA y atiende solicitudes posteriores sin recargar los pesos.
- La API acepta JPEG, PNG o WebP, limita el tamaño y devuelve cajas normalizadas, clase, confianza y latencia.
- La predicción requiere una clave externa al repositorio; las sondas de salud no revelan secretos.
- ACR conserva la imagen de forma privada y Container Apps usa identidad administrada para descargarla.
- El perfil T4 usa mínimo cero, máximo uno y permite mínimo uno durante el partido.
- El script comprueba suscripción, región, perfil GPU y aceptación de las condiciones de los pesos antes de crear recursos.
- La documentación diferencia implementación local de verificación real en Azure.

**Dependencias:** DV-US-26, cuota para `Consumption-GPU-NC8as-T4` y revisión de licencias de los pesos.

### DV-US-31 · Preparar el despliegue de los modelos restantes

**Como** integrante del equipo,
**quiero** desplegar los modelos de visión restantes mediante comandos repetibles,
**para** probar cada API sin repetir los errores encontrados con el primer detector.

**Prioridad:** P1.

**Estado:** verificada en Azure para la suite Roboflow y TeamSpotting. Los
cuatro modelos procesaron la misma fuente autorizada de forma secuencial sobre
Tesla T4. GameState permanece pendiente y la cuota actual no permite ejecutar
dos aplicaciones GPU simultáneamente.

**Evidencia:** [informe técnico de DV-US-31](evidencias/DV-US-31.md).

**Criterios de aceptación:**

- Los recursos comunes reutilizan ACR, entorno y perfil T4 sin mezclar identidades de las APIs.
- La suite Roboflow verifica los tres pesos y permite seleccionar jugador, balón y campo.
- TeamSpotting acepta un clip MP4 acotado y devuelve candidatos temporales sin inventar identidad.
- Los scripts conservan escala 0–1, secretos externos, ACR privado y construcción local reanudable.
- Una huella del contenido evita desplegar una imagen anterior al trabajar desde un ZIP.
- GameState no crea recursos hasta completar su adaptador y verificación.
- La guía indica despliegue, prueba, evidencia y apagado para el equipo.

**Dependencias:** DV-US-20, DV-US-26, DV-US-27, DV-US-30 y cuota T4.

### DV-US-32 · Generar un catálogo de partidos sintéticos con MESSI

**Como** responsable de datos sintéticos,
**quiero** ejecutar MESSI como un trabajo GPU finito y almacenar sus repeticiones,
**para** disponer de varios partidos reproducibles sin generar vídeo durante la reproducción.

**Prioridad:** P1.

**Estado:** implementada y desplegada; la primera ejecución GPU detectó un fallo
nativo durante el rollout y la corrección queda pendiente de una prueba corta en Azure.

**Evidencia:** [informe técnico de DV-US-32](evidencias/DV-US-32.md).

**Criterios de aceptación:**

- El lote predeterminado genera 30 partidos sintéticos con semillas distintas y reproducibles.
- Cada partido produce MP4, eventos, tracking, metadatos y un manifiesto con hashes.
- El generador usa un Azure Container Apps Job sobre T4 y termina al completar el lote.
- La identidad administrada descarga la imagen privada y escribe en Blob Storage mediante RBAC.
- Los partidos completos se representan como vídeos tácticos comprimidos de tres minutos.
- Una ejecución repetida omite partidos cuyo manifiesto ya figura como completo.
- El contenedor de Storage es privado y la futura reproducción usará acceso temporal de lectura.
- La documentación distingue los datos estructurados de MESSI de una transmisión real.

**Dependencias:** DV-US-06, DV-US-09, cuota T4 y MESSI fijado a una revisión verificable.

### DV-US-33 · Adaptar un MP4 a SoccerNet GameState

**Como** responsable de visión,
**quiero** procesar un MP4 sintético o autorizado mediante el baseline GameState y normalizar su estado,
**para** entregar seguimiento, equipo, dorsal y posición al backend sin inventar identidades.

**Prioridad:** P2.

**Estado:** implementada y verificada localmente para adaptación y contratos; pendiente de inferencia GPU completa.

**Evidencia:** [informe técnico de DV-US-33](evidencias/DV-US-33.md).

**Criterios de aceptación:**

- El lanzador acepta un MP4 mediante el `ExternalVideo` incluido en TrackLab 1.3.24.
- El estado `.pklz` se exporta dentro del contenedor a JSONL sin obligar al backend Python 3.12 a cargar pickle.
- El adaptador produce `VisionObservation` y `TrackingFrame v1` con tiempos reproducibles desde cuadro y FPS.
- Equipo, dorsal y pista conservan su condición de estimaciones. `player_id` solo se completa
  cuando al menos tres lecturas válidas del mismo track alcanzan 70 % de acuerdo y la combinación
  equipo-dorsal corresponde a una sola persona de la plantilla verificada; los casos ambiguos
  permanecen vacíos. El backend exige un mapeo explícito de lados a equipos y la confirmación de
  que la plantilla corresponde al MP4; no deduce local/visitante a partir del cluster del modelo.
- Una fila sin calibración sigue disponible como observación, pero no produce una posición de seguimiento falsa.
- La historia no se marca como verificada en integración hasta completar una inferencia GPU sobre un MP4 permitido.

**Dependencias:** DV-US-12, DV-US-17, DV-US-27, GPU compatible y pesos oficiales de GameState.

### DV-US-34 · Ejecutar inferencia mientras se reproduce el vídeo

**Como** operador de The Prime Moment,
**quiero** que los modelos capturen el vídeo únicamente mientras está en reproducción,
**para** observar resultados nuevos sin procesar el partido cuando está pausado.

**Prioridad:** P0.

**Estado:** captura verificada localmente y topología Azure verificada; recorrido
visual con endpoint GPU, Blob Storage y WebSocket pendiente.

**Evidencia:** [informe técnico de DV-US-34](evidencias/DV-US-34.md).

**Criterios de aceptación:**

- El navegador obtiene el MP4 privado mediante el backend y conserva la cancha sintética como fallback.
- Play habilita la captura y Pause la detiene en frontend y backend.
- Se envía como máximo un fotograma por segundo y nunca se expone la clave del modelo al navegador.
- Una inferencia que termina después de Pause se descarta antes de publicar observaciones.
- Los tres modelos de la suite Roboflow se ejecutan sobre el mismo fotograma.
- Las detecciones se normalizan y publican en `vision-observations`.
- El consumidor entrega las observaciones al panel oficial mediante WebSocket.
- Los eventos deportivos fusionados conservan su separación posterior entre métricas e importantes.

**Dependencias:** DV-US-24, DV-US-29, DV-US-30, DV-US-31, vídeo MESSI completo y RBAC de Azure.

### DV-US-35 · Consumir eventos importantes con un worker

**Como** operador de The Prime Moment,
**quiero** que un worker retire de forma segura las decisiones importantes,
**para** reintentar fallos sin perder jugadas relevantes ni procesarlas dos veces.

**Prioridad:** P0.

**Estado:** transporte y despacho verificados en Azure; ejecutores de agentes pendientes.

**Evidencia:** [informe técnico de DV-US-35](evidencias/DV-US-35.md).

**Criterios de aceptación:**

- Valida `RoutingOutcome` antes de ejecutar trabajo.
- Completa éxitos y duplicados idempotentes.
- Abandona errores recuperables para permitir reintentos.
- Envía contratos inválidos a la cola muerta.
- Renueva el bloqueo durante tareas largas.
- Usa identidad de Azure sin cadenas de conexión.

**Dependencias:** DV-US-29, Service Bus y un ejecutor por cada tarea de agente.
