#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
SoccerNet GameState dispone ahora de un paquete experimental de despliegue.

Antes de crear recursos:
- lea deploy/azure-soccernet-gamestate/README.md;
- confirme cuota Consumption-GPU-NC8as-T4 en la suscripción seleccionada;
- acepte las condiciones de SoccerNet, TrackLab, pesos y datos aplicables;
- use únicamente un MP4 sintético o autorizado;
- recuerde que DV-US-36 sigue pendiente de verificación real en Azure.

Para desplegar:
  export MENTOX_MODEL_API_KEY="$(openssl rand -hex 32)"
  export MENTOX_ACCEPT_MODEL_LICENSES=1
  export MENTOX_IMAGE_BUILD_MODE=local
  bash infra/azure/gamestate-operator.sh deploy

Este preflight no crea recursos ni genera costos.
EOF
