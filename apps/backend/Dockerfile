# Imagen del backend: API (Persona 4 con la analítica de Persona 2), procesador
# continuo y repetición de partidos. El comando cambia en cada Container App.
# Se construye desde la raíz del repositorio (ver .dockerignore):
#   docker build -f apps/backend/Dockerfile .
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
COPY apps/backend/pyproject.toml apps/backend/uv.lock ./
RUN uv sync --frozen --extra db --no-install-project

# Resultados de los modelos de visión de Persona 1 (pestaña «Visión IA»). Se usa el
# informe de fusión recalculado, que corresponde a estas predicciones.
ARG VISION_RESULTS=apps/backend/data/vision
COPY ${VISION_RESULTS}/roboflow-sports-predictions.json \
     ${VISION_RESULTS}/soccernet-predictions.json \
     ${VISION_RESULTS}/dv-us-21-report-recalculado.json \
     /srv/repo/${VISION_RESULTS}/
ENV MENTOX_ROBOFLOW_ARTIFACT=/srv/repo/${VISION_RESULTS}/roboflow-sports-predictions.json \
    MENTOX_SOCCERNET_ARTIFACT=/srv/repo/${VISION_RESULTS}/soccernet-predictions.json \
    MENTOX_FUSION_ARTIFACT=/srv/repo/${VISION_RESULTS}/dv-us-21-report-recalculado.json

COPY apps/backend/src ./src
RUN uv sync --frozen --extra db
COPY apps/backend/data ./data
COPY apps/backend/scripts ./scripts

RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8000
CMD ["uvicorn", "match_intelligence.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
