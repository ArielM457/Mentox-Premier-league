# SDD-06 · Integración y despliegue

## Especificación

**Objetivo:** ejecutar una demo local reproducible y disponer de una configuración explícita para desplegar servicios remotos sin acoplar el dominio a ellos.

**Entradas:** código, lockfiles, variables, imágenes y parámetros de infraestructura. **Salidas:** frontend compilado, paquete backend, servicios configurados, flujos de eventos y almacenamiento.

Requisitos relacionados: RF-51, RF-64 y RNF de documentación, disponibilidad, idempotencia, coste, trazabilidad y respuesta a fallos. No se fija un SLA numérico que el equipo no haya medido y acordado.

### Criterios de aceptación

1. El frontend compila desde su lockfile y usa rutas relativas de API.
2. El backend instala sus dependencias y se puede iniciar con Uvicorn.
3. La demo sintética funciona con transporte en memoria y narrativa provisional.
4. Telemetría e información importante tienen fallos independientes: perder métricas no debe ocultar el fallo de una entrega importante.
5. El contexto de construcción Docker no necesita la carpeta ignorada de documentos antiguos.
6. Las credenciales permanecen en el servidor o almacenes de secretos y no en React ni en documentos versionados.

## Diseño implementado

Los Dockerfiles de API y frontend producen imágenes separadas. La API, el procesador continuo y el replay reutilizan la imagen backend cuando así lo define la plantilla. `Dockerfile.worker` cubre el worker importante y `Dockerfile.integration` la demo diagnóstica.

`infra/azure/analytics-platform.bicep` y sus plantillas relacionadas describen registro, identidades, permisos, servicios de datos y Container Apps. `deploy-analytics.ps1` organiza provisión, construcción/publicación de imágenes y despliegue. Los servicios de visión tienen scripts específicos.

El frontend de contenedor usa nginx como proxy; `API_UPSTREAM` y `API_HOST` apuntan al backend de ese entorno. En desarrollo se usa `VITE_BACKEND_PROXY` o el backend local en el puerto 8000.

Supabase tiene migraciones y un proceso de seed. Event Hubs transporta flujos, Service Bus decisiones importantes y Blob Storage artefactos. Los adaptadores locales siguen disponibles para pruebas sin acceso remoto.

## Tareas y estado

- [x] Versionar lockfiles, scripts de ejecución e imágenes.
- [x] Definir infraestructura parametrizable, identidad administrada y roles.
- [x] Incorporar persistencia y flujos remotos seleccionables.
- [x] Separar recursos de prueba, demo y resultados de visión de la documentación.
- [x] Actualizar rutas de Docker, exportadores, pruebas e instrucciones tras el archivo documental.
- [ ] Construir imágenes en Docker/ACR con la nueva estructura en el entorno de despliegue.
- [ ] Verificar recursos remotos, permisos, redes, cuotas y disponibilidad real de modelos.
- [ ] Validar recuperación, idempotencia durable y operación con múltiples réplicas.
- [ ] Medir latencia/coste y acordar objetivos de operación antes de declarar producción.

## Validación

`test_transport_configuration.py`, `test_routing_transport.py`, `test_azure_event_hubs.py`, `test_azure_blob_storage.py`, `test_analytics_azure.py` y `test_azure_infrastructure.py` cubren configuración y contratos con dobles. No aprovisionan una suscripción completa.

La [guía de despliegue](../funcionamiento/despliegue.md) recoge los comandos y requisitos reales. La reorganización no ejecuta despliegues ni modifica servicios externos.
