# Instalación y ejecución local

## Requisitos

- Node compatible con el Vite fijado por el lockfile; esta máquina se comprobó con Node 24.19.0 y npm 11.17.0.
- Python 3.12 y uv. El proyecto admite Python `>=3.12,<3.14`.
- Git y Git LFS para las imágenes del directorio de referencia `ejemplo ui/`.

Los comandos de preparación siguientes parten de la raíz de `The-Premier-Moment`. No se necesita Azure ni Supabase para la demo sintética.

## Instalar dependencias

```powershell
npm ci
uv python install 3.12
uv sync --project apps/backend --locked --all-extras
```

`--all-extras` incluye agentes, base de datos y desarrollo. Para una instalación menor usar `--extra dev`; añadir `--extra db` o `--extra agents` cuando se utilicen esas integraciones. Las dependencias especializadas de los experimentos GPU no están incluidas en esta instalación.

Si todavía no existe `apps/backend/.env`, copiar `apps/backend/.env.example` con ese nombre. Conservar cualquier `.env` ya configurado; no sobrescribirlo. La configuración inicial usa memoria, narrativa provisional, analítica provisional y fuente sintética. Para el motor analítico de Persona 2, establecer `ANALYTICS_ENGINE=persona2`.

En esta máquina también hay herramientas portátiles en `../.git-tools/`; no forman parte del repositorio ni deben suponerse instaladas en otros equipos. Se puede invocar uv como `& ..\.git-tools\uv\uv.exe` desde la raíz si no está en el PATH.

## Iniciar backend

En una terminal, desde la raíz:

```powershell
cd apps/backend
.\.venv\Scripts\Activate.ps1
uvicorn match_intelligence.main:app --reload --app-dir src --env-file .env
```

API: `http://localhost:8000`. Swagger: `http://localhost:8000/docs`. Salud: `http://localhost:8000/api/v1/health`.

Alternativa desde la raíz, sin activar el entorno:

```powershell
uv run --project apps/backend --no-sync uvicorn match_intelligence.main:app --reload --app-dir apps/backend/src --env-file apps/backend/.env
```

## Iniciar frontend

En otra terminal, desde la raíz:

```powershell
cd apps/frontend
npm run dev
```

Vite suele servir `http://localhost:5173`. Si el puerto está ocupado, revisar la dirección que imprime. `/api` se reenvía por defecto a `http://127.0.0.1:8000`.

Para usar otro backend, establecer antes de `npm run dev`:

```powershell
$env:VITE_BACKEND_PROXY = 'http://127.0.0.1:8001'
npm run dev
```

La configuración actual lee esa variable del proceso de Vite. No asumir que crear un `.env` de frontend basta para modificar `process.env` en `vite.config.js`.

## Compilar y empaquetar

Frontend, desde `apps/frontend`:

```powershell
npm run build
```

Genera `apps/frontend/dist`. El backend Python se ejecuta con Uvicorn; si se necesita una distribución, desde la raíz:

```powershell
uv build --project apps/backend --out-dir apps/backend/dist
```

Genera wheel y distribución fuente; no inicia el servidor. Los archivos `dist` y el entorno virtual están ignorados.

## Pruebas y recursos regenerables

Desde la raíz, con dependencias instaladas:

```powershell
uv run --project apps/backend --no-sync pytest apps/backend/tests -q
npm run lint:frontend
npm run build:frontend
```

Con el entorno Python activado también se puede usar `pytest apps/backend/tests -q` desde la raíz. La suite completa tiene fallos conocidos del entorno: consultar [validación](../desarrollo/validacion.md) antes de interpretar un resultado.

Para regenerar ejemplos y tablero, desde la raíz y con el Python del backend activo:

```powershell
python apps/backend/scripts/export_analytics_examples.py
python apps/backend/scripts/export_analytics_demo.py
```

La demo HTML queda en `experiments/analytics-demo/tablero.html`. Para la integración de visión y sus artefactos, seguir [datos y visión](datos-y-vision.md).
