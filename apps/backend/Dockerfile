# Imagen del backend: API (Persona 4 con la analítica de Persona 2), procesador
# continuo y repetición de partidos. El comando cambia en cada Container App.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir uv==0.13.1

# El código queda en la misma ruta relativa que en el repositorio: algunos módulos
# ubican archivos subiendo carpetas desde su propio archivo (data/prematch y la
# raíz del repositorio), así que la instalación es editable y conserva src/.
WORKDIR /srv/repo/apps/backend
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --extra db --no-install-project
COPY src ./src
RUN uv sync --frozen --extra db
COPY data ./data
COPY scripts ./scripts

RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8000
CMD ["uvicorn", "match_intelligence.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
