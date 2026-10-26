# Evidencia DV-US-31 · Preparar el despliegue de los modelos restantes

## Estado

**Verificada en Azure.**
**Última revisión:** 25 de octubre de 2026.

Se desplegaron la suite espacial de Roboflow Sports y SoccerNet TeamSpotting en
Azure Container Apps con una Tesla T4. Ambos servicios procesaron el mismo
vídeo autorizado de 30 segundos: la suite recibió un fotograma del segundo 5 y
TeamSpotting recibió el clip completo. GameState continúa separado y no se
presenta como desplegado.

## Alcance y exclusiones

Incluye:

- API Roboflow con pesos de participantes, balón y puntos del campo en una T4;
- API TeamSpotting para clips MP4 autorizados de hasta 90 segundos;
- infraestructura común para ACR privado, identidad, `AcrPull`, entorno, perfil T4 y escala 0–1;
- wrappers individuales y un lanzador de los modelos restantes;
- preflight de GameState que evita crear recursos prematuros;
- guía para integrantes con poca experiencia operativa.

No incluye:

- despliegue de GameState;
- conexión de estas URL con el backend oficial;
- inferencia sobre transmisiones completas o datos Premier League;
- autenticación de producción con Microsoft Entra;
- ejecución simultánea de dos aplicaciones GPU con la cuota actual.

## Archivos

| Archivo | Propósito |
|---|---|
| `infra/azure/deploy-gpu-model-common.sh` | Aprovisionamiento GPU común y endurecido |
| `infra/azure/deploy-remaining-vision-models.sh` | Ejecución ordenada para el equipo |
| `infra/azure/deploy-roboflow-suite.sh` | Parámetros de la suite espacial |
| `infra/azure/deploy-soccernet-teamspotting.sh` | Parámetros de TeamSpotting |
| `infra/azure/preflight-soccernet-gamestate.sh` | Bloqueo explicativo sin crear recursos |
| `deploy/azure-roboflow-suite/` | Imagen, API, dependencias y operación |
| `deploy/azure-soccernet-teamspotting/` | Imagen, API, dependencias y operación |
| `docs/persona-1-datos-y-vision/despliegue-modelos-azure-equipo.md` | Guía completa del equipo |

## Correcciones incorporadas de DV-US-30

1. `northcentralus` como región T4 compatible con la política observada.
2. Ubicación explícita para ACR e identidad, sin heredar `eastus` del grupo.
3. Entorno `WorkloadProfiles`, no Express.
4. Registros deshabilitados para no crear Log Analytics involuntariamente.
5. Construcción local predeterminada porque Azure for Students bloqueó ACR Tasks.
6. Entorno virtual `/opt/venv` para respetar PEP 668 de Ubuntu 24.04.
7. `UV_HTTP_TIMEOUT=300`, caché BuildKit y capas separadas para descargas CUDA.
8. Token temporal de ACR en un directorio Docker efímero con limpieza garantizada.
9. Modo `existing` para reanudar después de haber publicado la imagen.
10. Etiqueta derivada del contenido del paquete para no reutilizar una imagen vieja de un ZIP.
11. ACR privado, administrador deshabilitado e identidad administrada por servicio.
12. Escala predeterminada de cero a una réplica y serialización de inferencia por GPU.

## Integridad y versiones

- Python 3.12.
- CUDA 12.8.1 y cuDNN runtime.
- PyTorch 2.7.1 y Torchvision 0.22.1.
- `football-player-detection.pt`: SHA-256 `75b09c377fbf9d0791d23f6cfb689f5aed6eaa43a6818bd1fb884cf7507fffaf`.
- `football-ball-detection.pt`: SHA-256 `678fbad05134f19c5094cb8d273812ec9c6691228180d46832551ecf99ed2912`.
- `football-pitch-detection.pt`: SHA-256 `28f68f7c4056d6d9b137efd2e7ab5f3c494039380c63831649126ced25628b36`.
- TeamSpotting commit `091fed2fc35c33f7489f3596958a2fe385e37d65`.
- TeamSpotting checkpoint: SHA-256 `ed7c558d575eba1918be8f67813571723962eeff807dba68a12a2d794dd1c72a`.

## Matriz de criterios

| Criterio | Implementación | Estado |
|---|---|---|
| Reutilizar correcciones reales | Script común con región, modo local, venv, timeout y WorkloadProfiles | Verificado por inspección y sintaxis |
| No duplicar infraestructura costosa | ACR, entorno y perfil compartidos; APIs separadas | Verificado por parámetros |
| Preservar integridad de pesos | Identificadores y SHA-256 fijados en Dockerfiles | Verificado durante construcción y arranque remoto |
| Limitar costo | Mínimo 0, máximo 1, sin Log Analytics | Verificado por valores predeterminados |
| Proteger inferencia | Clave fuera de Git, límite de archivo y bloqueo por réplica | Verificado por código |
| No fingir GameState | Preflight termina antes de Azure y explica dependencias | Verificado localmente |
| Instrucciones para el equipo | Guía de despliegue, prueba, evidencia y apagado | Verificado por revisión documental |

## Comandos de verificación local

```bash
bash -n infra/azure/deploy-gpu-model-common.sh
bash -n infra/azure/deploy-roboflow-suite.sh
bash -n infra/azure/deploy-soccernet-teamspotting.sh
bash -n infra/azure/deploy-remaining-vision-models.sh
bash -n infra/azure/preflight-soccernet-gamestate.sh
python3.12 -m py_compile deploy/azure-roboflow-suite/app.py
python3.12 -m py_compile deploy/azure-soccernet-teamspotting/app.py
git diff --check
```

