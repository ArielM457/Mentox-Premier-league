# Plan de pruebas con servicios y medios reales

## Objetivo

Este plan transforma las verificaciones locales de DV-US-06 a DV-US-13 en evidencias de integración. No cambia el MVP sintético ni supone que Azure, los vídeos o los modelos ya estén disponibles.

La ejecución se divide en tres recorridos:

1. Azure real: infraestructura, Event Hubs y Blob Storage.
2. Vídeo permitido: sincronización observable desde una interfaz mínima.
3. Visión real: Roboflow Sports, SoccerNet, identidad y fusión experimental.

## Qué falta actualmente

| Capacidad | Estado actual | Para cerrarla falta |
|---|---|---|
| Infraestructura Azure | Bicep compila localmente | `validate`, `what-if`, despliegue, RBAC y evidencia anonimizada |
| Event Hubs | SDK y dobles verificados | Publicación y consumo contra el servicio real |
| Blob Storage | SDK y dobles verificados | Carga y descarga contra la cuenta real |
| Evento tardío | Detección local | Política acordada con Persona 2 |
| Sincronización | Coordinador local | Vídeo permitido, API y página de diagnóstico |
| Evaluación de visión | Evaluador local | Vídeo, anotación, commits, pesos y predicciones reales |
| Identidad | Regla local | Evidencia nominal producida y revisada sobre la muestra |
| Fusión | Política local | Observaciones reales y tolerancias calibradas |

## ¿Necesitamos una interfaz?

### No para Azure

Event Hubs y Blob Storage se pueden verificar con los scripts existentes:

- `apps/backend/scripts/event_hubs_smoke.py`;
- `apps/backend/scripts/blob_storage_smoke.py`.

La salida estructurada de terminal es suficiente si se conserva anonimizada. Swagger o React no añaden evidencia para transporte, RBAC o integridad.

### Sí para sincronización con vídeo

Pausa y salto tienen un componente visual: no basta con comprobar el algoritmo aislado. Se necesita una página de diagnóstico pequeña, no la interfaz final del producto.

La página propuesta pertenece a Persona 4 y debe incluir:

- selector de archivo local o URL autorizada;
- elemento de vídeo con reproducir, pausar, adelantar, retroceder y reiniciar;
- posición actual del vídeo en milisegundos;
- lista de eventos visibles del tramo actual;
- contador o estado reconstruido después de un salto, separado de los mensajes visibles;
- detalle de `event_id`, `clock_ms`, `video_time_ms`, `source`, `track_id`, `player_id` y estado de identidad;
- panel de errores y exportación de un registro JSON de la sesión.

Para probar el coordinador Python de DV-US-10, la página debe llamar a una API de integración del backend. Una simulación completamente local en React solo probaría la interfaz, no el caso de uso implementado.

Contrato mínimo propuesto para revisión con Persona 4:

```text
POST /api/integration/video-sync/session
POST /api/integration/video-sync/play
POST /api/integration/video-sync/pause
POST /api/integration/video-sync/advance   {"video_time_ms": 12000}
POST /api/integration/video-sync/seek      {"video_time_ms": 25000}
POST /api/integration/video-sync/restart
GET  /api/integration/video-sync/session
```

Estas rutas son una propuesta de prueba, no una API implementada ni un contrato público aprobado.

## Información que debe aportar el equipo

Antes de comenzar se necesitan estas decisiones:

1. Suscripción y grupo de recursos permitidos para pruebas.
2. Región, prefijo y presupuesto o límite de costo.
3. Identidad que recibirá los roles RBAC.
4. Vídeo propio, generado o autorizado y condiciones de almacenamiento.
5. Hardware disponible para visión, especialmente GPU y memoria.
6. Umbrales iniciales para declarar un modelo `candidate`.
7. Persona responsable de revisar permisos, falsos positivos e identidades.

No se deben compartir contraseñas, tokens, claves o cadenas de conexión. La autenticación se hace con Azure CLI y `DefaultAzureCredential`.

## Paso 0 · Confirmar la base local

Desde la raíz del repositorio:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 pytest -q
```

Resultado base antes de las historias nuevas:

```text
134 passed
```

También se deben ejecutar:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache uv lock --project apps/backend --check
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python -m compileall -q apps/backend/src apps/backend/scripts
git diff --check
```

Si esta base falla, no se continúa con servicios externos hasta separar la regresión del problema de integración.

