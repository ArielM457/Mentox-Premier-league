# Suite Roboflow Sports en Azure GPU

Este servicio carga en una sola T4 los pesos de jugadores, balón y puntos del campo. Acepta una imagen y permite ejecutar uno, varios o los tres modelos. No identifica personas ni infiere eventos temporales.

Los pesos se descargan desde los identificadores usados por Roboflow Sports y se verifican con SHA-256. El código de Roboflow Sports declara MIT; Ultralytics usa AGPL-3.0-or-later y los pesos no declaran claramente una licencia separada. Este paquete es experimental, el ACR queda privado y el equipo debe revisar las condiciones antes de una distribución pública.

## Despliegue

```bash
export MENTOX_MODEL_API_KEY="$(openssl rand -hex 32)"
export MENTOX_ACCEPT_MODEL_LICENSES=1
export MENTOX_IMAGE_BUILD_MODE=local
export MENTOX_MIN_REPLICAS=0
bash infra/azure/deploy-roboflow-suite.sh
```

La construcción local evita el bloqueo de ACR Tasks observado en Azure for Students. No guarde la clave en Git.

## Prueba

```bash
curl --fail-with-body --header "X-API-Key: ${MENTOX_MODEL_API_KEY}" \
  --form "image=@/ruta/fotograma-autorizado.jpg" \
  "https://<fqdn>/v1/predict?models=all"
```

También puede usar `models=player`, `models=ball,pitch` o cualquier combinación válida. Las cajas y puntos se normalizan entre 0 y 1. La API no conserva imágenes.