## Verificación real en Azure

Recursos observados:

| Aplicación | Imagen | Perfil | Estado |
|---|---|---|---|
| `ca-mentox-roboflow-dev` | `mentox/roboflow-suite:bb033679830f` | `NC8as-T4` | `Succeeded` |
| `ca-mentox-teamspotting-dev` | `mentox/soccernet-teamspotting:08817e0fac34` | `NC8as-T4` | `Succeeded` |

Entrada autorizada:

- `experiments/authorized-video/input/2e57b9_0.mp4`;
- H.264, 1920×1080, 25 FPS, 750 cuadros y 30 segundos;
- el fotograma espacial se extrajo en el segundo 5;
- no se copió el MP4 ni se guardó ninguna credencial en la evidencia.

Resultado de la suite Roboflow en Tesla T4:

| Modelo solicitado | Ejecución observada | Resultado |
|---|---|---|
| `player` | Sí | 26 detecciones: 22 jugadores, 3 árbitros y 1 balón |
| `ball` | Sí | 0 detecciones en ese fotograma |
| `pitch` | Sí | 1 detección de campo |

La respuesta incluyó los tres nombres dentro de `results`, por lo que una
salida vacía del modelo `ball` no se interpreta como modelo omitido. La
inferencia conjunta tardó `304.851 ms`. El SHA-256 del JSON completo temporal
fue `94426aaad6808b9de7f6f7d3e7bc93605ec0bb04432f2e3a55f8191977f41208`.

Resultado de SoccerNet TeamSpotting en Tesla T4:

- 375 cuadros muestreados a 12,5 FPS;
- `3858.928 ms` de inferencia del modelo;
- 127 candidatos temporales: 48 `drive`, 7 `header`, 16 `high pass`, 7
  `out`, 46 `pass` y 3 `throw in`;
- SHA-256 del JSON completo temporal:
  `f6cea990b7c6ecb01999373e8f0fb91a9d642429ef4263c442c7e33772c9ad2b`.

Comandos usados, con el secreto recuperado en una variable efímera y nunca
impreso:

```bash
ffmpeg -hide_banner -loglevel error -y -ss 00:00:05 \
  -i experiments/authorized-video/input/2e57b9_0.mp4 \
  -frames:v 1 /tmp/mentox-full-flow/frame.jpg

curl --fail-with-body \
  --header "X-API-Key: ${MENTOX_MODEL_API_KEY}" \
  --form "image=@/tmp/mentox-full-flow/frame.jpg;type=image/jpeg" \
  "https://<roboflow-fqdn>/v1/predict?models=all"

curl --fail-with-body \
  --header "X-API-Key: ${MENTOX_MODEL_API_KEY}" \
  --form "video=@experiments/authorized-video/input/2e57b9_0.mp4;type=video/mp4" \
  "https://<teamspotting-fqdn>/v1/predict"
```

Durante el cambio de una aplicación a otra Azure respondió temporalmente con
HTTP `507`. Los reintentos finalizaron correctamente cuando se liberó la T4.
Esto demuestra ejecución secuencial, no simultánea.

## Riesgos y dependencias

- Los pesos no declaran todos una licencia separada; ACR debe permanecer privado hasta resolverlo.
- La cuota observada solo permite una carga T4 a la vez. Roboflow y
  TeamSpotting funcionan por separado, pero no simultáneamente en esta
  suscripción. Para paralelizarlos se necesita más cuota u otras suscripciones.
- Arrancar desde cero añade latencia de descarga de imagen y carga del modelo.
- TeamSpotting consume el clip completo y no forma parte todavía del bucle de
  fotogramas en vivo del frontend. Requiere un worker de ventanas MP4.
- La disponibilidad del perfil no garantiza cuota en otra suscripción.
- GameState depende de DV-US-27 y de un adaptador todavía inexistente.

## Documentación vigente consultada

Context7 confirmó el patrón recomendado de FastAPI para cargar recursos de aprendizaje automático una sola vez mediante `lifespan`: la carga ocurre antes de aceptar solicitudes y el mismo modelo se comparte entre ellas. Las dos APIs aplican ese patrón y ejecutan Uvicorn con un solo worker para no duplicar pesos en la GPU.

## Integración con `develop`

El 25 de octubre de 2026 se creó la rama
`integration/modelos-frontend-20261025` desde `origin/main`. Primero se registraron
los despliegues de modelos en el commit `01a0ba2` y después se fusionó
`origin/develop` sin modificar `main`.

La resolución conservó:

- el escenario sintético en vivo, seguimiento y previa táctica procedentes de
  `develop`;
- el cliente y el panel de visión de `main`;
- una pestaña `Visión IA` dentro del nuevo centro de partidos, sin exponer al
  navegador la clave de las APIs de modelos.

Verificación reproducible posterior a la fusión:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 --extra dev \
  pytest -q apps/backend/tests

npm run lint:frontend
npm run build:frontend
git diff --check
```

Resultados:

- backend: `387 passed, 1 skipped` en 14,54 segundos;
- frontend: lint sin errores y tres advertencias preexistentes sobre
  `set-state-in-effect`;
- frontend: compilación Vite correcta, 56 módulos transformados;
- Git: sin marcadores de conflicto ni errores de espacios.