## Paso 1 · Preparar Azure CLI sin guardar datos personales

```bash
az login
az account list --output table
az account set --subscription "<suscripcion>"
az account show --query "{name:name,id:id,user:user.name}" --output table
az version
az bicep version
```

La salida completa de cuenta puede contener correo e identificadores. Se revisa en terminal, pero solo se registra en evidencia una confirmación anonimizada.

Copie el archivo de parámetros ignorado por Git:

```bash
cp infra/azure/dev.bicepparam.example infra/azure/dev.bicepparam
```

Defina en ese archivo un prefijo propio sin introducir credenciales.

## Paso 2 · Validar, previsualizar y desplegar

```bash
az group create --name "<grupo>" --location "<region>"

az deployment group validate \
  --resource-group "<grupo>" \
  --template-file infra/azure/main.bicep \
  --parameters infra/azure/dev.bicepparam

az deployment group what-if \
  --resource-group "<grupo>" \
  --template-file infra/azure/main.bicep \
  --parameters infra/azure/dev.bicepparam

az deployment group create \
  --name "mentox-data-vision" \
  --resource-group "<grupo>" \
  --template-file infra/azure/main.bicep \
  --parameters infra/azure/dev.bicepparam
```

No se ejecuta `create` hasta revisar `what-if`. Después se consultan las salidas:

```bash
az deployment group show \
  --name "mentox-data-vision" \
  --resource-group "<grupo>" \
  --query properties.outputs \
  --output json
```

Se necesitan el namespace de Event Hubs, el nombre del hub y `blobServiceEndpoint`.

## Paso 3 · Asignar y comprobar RBAC

La identidad concreta debe elegirse de forma explícita. Para un usuario de desarrollo, obtenga su identificador en terminal y no lo confirme en Git:

```bash
az ad signed-in-user show --query id --output tsv
```

Un administrador puede asignar en el alcance acordado:

```bash
az role assignment create \
  --assignee-object-id "<object-id>" \
  --assignee-principal-type User \
  --role "Azure Event Hubs Data Owner" \
  --scope "<alcance>"

az role assignment create \
  --assignee-object-id "<object-id>" \
  --assignee-principal-type User \
  --role "Storage Blob Data Contributor" \
  --scope "<alcance>"
```

Después se comprueba:

```bash
az role assignment list \
  --assignee "<object-id>" \
  --scope "<alcance>" \
  --output table
```

Se debe preferir el menor alcance práctico. La propagación de RBAC puede tardar; un error inmediato de autorización no debe resolverse añadiendo claves compartidas.

## Paso 4 · Ejecutar Event Hubs real

```bash
export EVENT_HUB_FULLY_QUALIFIED_NAMESPACE="<namespace>.servicebus.windows.net"
export EVENT_HUB_NAME="match-events"
export EVENT_HUB_CONSUMER_GROUP="diagnostics"

UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/event_hubs_smoke.py
```

La evidencia debe incluir, sin identificadores personales:

- un evento aceptado;
- un duplicado;
- cero rechazos inesperados;
- cero fallos del consumidor y productor;
- duración de publicación y latencia de transporte;
- fecha, región y versiones.

Después se vuelve a ejecutar el modo local para demostrar que Azure no lo reemplazó:

```bash
export EVENT_TRANSPORT=memory
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_transport_configuration.py -q
```

## Paso 5 · Ejecutar Blob Storage real

```bash
export AZURE_BLOB_SERVICE_ENDPOINT="https://<storage-account>.blob.core.windows.net"

UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/blob_storage_smoke.py
```

La evidencia debe registrar contenedor, nombre, partido, origen, procedencia, cantidad de bytes, SHA-256 y `content_matches=true`. No se registran tokens ni URLs firmadas.

Antes de probar `authorized-videos`, debe terminar DV-US-17. Mientras no exista permiso, solo se usan partidos y observaciones sintéticas.

## Paso 6 · Preparar el vídeo y la muestra manual

1. Elegir vídeo propio, generado o autorizado.
2. Registrar permiso, propietario, uso permitido y restricciones.
3. Calcular SHA-256 sin confirmar el archivo si no es redistribuible.
4. Registrar duración, resolución y FPS.
5. Seleccionar un tramo corto y anotar manualmente:
   - tiempos de acciones;
   - clases;
   - cajas normalizadas para detección espacial;
   - equipo cuando sea comprobable;
   - identidad solo cuando exista evidencia separada.
