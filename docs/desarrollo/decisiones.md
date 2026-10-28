# Decisiones de implementación

## Producto y organización

La marca visible es **The Prime Moment**. Se conservan los identificadores técnicos `match_intelligence` y el nombre del repositorio. El producto se demuestra con datos sintéticos y material con permiso; no se distribuyen datos reales de Premier League como parte de la demo.

El backend separa dominio, aplicación y adaptadores. Los contratos y cálculos permanecen independientes de HTTP y de los proveedores externos. Las implementaciones de memoria permiten desarrollo local; las de Azure y Supabase son intercambiables mediante configuración.

## Tecnologías presentes

| Capa | Decisión y evidencia |
|---|---|
| Interfaz | React 19, JavaScript, Vite 8 y CSS por área, declarados en `apps/frontend/package.json` |
| API | FastAPI y Uvicorn sobre Python `>=3.12,<3.14`; entorno recomendado del repositorio: Python 3.12 |
| Dependencias | `package-lock.json` para npm; `apps/backend/uv.lock` para Python con uv |
| Navegación | Router hash propio, en `apps/frontend/src/app/router.js` |
| Preferencias | Contexto React y almacenamiento local `itg:preferences` |
| Directo | SSE para mensajes de partido/comunidad y WebSocket en la integración de observaciones |
| Datos remotos | Supabase Data API para persistencia de experiencia y conexión PostgreSQL para carga/lectura operativa |
| Transporte | Memoria en local; Event Hubs para flujos y Service Bus para eventos importantes |
| Almacenamiento | Blob Storage para artefactos y adaptadores de ficheros para pruebas locales |
| Infraestructura | Bicep, scripts PowerShell/Bash, Docker y Azure Container Apps |

Las versiones exactas instalables las fijan los lockfiles. Esta tabla describe el repositorio y no propone actualizaciones de dependencias.

## Reglas del flujo

- Validar y deduplicar antes de producir efectos. Los eventos tardíos se marcan con `forward_and_flag`; esa política no reconstruye por sí sola el estado.
- Calcular estadísticas con código determinista. Una cifra no se obtiene de prosa generada por un modelo.
- Conservar `source_event_ids`, versión de fórmula y límites de evidencia.
- Usar el reloj del vídeo para decidir qué datos ya ocurrieron; adelantar o cambiar de pestaña no debe revelar eventos futuros.
- Separar observaciones de vídeo, candidatos de fusión, simulaciones y hechos deportivos confirmados.
- Personalizar foco, tono y detalle; el marcador y las cifras no cambian por el club seguido.
- Retener la publicación editorial hasta una aprobación explícita; un voto comunitario no reemplaza esa aprobación.

## Agentes y degradación

`NARRATIVE_PROVIDER=provisional` usa plantillas locales, `fixture` utiliza la ruta de contratos sin red y `azure` conecta CrewAI. El gateway de CrewAI permite despliegues rápidos y de calidad separados. El enrutador de tareas usa `FixtureDispatchGateway` por defecto, por lo que no se describe como un orquestador LLM activo.

La narrativa conserva respaldos locales y algunos métodos siguen delegando a ellos incluso cuando existe un proveedor remoto. La política futura de modelos no equivale a una configuración desplegada. El detalle está en [agentes](../funcionamiento/agentes.md).

## Organización documental

Desde el 28 de octubre los documentos anteriores viven en `docs-anteirores/`, ignorado por Git. Los datos necesarios para pruebas y contenedores se versionan fuera del archivo. Las nuevas evidencias se guardan en `docs/desarrollo/evidencias/`. El plan del 1 al 27 es retrospectivo y no se modifica para atribuirle entregas del 28.

## Decisiones todavía abiertas

La integración completa de inferencias a eventos confirmados, el almacenamiento durable de idempotencia, la ejecución de agentes detrás del worker, los objetivos medidos de latencia, el dimensionamiento de producción y la investigación externa requieren decisiones y pruebas adicionales. Consultar [validación](validacion.md).
