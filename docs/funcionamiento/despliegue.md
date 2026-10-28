# Despliegue y operación

Esta guía documenta las definiciones y scripts presentes en el repositorio. La reorganización documental no ejecutó un despliegue ni verificó el estado de una suscripción, base de datos o modelo remoto.

## Servicios y construcción

| Pieza | Archivo y contexto | Comportamiento |
|---|---|---|
| API | `apps/backend/Dockerfile`, contexto raíz | Uvicorn en 8000; imagen reutilizable para worker analítico/replay |
| Web | `apps/frontend/Dockerfile`, contexto `apps/frontend` | Compila con Node y sirve con nginx en 80 |
| Worker importante | `apps/backend/Dockerfile.worker`, contexto `apps/backend` | Ejecuta el consumidor de eventos importantes |
| Diagnóstico de vídeo | `apps/backend/Dockerfile.integration`, contexto raíz | Sirve el experimento de sincronización en 8018 |

Ejemplos de construcción desde la raíz:

```powershell
docker build -f apps/backend/Dockerfile -t prime-moment-api .
docker build -f apps/frontend/Dockerfile -t prime-moment-web apps/frontend
docker build -f apps/backend/Dockerfile.worker -t prime-moment-worker apps/backend
```

El backend copia los tres resultados precalculados de `apps/backend/data/vision/`. No necesita `docs-anteirores/`. `.dockerignore` limita el contexto a código, datos, scripts y experimento necesarios. El vídeo y pesos de modelos requieren provisión aparte.

El Dockerfile web usa su propio contexto y ejecuta `npm install`/`npm run build`. No sustituir su contexto por la raíz sin adaptar el archivo.

## Proxy del frontend

En nginx, `API_UPSTREAM` contiene la URL del backend y `API_HOST` su host. La plantilla de Azure los deriva del FQDN de la API. El navegador conserva un único origen y usa `/api/v1/...`.

El valor predeterminado de contenedor es `http://127.0.0.1:8000`. En contenedores separados debe configurarse un destino alcanzable; localhost identifica el contenedor web, no otra Container App. SSE requiere conexiones largas y buffering deshabilitado, como indica la plantilla nginx incluida.

## Azure

`infra/azure/deploy-analytics.ps1` coordina las plantillas Bicep, el registro de imágenes, identidades y roles, y las aplicaciones de API, web, procesador continuo y replay. Event Hubs/Blob y otros servicios se definen en las plantillas relacionadas; el transporte de decisiones importantes requiere además la configuración de Service Bus correspondiente.

Preparar Azure CLI autenticada, una suscripción/región con permisos y cuotas, Docker o ACR Tasks, y la configuración de Supabase cuando corresponda. Los nombres, prefijo y grupo son parámetros.

Ejemplo de inspección y ejecución, para quien vaya a desplegar:

```powershell
./infra/azure/deploy-analytics.ps1 -ResourceGroup <grupo> -Location eastus2 -WhatIf
./infra/azure/deploy-analytics.ps1 -ResourceGroup <grupo> -Location eastus2
```

`-WhatIf` **no es una operación completamente de solo lectura**: el script puede registrar proveedores y crear el grupo vacío antes de la previsualización. `-UseAcrBuild` construye en ACR; `-InfraOnly` ejecuta solo infraestructura; `-SkipWeb` omite web. `-WorkerOn` y `-ApiAlwaysOn` mantienen cómputo encendido. `-RecreateEnvironment` elimina/recrea el entorno y sus aplicaciones; no es necesario para una actualización ordinaria.

Los scripts de servicios de visión son independientes. Revisar sus preflights y requisitos de GPU; no presentar el servicio como activo sin comprobarlo.

## Supabase: dos conjuntos de migraciones

| Directorio | Uso |
|---|---|
| `infra/supabase/migrations/` | Almacenamiento analítico y datos de los procesos de seed/worker |
| `supabase/migrations/` | Experiencia, comunidad, variantes de resumen y callouts |

`supabase_seed.py --schema` aplica el primer conjunto; **no aplica automáticamente el segundo**. Revisar el procedimiento del proyecto Supabase para desplegar las migraciones de experiencia, respetando su orden.

Desde la raíz, con Python/backend instalado:

```powershell
python apps/backend/scripts/supabase_seed.py --dry-run
python apps/backend/scripts/supabase_seed.py --schema
```

La segunda orden requiere `SUPABASE_DB_URL` y escribe en la base. Volver a sembrar reemplaza los partidos de ejemplo y borra sus análisis previos según el script. No ejecutarla sobre datos que se quieran conservar sin revisar ese efecto.

## Variables por integración

| Integración | Variables principales |
|---|---|
| Experiencia Supabase Data API | `SUPABASE_ENABLED`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY` |
| Lectura PostgreSQL | `MATCH_SOURCE=supabase`, `SUPABASE_DB_URL` |
| Motor de analítica | `ANALYTICS_ENGINE=persona2` |
| Narrativa remota | `NARRATIVE_PROVIDER=azure` y `AZURE_OPENAI_*` |
| Ingreso de eventos | `EVENT_TRANSPORT`, namespace/hub/grupo de Event Hubs |
| Decisiones importantes | `ROUTING_TRANSPORT`, namespace/cola de Service Bus, hub de métricas |
| Salidas analíticas | `ANALYTICS_OUTPUT`, hub de insights y contenedor de Blob |
| Observaciones de visión | `VISION_OBSERVATION_TRANSPORT`, `VISION_EVENT_HUB_*` |
| Inferencia y resultados | Endpoint/clave Roboflow, `MENTOX_*_ARTIFACT`, vídeo permitido |

Consultar `.env.example` y los validadores de configuración: estos nombres no son una lista suficiente de credenciales o roles para todos los modos. Las claves secretas permanecen en backend/almacén de secretos, nunca en React ni en documentación.

## Comprobación tras desplegar

1. Consultar salud y OpenAPI de la API y abrir el frontend desde su URL.
2. Probar `/api` a través del origen web y verificar SSE sin cortes por buffering.
3. Reproducir un escenario, pausar, saltar, preguntar y revisar un resumen.
4. Confirmar proveedor analítico/narrativo realmente seleccionado y distinguir respaldos locales.
5. Si hay workers, seguir correlación desde ingreso hasta métricas/decisión importante y salida persistida.
6. Si hay visión, revisar hashes, origen del medio, tiempos y disponibilidad de vídeo/modelos.
7. Revisar logs sin secretos, permisos de identidad, réplicas, errores, coste y recuperación.

Estas comprobaciones están pendientes en el entorno remoto para esta reorganización. Las pruebas locales con dobles no certifican disponibilidad ni un SLA de producción.
