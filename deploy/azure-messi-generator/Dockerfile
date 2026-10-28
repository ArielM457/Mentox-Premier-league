FROM python:3.12-slim

ARG DEBIAN_FRONTEND=noninteractive
ARG MESSI_REPOSITORY=https://github.com/UoS-CIDA-Lab/MESSI.git
ARG MESSI_COMMIT=b04b15c59d36c1e4f44e02d0886b2d0d7261f689

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        ca-certificates \
        build-essential \
        ffmpeg \
        git \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /uvx /bin/
COPY requirements.txt /tmp/requirements.txt
COPY patches/clean-hud.patch /tmp/clean-hud.patch

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    UV_HTTP_TIMEOUT=300 \
    UV_LINK_MODE=copy

RUN git clone "${MESSI_REPOSITORY}" /opt/messi \
    && git -C /opt/messi checkout --detach "${MESSI_COMMIT}" \
    && test "$(git -C /opt/messi rev-parse HEAD)" = "${MESSI_COMMIT}" \
    && git -C /opt/messi apply --check /tmp/clean-hud.patch \
    && git -C /opt/messi apply /tmp/clean-hud.patch

RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv --python python3.12 "${VIRTUAL_ENV}" \
    && uv pip install --python "${VIRTUAL_ENV}/bin/python" \
        "jax[cuda12]==0.4.38" \
        "jaxmarl==0.0.7" \
        "jaxtyping>=0.2.36,<1" \
        "numpy>=1.26,<3" \
        "imageio[ffmpeg]>=2.34,<3" \
        "matplotlib>=3.8,<4" \
        "pillow>=10,<13" \
    && uv pip install --python "${VIRTUAL_ENV}/bin/python" \
        --no-deps --editable /opt/messi \
    && uv pip install --python "${VIRTUAL_ENV}/bin/python" \
        --requirements /tmp/requirements.txt

RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin mentox \
    && mkdir -p /app /work/output /work/jax-cache \
    && chown -R 10001:10001 /app /work

COPY --chown=10001:10001 generate_batch.py /app/generate_batch.py

ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    MPLBACKEND=Agg \
    JAX_COMPILATION_CACHE_DIR=/work/jax-cache \
    JAX_PLATFORMS=cuda \
    XLA_PYTHON_CLIENT_PREALLOCATE=false \
    MENTOX_MATCH_COUNT=30 \
    MENTOX_MATCH_SECONDS=180 \
    MENTOX_CONTROL_FPS=15 \
    MENTOX_RENDER_FPS=15 \
    MENTOX_STATE_STRIDE=15 \
    MENTOX_RENDER_MODE=light \
    MENTOX_UPLOAD_ENABLED=1 \
    MENTOX_BLOB_CONTAINER=synthetic-videos \
    MENTOX_BLOB_PREFIX=messi

USER 10001
WORKDIR /app

CMD ["python", "/app/generate_batch.py"]
