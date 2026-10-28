# Desplegar los modelos de visión en Azure

Esta guía permite que un integrante del equipo despliegue los modelos que ya tienen una entrada válida para Mentox. Los recursos comparten el ACR, el entorno de Container Apps y el perfil T4, pero cada servicio tiene su propia identidad y API.

## Qué se despliega

| Servicio | Entrada | Resultado | Estado |
|---|---|---|---|
| Roboflow Suite | Imagen JPEG, PNG o WebP | Jugadores, árbitro, balón y puntos del campo | Preparado para desplegar |
| SoccerNet TeamSpotting | Clip MP4 de hasta 90 segundos | Candidatos de acciones con tiempo, equipo y confianza | Preparado para desplegar |
| SoccerNet GameState | MP4 mediante TrackLab `ExternalVideo` | Estado, tracking, equipo, dorsal y calibración | Retirado de la demo MESSI; Container App eliminado el 27 de octubre |

GameState conserva su código experimental y sus pruebas, pero no debe
desplegarse para la demo actual. Se continuará con Roboflow y TeamSpotting,
complementados con datos del mismo partido MESSI y procedencia visible.
La integración complementaria está implementada y probada localmente. El
recorrido actualizado con ambos servicios remotos sigue pendiente de ejecutar.
Use [la guía del flujo híbrido](guia-flujo-hibrido-messi.md) para preparar
las variables y comprobar que los datos corresponden al vídeo.

Antes de arrancar el backend desde una terminal que usó GameState, ejecute:

```bash
unset SOCCERNET_GAMESTATE_ENDPOINT SOCCERNET_GAMESTATE_API_KEY
```

Quite también esas variables de cualquier archivo local o configuración que
las vuelva a exportar. Si el backend ya estaba ejecutándose, reinícielo desde
esa terminal: cambiar variables en otra terminal no cambia el proceso activo.
Esto evita que la preparación espere al servicio eliminado. No quite las
variables de Roboflow, TeamSpotting, Blob Storage ni las colas.

Véase [la evidencia del retiro](evidencias/gamestate-retiro-20261027.md).

## Requisitos del equipo

1. Ubuntu o WSL con Docker funcionando.
2. Azure CLI con la sesión iniciada en la suscripción correcta.
3. Bicep no es necesario para estos modelos.
4. Permiso para crear ACR, identidades, roles y Container Apps.
5. Cuota `Consumption-GPU-NC8as-T4` en `northcentralus`.
6. Haber leído las condiciones descritas en los README de `deploy/`.

Compruebe la cuenta antes de continuar:

```bash
az account show --query "{suscripcion:name,estado:state,id:id}" --output table
sudo docker info --format 'Docker Server: {{.ServerVersion}}'
```

## Desplegar todo lo preparado

Ejecute desde la raíz del proyecto:

```bash
export MENTOX_AZURE_RESOURCE_GROUP="rg-mentox-dev"
export MENTOX_AZURE_LOCATION="northcentralus"
export MENTOX_MODEL_API_KEY="$(openssl rand -hex 32)"
export MENTOX_ACCEPT_MODEL_LICENSES=1
export MENTOX_IMAGE_BUILD_MODE=local
export MENTOX_MIN_REPLICAS=0

bash infra/azure/deploy-remaining-vision-models.sh
```

Conserve `MENTOX_MODEL_API_KEY` en un gestor seguro. No la pegue en Git, capturas ni documentos. El modo `local` es intencional: Azure for Students bloqueó ACR Tasks durante la prueba real.

El proceso puede tardar porque construye y sube dos imágenes CUDA. Si se interrumpe después de subir una imagen, repita el wrapper correspondiente con la misma huella:

```bash
export MENTOX_IMAGE_BUILD_MODE=existing
bash infra/azure/deploy-roboflow-suite.sh
```

## Desplegar solo un servicio

```bash
bash infra/azure/deploy-roboflow-suite.sh
bash infra/azure/deploy-soccernet-teamspotting.sh
```

Los scripts son idempotentes: actualizan la aplicación si ya existe. La etiqueta se calcula a partir del contenido del paquete, por lo que un ZIP modificado genera una etiqueta nueva aunque no tenga un commit nuevo.

## Procedimiento de Ariel para TeamSpotting

Ariel debe usar el script operativo específico. Este despliega en escala cero, fuerza una sola revisión activa y separa claramente el encendido del apagado:

