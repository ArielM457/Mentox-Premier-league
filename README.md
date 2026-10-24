# **Inteligencia de partidos**

Monorepo inicial para el hackathon. La [documentación](docs/README.md) contiene el alcance, las decisiones, los casos de uso y el contrato de eventos.

## **Estructura**

- `apps/frontend`: interfaz React en JavaScript, creada con Vite.
- `apps/backend`: API FastAPI en Python con Uvicorn.
- `docs`: decisiones, requisitos e investigación.
- `.agents/skills`: instrucciones del proyecto para futuros agentes.

## **Codex y Context7**

El repositorio incluye una configuración de Context7 para consultar documentación vigente de bibliotecas y frameworks desde Codex. Cada integrante debe autorizar su propia cuenta antes de usarla; no se comparten claves ni sesiones.

Las instrucciones de confianza, autenticación, verificación y solución de problemas están en [`.codex/README.md`](.codex/README.md).

## **Preparación local**

Se necesita Python 3.12, [uv](https://docs.astral.sh/uv/) y una versión de Node compatible con Vite. `uv` puede instalar automáticamente la versión fijada en `.python-version`. Desde la raíz del repositorio:

```bash
npm install
uv python install 3.12
uv sync --project apps/backend --extra dev
```

En una terminal, inicia la API con la configuración local de `apps/backend/.env`:

```bash
uv run --project apps/backend uvicorn match_intelligence.main:app --reload --app-dir apps/backend/src --env-file apps/backend/.env
```

Copia primero `apps/backend/.env.example` como `apps/backend/.env`. El archivo real está ignorado por Git. Usa `NARRATIVE_PROVIDER=provisional` para trabajar sin servicios externos, `fixture` para probar los contratos reales de Persona 3 sin Azure o `azure` para usar los despliegues configurados.

En otra terminal, inicia el frontend:

```bash
npm run dev:frontend
```

La interfaz local aparece en `http://localhost:5173`. Swagger UI está en `http://localhost:8000/docs`. La interfaz reproduce los partidos sintéticos con mensajes sincronizados, preferencias, preguntas, resumen y revisión editorial. También permite simular las seis rutas del filtro, revisar propuestas de recorte y consultar el flujo desde el perfil analista. La experiencia ya puede consumir el módulo de Persona 3 mediante el proveedor configurado; el detalle está en [Persona 4](docs/persona-4-api-y-frontend/README.md).

CrewAI es una dependencia opcional del backend. Para usar la integración con Azure OpenAI, se puede instalar con `uv sync --project apps/backend --extra agents`.

El módulo de la persona 3 ya tiene contratos, un flujo de narración y pruebas con un partido sintético. Consulta la [guía de agentes y narrativa](apps/backend/README-narrativa.md) para ejecutarlo. La API expone las operaciones de narrativa con un proveedor sintético de prueba o con Azure OpenAI si se configura el recurso y los despliegues. El adaptador de la experiencia del partido usa ese mismo flujo sin cambiar los contratos del frontend.

El backend también tiene una primera versión del filtro y el enrutamiento de agentes. La ruta `/api/v1/agent-routing/evaluate` separa eventos de solo métricas y solicitudes relevantes, reconoce dos patrones iniciales y prepara un despacho reproducible. `POST /api/v1/matches/{match_id}/simulation` recorre seis escenarios sintéticos. Todavía no existe almacenamiento persistente ni un canal durable real.

La [colección de Postman](postman/README.md) contiene peticiones y pruebas listas para importar.

## **Demostración integrada de datos y visión**

La demostración reutiliza el backend oficial y una interfaz técnica de validación. No modifica el frontend de producto. Requiere el vídeo permitido y las exportaciones locales de Roboflow Sports, SoccerNet y DV-US-21.

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  uvicorn video_sync_diagnostic.app:app \
  --app-dir experiments --host 127.0.0.1 --port 8018
```

Abra <http://127.0.0.1:8018>. La API integrada está en `GET /api/v1/integration/status`, `GET /api/v1/integration/timeline` y `/docs`.

Con Docker:

```bash
docker-compose -f compose.integration.yml up --build
```

El vídeo y los resultados se montan como volúmenes de solo lectura y no se incorporan a la imagen. Para Azure, exporte las variables de `apps/backend/.env.example`; el modo predeterminado sigue siendo `memory`.

La interfaz controla la reproducción de las observaciones ya calculadas. No se
publica nada hasta pulsar **Play**; pausa, salto y reinicio actualizan el cursor
del backend sin volver a presentar el historial como nuevo.

Para iniciar la prueba integrada:

```bash
sudo docker-compose -f compose.integration.yml up --build
```

En Azure, añada antes:

```bash
export VISION_OBSERVATION_TRANSPORT=azure_event_hubs
export EVENT_HUB_FULLY_QUALIFIED_NAMESPACE="<namespace>.servicebus.windows.net"
export VISION_EVENT_HUB_NAME="vision-observations"
export VISION_EVENT_HUB_CONSUMER_GROUP="backend"
```

El reproductor ordena al backend publicar el tramo cruzado. En Azure, el backend
produce en Event Hubs, su consumidor recibe y deduplica, y finalmente WebSocket
actualiza la interfaz. Esta prueba reutiliza inferencias ya calculadas; no vuelve
a ejecutar los modelos.
