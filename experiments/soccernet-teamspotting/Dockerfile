FROM python:3.12-slim

ARG DEBIAN_FRONTEND=noninteractive
ARG SOCCERNET_COMMIT=091fed2fc35c33f7489f3596958a2fe385e37d65
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        git \
        libglib2.0-0 \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir \
        --index-url "${TORCH_INDEX_URL}" \
        "torch==2.5.0" \
        "torchvision==0.20.0"

RUN python -m pip install --no-cache-dir \
        "gdown==6.4.2" \
        "numpy==2.1.2" \
        "opencv-python-headless==4.10.0.84" \
        "pillow==11.0.0" \
        "timm==1.0.11"

RUN git clone https://github.com/SoccerNet/sn-teamspotting.git /opt/sn-teamspotting \
    && git -C /opt/sn-teamspotting checkout "${SOCCERNET_COMMIT}" \
    && sed -i 's/pretrained=True/pretrained=False/' /opt/sn-teamspotting/model/model.py \
    && sed -i 's/self\._pred_fine = self\._pred_fine\.cuda()/self._pred_fine = self._pred_fine.to(next(self.parameters()).device)/' /opt/sn-teamspotting/model/model.py \
    && sed -i 's/torch\.zeros(pred\.shape\[0\], pred\.shape\[1\], 1 + (pred\.shape\[2\]-1) \* 2)/torch.zeros(pred.shape[0], pred.shape[1], 1 + (pred.shape[2]-1) * 2, device=pred.device)/' /opt/sn-teamspotting/model/modules.py

RUN mkdir -p /models \
    && gdown \
        1Dp2tqDIrNwLmfuUJPPhpz1db7DZjxIzd \
        --output /models/checkpoint_best.pt \
    && chmod 0444 /models/checkpoint_best.pt

COPY run_inference.py /opt/sn-teamspotting/mentox_inference.py

ENV PYTHONUNBUFFERED=1
ENV MENTOX_VISION_DEVICE=cpu

WORKDIR /opt/sn-teamspotting
ENTRYPOINT ["python", "mentox_inference.py"]
