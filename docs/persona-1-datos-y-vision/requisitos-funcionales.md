# Requisitos funcionales de datos, visión e ingesta

## Convenciones

- `DV-RF`: requisito funcional de datos y visión.
- `DV-RNF`: requisito no funcional de esta parte.
- P0: obligatorio para el primer flujo integrado.
- P1: ampliación posterior al flujo local.
- P2: investigación opcional.

Estos requisitos detallan RF-01 a RF-06, RF-12, RF-13 y RF-37 del catálogo general. No reemplazan sus identificadores.

## Metadatos y generación sintética

### DV-RF-01 · P0 · Cargar metadatos

**Entrada:** metadatos de un partido sintético.

**Resultado:** partido identificado con equipos, jugadores, dimensiones del campo y direcciones de ataque por período.

**Verificación:** cargar un ejemplo válido y consultar los mismos identificadores y valores.

**Dependencia:** contrato de metadatos de `MatchEvent 1.0`.

### DV-RF-02 · P0 · Generar un partido reproducible

**Entrada:** configuración y semilla conocidas.

**Resultado:** secuencia estable de eventos con identificadores deterministas.

**Verificación:** ejecutar dos veces y comparar la secuencia completa.

### DV-RF-03 · P0 · Cubrir los eventos mínimos

**Entrada:** escenario sintético de aceptación.

**Resultado:** secuencia con pase, tiro, entrada, cambio de posesión, presión y recuperación, además de una transición y un momento decisivo.

**Verificación:** comprobar que cada tipo y escenario aparece en el catálogo.

## Validación e ingesta

### DV-RF-04 · P0 · Validar eventos

**Entrada:** objeto candidato a `MatchEvent 1.0`.

**Resultado:** evento aceptado o error estructurado con campo y motivo.

**Verificación:** probar un evento válido, uno sin campos opcionales y uno inválido.

### DV-RF-05 · P0 · Preservar identidad y tiempo

**Entrada:** evento válido.

**Resultado:** `event_id`, `match_id`, `period`, `clock_ms` y `video_time_ms` conservados durante el transporte.

**Verificación:** rastrear el mismo evento desde el productor hasta el consumidor.

### DV-RF-06 · P0 · Evitar duplicados

**Entrada:** dos mensajes con el mismo `match_id` y `event_id`.

**Resultado:** un solo evento deportivo aceptado; el duplicado queda registrado.

**Verificación:** publicar dos veces el mismo evento y comprobar el conteo del consumidor.

### DV-RF-07 · P0 · Registrar eventos incompletos

**Entrada:** evento sin un campo obligatorio.

**Resultado:** rechazo explícito sin detener los eventos posteriores.

**Verificación:** intercalar un evento incompleto entre dos válidos y recibir los dos válidos.

### DV-RF-08 · P1 · Tratar eventos tardíos

**Entrada:** evento válido cuyo reloj deportivo es anterior al último evento procesado.

**Resultado:** evento marcado y tratado según la política acordada; nunca se oculta silenciosamente.

**Verificación:** enviar eventos fuera de orden y comparar el registro y la salida con la política documentada.

**Dependencia:** acuerdo con Persona 2 sobre reconstrucción del estado.

## Reproducción y sincronización

### DV-RF-09 · P0 · Reproducir progresivamente

**Entrada:** partido sintético y factor de velocidad.

**Resultado:** eventos emitidos en el orden y ritmo configurados.

**Verificación:** ejecutar a velocidad normal y acelerada sin cambiar los eventos.

### DV-RF-10 · P0 · Sincronizar con vídeo

**Entrada:** eventos con `video_time_ms` y vídeo autorizado.

**Resultado:** emisión correspondiente a la posición actual del vídeo.

**Verificación:** pausar, adelantar y reiniciar sin emitir eventos de otro momento.

**Dependencia:** vídeo permitido y regla de sincronización.

## Transporte y almacenamiento Azure

### DV-RF-11 · P0 · Usar transporte local

**Entrada:** eventos normalizados y configuración `memory`.

**Resultado:** eventos disponibles para un consumidor local sin Azure.

**Verificación:** recorrer el partido completo sin conexión a servicios externos.

### DV-RF-12 · P0 · Publicar en Azure Event Hubs

**Entrada:** evento válido y configuración de Azure.

**Resultado:** sobre de transporte publicado en el event hub configurado.

**Verificación:** consumir el mensaje y comprobar que la carga útil coincide con el evento original.

