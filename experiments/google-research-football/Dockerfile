FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive
ARG GRF_COMMIT=3d9e754720a95621bba6475c4d3b0d56fe919014

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        build-essential \
        cmake \
        ffmpeg \
        git \
        libboost-all-dev \
        libdirectfb-dev \
        libgl1-mesa-dev \
        libglib2.0-0 \
        libsdl2-dev \
        libsdl2-gfx-dev \
        libsdl2-image-dev \
        libsdl2-ttf-dev \
        libsm6 \
        libst-dev \
        libxext6 \
        libxrender1 \
        mesa-utils \
        python3-pip \
        x11vnc \
        xvfb \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir \
        "pip<24.1" \
        "setuptools<66" \
        wheel \
        psutil

RUN git clone https://github.com/google-research/football.git /opt/gfootball \
    && git -C /opt/gfootball checkout "${GRF_COMMIT}" \
    && python3 -m pip install --no-cache-dir /opt/gfootball

# GRF importa six en football_action_set.py, pero la revisión fijada no lo
# declara entre sus dependencias instalables.
RUN python3 -m pip install --no-cache-dir "six==1.17.0"

COPY generate_video.py /opt/mentox/generate_video.py

ENV SDL_AUDIODRIVER=dummy
ENV SDL_VIDEODRIVER=dummy
ENV PYTHONUNBUFFERED=1

WORKDIR /opt/mentox
ENTRYPOINT ["python3", "/opt/mentox/generate_video.py"]
