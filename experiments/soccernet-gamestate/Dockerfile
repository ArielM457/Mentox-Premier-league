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

RUN python -m pip install --no-cache-dir --upgrade "pip<26" setuptools wheel \
    && python -m pip install --no-cache-dir \
        --extra-index-url https://download.pytorch.org/whl/cu117 \
        "torch==1.13.1+cu117" \
        "torchvision==0.14.1+cu117"

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

COPY run_official_baseline.sh /usr/local/bin/run-official-baseline
RUN chmod 0555 /usr/local/bin/run-official-baseline

ENV XDG_CACHE_HOME=/models/cache
ENV HF_HOME=/models/huggingface
ENV TORCH_HOME=/models/torch
ENV MPLCONFIGDIR=/models/matplotlib
ENV PYTHONUNBUFFERED=1

WORKDIR /opt/sn-gamestate
ENTRYPOINT ["run-official-baseline"]
