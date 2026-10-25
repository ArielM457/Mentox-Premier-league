#!/usr/bin/env bash
set -euo pipefail

cat >&2 <<'EOF'
SoccerNet GameState NO está listo para desplegar como API de Mentox.

Motivos verificables:
- el baseline oficial recibe un dataset SoccerNet GSR/TrackLab, no un MP4 arbitrario;
- requiere descargar pesos y datos sujetos a las condiciones de SoccerNet;
- aún falta convertir su salida a VisionObservation y probar el adaptador con vídeo autorizado;
- DV-US-27 sigue pendiente de una ejecución completa.

Primero ejecute y documente el smoke local:
  bash experiments/soccernet-gamestate/run.sh

No se crea ningún recurso Azure para evitar costo y una falsa sensación de integración.
Consulte:
  experiments/soccernet-gamestate/README.md
  docs/persona-1-datos-y-vision/evidencias/DV-US-27.md
EOF
exit 2