### DV-RF-13 · P0 · Consumir desde Azure Event Hubs

**Entrada:** mensajes del event hub.

**Resultado:** eventos validados entregados al backend; mensajes inválidos y duplicados quedan registrados.

**Verificación:** publicar una mezcla conocida y comparar aceptados, rechazados y duplicados.

### DV-RF-14 · P1 · Guardar artefactos en Blob Storage

**Entrada:** partido sintético, vídeo autorizado u observación experimental.

**Resultado:** archivo almacenado en el contenedor correspondiente con procedencia identificable.

**Verificación:** escribir, consultar y recuperar un archivo de prueba.

### DV-RF-15 · P0 · Desplegar Azure mediante comandos

**Entrada:** suscripción, región, grupo de recursos y prefijo personal.

**Resultado:** Event Hubs y Blob Storage creados mediante Azure CLI y Bicep.

**Verificación:** dos integrantes despliegan con parámetros distintos sin editar `main.bicep` ni compartir credenciales.

### DV-RF-16 · P0 · Exponer configuración sin secretos

**Entrada:** salidas del despliegue.

**Resultado:** nombres y endpoints utilizables por la aplicación sin guardar secretos reales en Git.

**Verificación:** revisión del repositorio y ejecución con autenticación individual.

## Vídeo y fusión experimental

### DV-RF-17 · P2 · Evaluar percepción espacial

**Entrada:** vídeo permitido y muestra anotada.

**Resultado:** detecciones de jugador y balón, posiciones, confianza, latencia y errores observados.

**Verificación:** comparar contra la muestra manual y publicar el informe, aunque el modelo no sea viable.

### DV-RF-18 · P2 · Evaluar detección de acciones

**Entrada:** vídeo permitido y referencia temporal anotada.

**Resultado:** acciones detectadas con tiempo, clase, confianza y errores.

**Verificación:** medir resultados por clase y tiempo de procesamiento.

### DV-RF-19 · P2 · Fusionar observaciones

**Entrada:** observaciones temporales y espaciales compatibles.

**Resultado:** evento normalizado con fuentes, confianza y referencias a observaciones originales.

**Verificación:** casos de coincidencia, contradicción y ausencia de evidencia suficiente.

### DV-RF-20 · P2 · Evitar identidad no comprobada

**Entrada:** seguimiento visual sin asociación fiable a la plantilla.

**Resultado:** se conserva `track_id`, pero `player_id` queda ausente.

**Verificación:** comprobar que ninguna salida transforma automáticamente un seguimiento en identidad real.

## Requisitos no funcionales

### DV-RNF-01 · P0 · Reproducibilidad

La misma configuración y semilla deben producir los mismos eventos e identificadores.

### DV-RNF-02 · P0 · Independencia de infraestructura

El generador, validador y contrato no deben depender del SDK de Azure, Roboflow ni SoccerNet.

### DV-RNF-03 · P0 · Trazabilidad

Cada salida debe conservar la procedencia necesaria para llegar al evento u observación original.

### DV-RNF-04 · P0 · Seguridad de configuración

No se guardarán claves, cadenas de conexión, tokens ni identificadores personales de suscripción en el repositorio.

### DV-RNF-05 · P0 · Despliegue repetible

La infraestructura debe crearse desde un entorno limpio con comandos documentados y parámetros propios de cada cuenta.

### DV-RNF-06 · P1 · Fallo aislado de Azure

Un fallo de publicación en Azure debe producir un error observable y no corromper el evento original. El modo local debe continuar disponible.

### DV-RNF-07 · P1 · Medición

La prueba integrada debe registrar, por mensaje, tiempo de producción, publicación y recepción para calcular la latencia del transporte.

## Matriz con requisitos generales

| Requisito general | Detalle de Persona 1 |
|---|---|
| RF-01 | DV-RF-01, DV-RF-02 |
| RF-02 | DV-RF-03 |
| RF-03 | DV-RF-05 |
| RF-04 | DV-RF-04, DV-RF-06, DV-RF-07 |
| RF-05 | DV-RF-08 |
| RF-06 | DV-RF-02, DV-RF-03 |
| RF-12 | DV-RF-17, DV-RF-19 |
| RF-13 | DV-RF-17 a DV-RF-20 |
| RF-37 | DV-RF-09, DV-RF-10 |
| RNF-01 | DV-RNF-01 |
| RNF-03 | DV-RNF-03 |
| RNF-04 | DV-RNF-05 |