```bash
cd /ruta/al/proyecto

export MENTOX_MODEL_API_KEY="$(openssl rand -hex 32)"
export MENTOX_ACCEPT_MODEL_LICENSES=1
export MENTOX_IMAGE_BUILD_MODE=local

bash infra/azure/teamspotting-ariel.sh deploy
bash infra/azure/teamspotting-ariel.sh start
```

`start` deja una réplica T4 encendida y espera a que `/health/ready` responda correctamente. Solo después de ver `TeamSpotting está listo` debe comenzar la prueba. Así el tiempo de carga de CUDA y de los pesos no se mezcla con la latencia del partido.

Para consultar el estado y apagar el servicio al terminar:

```bash
bash infra/azure/teamspotting-ariel.sh status
bash infra/azure/teamspotting-ariel.sh stop
```

El apagado configura `min-replicas=0`; Azure puede tardar unos minutos en retirar la réplica. No se debe confundir el endpoint con una credencial. Ariel debe entregar por canal privado únicamente:

- endpoint HTTPS impreso por el script;
- valor de `MENTOX_MODEL_API_KEY` usado en su despliegue;
- nombre de la aplicación y grupo de recursos;
- salida de `/health/ready` y estado final en escala cero.

No debe entregar contraseña de Azure, sesión de Azure CLI, secreto del cliente ni claves de Storage.

## Probar y entregar evidencia

Cada script imprime su FQDN. Espere a que la réplica termine el arranque en frío y pruebe:

```bash
curl --fail-with-body "https://<fqdn-roboflow>/health/ready"
curl --fail-with-body "https://<fqdn-teamspotting>/health/ready"
```

Las pruebas de inferencia están en los README de cada paquete. Comparta sin secretos:

- salida de ambas sondas de salud;
- identificador de imagen y revisión activa;
- respuesta JSON sobre material autorizado;
- nombre de GPU y tiempo de procesamiento;
- estado de réplica después de volver a escala cero;
- errores completos si alguna operación falla.

## Encender y apagar para la demostración

Para retirar el arranque en frío, encienda únicamente el servicio necesario:

```bash
az containerapp update --resource-group "rg-mentox-dev" \
  --name "ca-mentox-roboflow-dev" --min-replicas 1
```

Al terminar:

```bash
az containerapp update --resource-group "rg-mentox-dev" \
  --name "ca-mentox-roboflow-dev" --min-replicas 0

az containerapp update --resource-group "rg-mentox-dev" \
  --name "ca-mentox-teamspotting-dev" --min-replicas 0
```

Una réplica T4 encendida factura mientras está asignada. ACR Basic conserva un costo pequeño aunque las aplicaciones estén en cero.

## Arranque coordinado con el backend

Para el análisis de fotogramas en la pantalla Partido, el backend usa estas variables:

```bash
export ROBOFLOW_SUITE_ENDPOINT="https://<fqdn-roboflow>"
export ROBOFLOW_SUITE_API_KEY="<clave-privada-del-servicio>"
export SOCCERNET_ENDPOINT="https://<fqdn-teamspotting>"
export SOCCERNET_API_KEY="<clave-privada-teamspotting>"
export SOCCERNET_GAMESTATE_ENDPOINT="https://<fqdn-gamestate>"
export SOCCERNET_GAMESTATE_API_KEY="<clave-privada-gamestate>"
```

Antes de reproducir un MP4, el frontend llama `POST /api/v1/integration/live/models/prepare`. El backend prepara Roboflow, TeamSpotting y GameState en paralelo. El video solo empieza cuando los tres servicios configurados terminan; si alguno sigue iniciando o falla, la interfaz mantiene el video pausado y muestra el error. Use una clave específica por servicio porque pertenecen a cuentas distintas.

## GameState

```bash
export MENTOX_MODEL_API_KEY="$(openssl rand -hex 32)"
export MENTOX_ACCEPT_MODEL_LICENSES=1
export MENTOX_IMAGE_BUILD_MODE=local

bash infra/azure/gamestate-operator.sh deploy
bash infra/azure/gamestate-operator.sh start
```

La guía completa, incluida la carga asíncrona, consulta, descarga de resultados
y apagado, está en `deploy/azure-soccernet-gamestate/README.md`. GameState aún
no se considera verificado: DV-US-36 enumera la evidencia que debe devolver la
persona responsable de la segunda suscripción.

