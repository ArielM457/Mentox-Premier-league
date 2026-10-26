FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04

ARG DEBIAN_FRONTEND=noninteractive
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu128
ARG PLAYER_MODEL_GDRIVE_ID=17PXFNlx-jI7VjVo_vQnB1sONjRyvoB-q
ARG PLAYER_MODEL_SHA256=75b09c377fbf9d0791d23f6cfb689f5aed6eaa43a6818bd1fb884cf7507fffaf

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        ca-certificates \
        curl \
        libglib2.0-0 \
        libgl1 \
        python3.12 \
        python3.12-venv \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /uvx /bin/
COPY requirements.txt /tmp/requirements.txt

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    UV_HTTP_TIMEOUT=300 \
    UV_LINK_MODE=copy

RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv --python python3.12 "${VIRTUAL_ENV}" \
    && uv pip install --python "${VIRTUAL_ENV}/bin/python" \
        --index-url "${TORCH_INDEX_URL}" \
        "torch==2.7.1" "torchvision==0.22.1"

RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --python "${VIRTUAL_ENV}/bin/python" \
        --requirements /tmp/requirements.txt

RUN mkdir -p /models \
    && python -m gdown "${PLAYER_MODEL_GDRIVE_ID}" \
        --output /models/football-player-detection.pt \
    && echo "${PLAYER_MODEL_SHA256}  /models/football-player-detection.pt" | sha256sum --check - \
    && chmod 0444 /models/football-player-detection.pt \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin mentox

COPY --chown=10001:10001 app.py /app/app.py

ENV PYTHONUNBUFFERED=1 \
    YOLO_CONFIG_DIR=/tmp/ultralytics \
    MENTOX_MODEL_PATH=/models/football-player-detection.pt

USER 10001
WORKDIR /app
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

