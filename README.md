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

En una terminal, inicia la API:

```bash
uv run --project apps/backend uvicorn match_intelligence.main:app --reload --app-dir apps/backend/src
```

En otra terminal, inicia el frontend:

```bash
npm run dev:frontend
```

La interfaz local aparece en `http://localhost:5173`. Swagger UI está en `http://localhost:8000/docs`. El formulario inicial valida un evento contra el formato `1.0`; todavía no guarda eventos ni analiza partidos.

CrewAI figura como dependencia opcional del backend. Cuando se implemente el equipo de agentes y se elija un proveedor de modelos, se podrá instalar con `uv sync --project apps/backend --extra agents`.
