FROM python:3.12-slim

ARG DEBIAN_FRONTEND=noninteractive
ARG SPORTS_COMMIT=42c80c06b6b65a7f89455b89fe31cdf4c38ba227
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        git \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir \
        --index-url "${TORCH_INDEX_URL}" \
        "torch==2.14.1" \
        "torchvision==0.29.1"

RUN python -m pip install --no-cache-dir \
        "gdown==6.4.2" \
        "supervision==0.30.9" \
        "ultralytics==8.4.177"

RUN python -m pip install --no-cache-dir "lap==0.5.13"

RUN git clone https://github.com/roboflow/sports.git /opt/roboflow-sports \
    && git -C /opt/roboflow-sports checkout "${SPORTS_COMMIT}" \
    && python -m pip install --no-cache-dir --no-deps /opt/roboflow-sports

RUN mkdir -p /models \
    && gdown \
        17PXFNlx-jI7VjVo_vQnB1sONjRyvoB-q \
        --output /models/football-player-detection.pt \
    && gdown \
        1isw4wx-MK9h9LMr36VvIWlJD6ppUvw7V \
        --output /models/football-ball-detection.pt \
    && gdown \
        1Ma5Kt86tgpdjCTKfum79YMgNnSjcoOyf \
        --output /models/football-pitch-detection.pt \
    && chmod 0444 /models/*.pt

COPY run_inference.py /opt/mentox/run_inference.py

ENV PYTHONUNBUFFERED=1
ENV YOLO_CONFIG_DIR=/tmp/ultralytics
ENV MENTOX_VISION_DEVICE=cpu

WORKDIR /opt/mentox
ENTRYPOINT ["python", "/opt/mentox/run_inference.py"]
