#!/usr/bin/env bash
set -euo pipefail

cat >&2 <<'EOF'
SoccerNet GameState NO está listo todavía para desplegar como API de The Prime Moment.

Motivos verificables:
- TrackLab 1.3.24 acepta MP4 mediante ExternalVideo y el adaptador está implementado;
- requiere descargar pesos y datos sujetos a las condiciones de SoccerNet;
- la conversión a VisionObservation está verificada localmente, no con una salida real;
- DV-US-27 y DV-US-33 siguen pendientes de una inferencia GPU completa.

Primero ejecute y documente el smoke local:
  MENTOX_GAMESTATE_VIDEO_PATH=/ruta/video-permitido.mp4 \
    bash experiments/soccernet-gamestate/run.sh

No se crea ningún recurso Azure para evitar costo y una falsa sensación de integración.
Consulte:
  experiments/soccernet-gamestate/README.md
  docs/persona-1-datos-y-vision/evidencias/DV-US-27.md
  docs/persona-1-datos-y-vision/evidencias/DV-US-33.md
EOF
exit 2
