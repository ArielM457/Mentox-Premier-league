FROM python:3.9-slim

ARG DEBIAN_FRONTEND=noninteractive
ARG GAMESTATE_COMMIT=1c958345067218297d221e45e1a6405f975f83e0

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        build-essential \
        ffmpeg \
        git \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-api.txt /tmp/requirements-api.txt
RUN python -m pip install --no-cache-dir --upgrade "pip<26" setuptools wheel \
    && python -m pip install --no-cache-dir \
        --extra-index-url https://download.pytorch.org/whl/cu117 \
        "torch==1.13.1+cu117" \
        "torchvision==0.14.1+cu117" \
    && python -m pip install --no-cache-dir \
        --requirement /tmp/requirements-api.txt

RUN git clone https://github.com/SoccerNet/sn-gamestate.git /opt/sn-gamestate \
    && git -C /opt/sn-gamestate checkout "${GAMESTATE_COMMIT}" \
    && python -m pip install --no-cache-dir --no-deps -e /opt/sn-gamestate \
    && python -m pip install --no-cache-dir \
        "tracklab==1.3.24" \
        "easyocr==1.7.1" \
        "soccernet==0.1.55" \
        "lightning==2.0.9" \
        "numpy==1.26.4" \
        "transformers==4.35.2" \
        "tokenizers==0.15.2" \
        "openmim==0.3.9" \
        "mmocr==1.0.1" \
        "mmdet~=3.1.0" \
        "prtreid @ git+https://github.com/VlSomers/prtreid" \
        "torchreid @ git+https://github.com/VlSomers/bpbreid" \
    && python -m pip install --no-cache-dir --no-deps \
        -e /opt/sn-gamestate/plugins/calibration \
    && python -m mim install "mmcv==2.0.1"

RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin prime \
    && mkdir -p /models/cache /models/huggingface /models/torch \
        /models/matplotlib /work/analyses \
    && chown -R prime:prime /models /work

ENV XDG_CACHE_HOME=/models/cache \
    HF_HOME=/models/huggingface \
    TORCH_HOME=/models/torch \
    MPLCONFIGDIR=/models/matplotlib \
    PYTHONUNBUFFERED=1 \
    HOME=/home/prime

COPY preload_models.py /opt/prime/preload_models.py
RUN python /opt/prime/preload_models.py \
    && chown -R prime:prime /models

# Keep this after weight preloading so patch changes reuse the checkpoint layer.
COPY patch_calibration.py /opt/prime/patch_calibration.py
RUN python /opt/prime/patch_calibration.py --root /opt/sn-gamestate

COPY --chown=10001:10001 run_analysis.sh /opt/prime/run_analysis.sh
COPY --chown=10001:10001 export_tracker_state.py /opt/prime/export_tracker_state.py
COPY --chown=10001:10001 app.py /opt/prime/app.py
RUN chmod 0555 /opt/prime/run_analysis.sh

USER 10001
WORKDIR /opt/sn-gamestate
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app:app", "--app-dir", "/opt/prime", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

