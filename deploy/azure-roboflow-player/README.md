# Detector de jugadores en Azure Container Apps GPU

Este paquete despliega únicamente `football-player-detection.pt` como API HTTP en una NVIDIA T4 de Azure Container Apps. Detecta participantes, porteros, árbitros y balón según las clases del peso; no identifica nombres reales.

## Antes de desplegar

- La suscripción debe tener cuota para `Consumption-GPU-NC8as-T4` en la región elegida.
- Azure Container Apps GPU requiere un entorno con perfiles de carga.
- El peso se descarga desde el identificador usado por el ejemplo oficial de Roboflow Sports y se verifica mediante SHA-256.
- El repositorio de Roboflow Sports declara MIT y Ultralytics usa AGPL-3.0-or-later. El peso no declara de forma inequívoca una licencia separada. Revise esas condiciones antes de subir la imagen a ACR.
- ACR permanece privado y no habilita el usuario administrador.

## Desplegar

```bash
cd /ruta/Mentox-Premier-league

export MENTOX_AZURE_RESOURCE_GROUP="rg-mentox-dev"
export MENTOX_AZURE_LOCATION="northcentralus"
export MENTOX_MODEL_API_KEY="$(openssl rand -hex 32)"
export MENTOX_ACCEPT_MODEL_LICENSES=1
export MENTOX_IMAGE_BUILD_MODE=local

bash infra/azure/deploy-roboflow-player.sh
```

La clave existe solo en la terminal y como secreto de Container Apps. No la escriba en `.env`, documentación o evidencias.

El script:

1. confirma la suscripción activa y registra proveedores;
2. verifica que la región anuncie el perfil T4;
3. crea un ACR Basic privado si no existe;
4. construye la imagen de Python 3.12 y CUDA en ACR o con Docker local;
5. crea una identidad administrada con `AcrPull`;
6. crea un entorno `WorkloadProfiles` sin Log Analytics y agrega el perfil GPU si faltan;
7. crea o actualiza la aplicación con máximo una réplica.

`MENTOX_IMAGE_BUILD_MODE=local` construye la imagen con Docker y la sube mediante un token temporal porque Azure for Students puede bloquear ACR Tasks. El script solicitará la contraseña de `sudo` cuando el usuario local no tenga acceso directo al daemon. Use `acr` solamente en suscripciones que permitan `az acr build`.

`MENTOX_IMAGE_BUILD_MODE=existing` omite la construcción únicamente si la etiqueta derivada del commit actual ya existe en el ACR. Es útil para reanudar el aprovisionamiento después de una interrupción posterior a la publicación de la imagen.

## Probar

El endpoint exacto aparece al final del despliegue:

```bash
curl "https://<fqdn>/health/ready"

curl --fail-with-body \
  --header "X-API-Key: ${MENTOX_MODEL_API_KEY}" \
  --form "image=@/ruta/fotograma-autorizado.jpg" \
  "https://<fqdn>/v1/predict"
```

La respuesta contiene cajas normalizadas, clase, confianza y duración de inferencia. No conserva la imagen.

## Encender antes del partido y apagar después

El valor predeterminado es mínimo cero. La primera solicitud puede tardar mientras Azure inicia la réplica y carga el peso. Antes de una demostración:

```bash
az containerapp update \
  --resource-group "${MENTOX_AZURE_RESOURCE_GROUP}" \
  --name "ca-mentox-player-dev" \
  --min-replicas 1
```

Al finalizar:

```bash
az containerapp update \
  --resource-group "${MENTOX_AZURE_RESOURCE_GROUP}" \
  --name "ca-mentox-player-dev" \
  --min-replicas 0
```

Confirme en Azure Cost Management que la réplica bajó a cero. ACR y registros pueden conservar costos pequeños aunque no exista una réplica GPU activa.

## Límites de esta primera versión

- Solo procesa imágenes; la segmentación del vídeo y conexión con el backend se agregan después de medir esta API.
- No incluye los pesos `ball`, `pitch`, TeamSpotting ni GameState.
- La clave HTTP es una protección de demostración. Para producción se debe usar autenticación de Microsoft Entra o ingreso interno.
- La disponibilidad regional no garantiza cuota para Azure for Students.

