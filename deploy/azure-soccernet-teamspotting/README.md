# SoccerNet TeamSpotting en Azure GPU

Este servicio recibe un clip MP4 autorizado de hasta 90 segundos y devuelve acciones temporales propuestas por T-DEED: pases, centros, tiros, salidas y otras clases del baseline. No recibe una imagen aislada y no identifica jugadores.

El repositorio de SoccerNet TeamSpotting usa GPL-3.0. El checkpoint público empleado por el baseline no declara claramente una licencia separada. Revise las condiciones antes de distribuir la imagen. El servicio no conserva el MP4 y el ACR permanece privado.

## Despliegue

```bash
export MENTOX_MODEL_API_KEY="$(openssl rand -hex 32)"
export MENTOX_ACCEPT_MODEL_LICENSES=1
export MENTOX_IMAGE_BUILD_MODE=local
export MENTOX_MIN_REPLICAS=0
bash infra/azure/deploy-soccernet-teamspotting.sh
```

## Prueba

```bash
curl --fail-with-body --header "X-API-Key: ${MENTOX_MODEL_API_KEY}" \
  --form "video=@experiments/authorized-video/input/2e57b9_0.mp4;type=video/mp4" \
  "https://<fqdn>/v1/predict" \
  --output /tmp/teamspotting-result.json
```

El primer arranque puede tardar por el escalado desde cero. La API serializa las peticiones dentro de una réplica para evitar competencia por VRAM.
