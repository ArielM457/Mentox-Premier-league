FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04

ARG DEBIAN_FRONTEND=noninteractive
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu128
ARG SOCCERNET_COMMIT=091fed2fc35c33f7489f3596958a2fe385e37d65
ARG CHECKPOINT_GDRIVE_ID=1Dp2tqDIrNwLmfuUJPPhpz1db7DZjxIzd
ARG CHECKPOINT_SHA256=ed7c558d575eba1918be8f67813571723962eeff807dba68a12a2d794dd1c72a

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates git libglib2.0-0 libgl1 python3.12 python3.12-venv \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /uvx /bin/
COPY requirements.txt /tmp/requirements.txt
ENV VIRTUAL_ENV=/opt/venv PATH="/opt/venv/bin:${PATH}" UV_HTTP_TIMEOUT=300 UV_LINK_MODE=copy

RUN uv venv --python python3.12 "${VIRTUAL_ENV}" \
    && uv pip install --python "${VIRTUAL_ENV}/bin/python" --index-url "${TORCH_INDEX_URL}" \
        "torch==2.7.1" "torchvision==0.22.1"
RUN uv pip install --python "${VIRTUAL_ENV}/bin/python" --requirements /tmp/requirements.txt

RUN git clone https://github.com/SoccerNet/sn-teamspotting.git /opt/sn-teamspotting \
    && git -C /opt/sn-teamspotting checkout "${SOCCERNET_COMMIT}" \
    && sed -i 's/pretrained=True/pretrained=False/' /opt/sn-teamspotting/model/model.py \
    && sed -i 's/self\._pred_fine = self\._pred_fine\.cuda()/self._pred_fine = self._pred_fine.to(next(self.parameters()).device)/' /opt/sn-teamspotting/model/model.py \
    && sed -i 's/torch\.zeros(pred\.shape\[0\], pred\.shape\[1\], 1 + (pred\.shape\[2\]-1) \* 2)/torch.zeros(pred.shape[0], pred.shape[1], 1 + (pred.shape[2]-1) * 2, device=pred.device)/' /opt/sn-teamspotting/model/modules.py

RUN mkdir -p /models \
    && python -m gdown "${CHECKPOINT_GDRIVE_ID}" --output /models/checkpoint_best.pt \
    && echo "${CHECKPOINT_SHA256}  /models/checkpoint_best.pt" | sha256sum --check - \
    && chmod 0444 /models/checkpoint_best.pt \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin mentox

COPY --chown=10001:10001 app.py /opt/sn-teamspotting/mentox_api.py
ENV PYTHONUNBUFFERED=1 YOLO_CONFIG_DIR=/tmp/ultralytics
USER 10001
WORKDIR /opt/sn-teamspotting
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "mentox_api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