6. Crear una entrada real a partir de `experimentos-vision/input.example.json`.
7. Mantener vídeo, pesos y resultados sensibles fuera de Git cuando sus licencias lo exijan.

## Paso 7 · Construir y probar la interfaz mínima

Esta tarea se coordina con Persona 4:

1. Exponer una sesión de `VideoSynchronizedReplay` mediante API.
2. Crear una ruta de diagnóstico en React.
3. Cargar el vídeo permitido sin redistribuirlo.
4. Reproducir hasta cruzar varios eventos y comprobar los dos relojes.
5. Pausar antes de un evento y confirmar que no aparece.
6. Adelantar sobre varios eventos y confirmar reconstrucción sin mensajes antiguos.
7. Retroceder y repetir el tramo.
8. Reiniciar y comprobar que posición y mensajes vuelven al inicio.
9. Exportar registro JSON y conservar capturas sin contenido restringido.

No se necesita terminar todas las superposiciones o preferencias del producto para ejecutar esta prueba.

## Paso 8 · Ejecutar Roboflow Sports

Antes de instalar:

1. Fijar un commit del repositorio oficial.
2. Registrar versiones de Python, CUDA, controlador y hardware.
3. Revisar licencias de código, Ultralytics, pesos y datasets.
4. Ejecutar en un entorno separado del backend principal.
5. Exportar clase, tiempo, caja, confianza y `track_id` sin convertirlo en `player_id`.

Después se adapta la exportación al documento de DV-US-11 con `prediction_origin=actual_model` y se ejecuta:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/evaluate_vision_predictions.py \
  <roboflow-real.json> --output <roboflow-report.json>
```

Un informe `candidate` autoriza una revisión posterior, no integración automática.

## Paso 9 · Ejecutar SoccerNet

El proceso es equivalente, pero se registran checkpoint, preprocesamiento, clases de acción y tolerancia temporal. Debe ejecutarse en un entorno aislado y fijado.

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/evaluate_vision_predictions.py \
  <soccernet-real.json> --output <soccernet-report.json>
```

No se compara directamente su F1 temporal con el IoU espacial de Roboflow Sports.

## Paso 10 · Calibrar identidad y fusión

1. Conservar `track_id` sin identidad nominal como caso predeterminado.
2. Crear asociaciones nominales solo con evidencia revisada.
3. Medir diferencias temporales y espaciales de coincidencias correctas e incorrectas.
4. Elegir tolerancias basadas en esas distribuciones y el FPS del vídeo.
5. Ejecutar casos compatibles, contradictorios y sin evidencia.
6. Revisar que cada `FusedVideoEvent` conserve las observaciones originales.
7. Confirmar que los rechazados no llegan a consumidores de `MatchEvent`.

## Paso 11 · Cerrar y clasificar resultados

Cada historia real debe tener su propio documento en `evidencias/` con uno de estos estados:

- **Verificada en integración:** pasó contra el servicio, medio o modelo declarado.
- **Rechazada para la demo:** se ejecutó, pero no alcanzó permisos, calidad o rendimiento.
- **Pendiente:** no se ejecutó o falta evidencia.

La evidencia debe incluir comandos, versiones, parámetros, duración, resultado, errores y limitaciones. Los datos personales y secretos se sustituyen por marcadores.

## Paso 12 · Conservar o eliminar Azure

Primero se revisa el nombre exacto:

```bash
az group show --name "<grupo>" --output table
```

Si el equipo decide eliminarlo:

```bash
az group delete --name "<grupo>"
```

La eliminación es destructiva y requiere confirmación humana. La evidencia debe indicar si el entorno quedó activo y quién controla su costo, sin registrar identificadores personales.

## Context7

El 9 de octubre de 2026 se consultó `/websites/learn_microsoft_en-us_cli_azure`. La documentación vigente confirma las firmas de `az deployment group create`, `az role assignment create` con `--assignee-object-id`, `--assignee-principal-type`, `--role` y `--scope`, y la consulta de asignaciones con `az role assignment list`.

Las consultas anteriores de DV-US-07, DV-US-09 y DV-US-11 siguen siendo la referencia para los SDK asíncronos de Event Hubs, Blob Storage, Roboflow Sports y SoccerNet.
