# **Inteligencia de partidos**

Monorepo inicial para el hackathon. La [documentación](docs/README.md) contiene el alcance, las decisiones, los casos de uso y el contrato de eventos.

## **Estructura**

- `apps/frontend`: interfaz React en JavaScript, creada con Vite.
- `apps/backend`: API FastAPI en Python con Uvicorn.
- `docs`: decisiones, requisitos e investigación.
- `.agents/skills`: instrucciones del proyecto para futuros agentes.

## **Preparación local**

Se necesita Python 3.10 a 3.13 y una versión de Node compatible con Vite. Desde la raíz del repositorio:

```powershell
npm install
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .\apps\backend
```

En una terminal, inicia la API:

```powershell
.\.venv\Scripts\python -m uvicorn match_intelligence.main:app --reload --app-dir apps/backend/src
```

En otra terminal, inicia el frontend:

```powershell
npm run dev:frontend
```

La interfaz local aparece en `http://localhost:5173`. Swagger UI está en `http://localhost:8000/docs`. El formulario inicial valida un evento contra el formato `1.0`; todavía no guarda eventos ni analiza partidos.

CrewAI figura como dependencia opcional del backend. Cuando se implemente el equipo de agentes y se elija un proveedor de modelos, se podrá instalar con `pip install -e '.\apps\backend[agents]'`.
