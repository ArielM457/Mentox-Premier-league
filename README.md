# The Prime Moment

Experiencia de inteligencia de partidos: eventos sintéticos, estadísticas, momentos explicados, reproducción sincronizada y personalización por club, jugador y modo.

La documentación vigente empieza en [docs/README.md](docs/README.md): [contexto](docs/contexto-del-proyecto.md), [plan del 1 al 27 de octubre](docs/plan-octubre.md), [desarrollo con Spec Driven Design](docs/desarrollo/README.md) y [funcionamiento del programa](docs/funcionamiento/README.md).

## Estructura

| Directorio | Contenido |
|---|---|
| `apps/frontend/` | React, JavaScript, Vite y estilos del producto |
| `apps/backend/` | FastAPI, dominio, analítica, narrativa, adaptadores y pruebas |
| `docs/` | Contexto, planificación, especificaciones y guías vigentes |
| `docs-anteirores/` | Archivo local ignorado de los 158 documentos anteriores |
| `experiments/` | Experimentos de datos/visión y tablero analítico |
| `infra/`, `deploy/` | Infraestructura, scripts y servicios de modelos |
| `supabase/` | Migraciones de la experiencia |
| `postman/` | Colección de peticiones y comprobaciones HTTP |
| `.agents/`, `.codex/` | Instrucciones del proyecto y configuración de herramientas |

El archivo anterior no se distribuye en los siguientes clones. Los datos necesarios para pruebas y empaquetado se conservan versionados fuera de ese archivo.

## Preparación

Se requiere Node compatible con Vite, Python 3.12 y uv. Desde la raíz:

```powershell
npm ci
uv sync --project apps/backend --locked --all-extras
```

Si no existe `apps/backend/.env`, copiar `apps/backend/.env.example` con ese nombre. La demo local usa datos sintéticos, memoria y narrativa provisional. Los proveedores remotos necesitan configuración adicional.

## Backend

En una terminal, desde la raíz:

```powershell
cd apps/backend
.\.venv\Scripts\Activate.ps1
uvicorn match_intelligence.main:app --reload --app-dir src --env-file .env
```

Swagger: `http://localhost:8000/docs`.

## Frontend

En otra terminal, desde la raíz:

```powershell
cd apps/frontend
npm run dev
```

Interfaz: `http://localhost:5173`. Vite reenvía `/api` al backend local del puerto 8000, salvo que se configure `VITE_BACKEND_PROXY`.

## Compilación y pruebas

Desde la raíz:

```powershell
npm run build:frontend
npm run lint:frontend
uv run --project apps/backend --no-sync pytest apps/backend/tests -q
uv build --project apps/backend --out-dir apps/backend/dist
```

Consultar los [resultados y fallos conocidos](docs/desarrollo/validacion.md). La existencia de adaptadores Azure/CrewAI/Supabase no significa que esos servicios se hayan comprobado en esta máquina.

La [ejecución local](docs/funcionamiento/ejecucion-local.md) incluye dependencias, recursos regenerables y configuración. La [guía de despliegue](docs/funcionamiento/despliegue.md) explica Docker, Azure y las dos familias de migraciones de Supabase. El [flujo del programa](docs/funcionamiento/flujo-del-programa.md) describe el recorrido completo.

Para el trabajo con Codex y Context7, consultar [la configuración del repositorio](.codex/README.md).
