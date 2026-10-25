# Evidencia DV-US-31 · Preparar el despliegue de los modelos restantes

## Estado

**Implementada, pendiente de verificación en Azure.**  
**Última revisión:** 25 de octubre de 2026.

Se prepararon imágenes y scripts reproducibles para la suite espacial de Roboflow Sports y SoccerNet TeamSpotting. No se afirma que estos dos servicios estén desplegados hasta ejecutar los comandos contra Azure y conservar sus respuestas. GameState se bloquea de manera explícita porque todavía no acepta un MP4 de Mentox.

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
- verificación remota de las imágenes nuevas.

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
| Preservar integridad de pesos | Identificadores y SHA-256 fijados en Dockerfiles | Pendiente de construcción remota |
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

## Comando de verificación en Azure pendiente

```bash
export MENTOX_MODEL_API_KEY="$(openssl rand -hex 32)"
export MENTOX_ACCEPT_MODEL_LICENSES=1
export MENTOX_IMAGE_BUILD_MODE=local
export MENTOX_MIN_REPLICAS=0
bash infra/azure/deploy-remaining-vision-models.sh
```

Se debe adjuntar la salida sin secretos y probar `/health/ready` e inferencia antes de cambiar el estado a verificada en Azure.

## Riesgos y dependencias

- Los pesos no declaran todos una licencia separada; ACR debe permanecer privado hasta resolverlo.
- Una sola T4 puede cargar la suite Roboflow, pero las APIs no comparten una réplica entre sí.
- Arrancar desde cero añade latencia de descarga de imagen y carga del modelo.
- TeamSpotting consume el clip completo y no sustituye todavía un worker por segmentos en vivo.
- La disponibilidad del perfil no garantiza cuota en otra suscripción.
- GameState depende de DV-US-27 y de un adaptador todavía inexistente.

## Documentación vigente consultada

Context7 confirmó el patrón recomendado de FastAPI para cargar recursos de aprendizaje automático una sola vez mediante `lifespan`: la carga ocurre antes de aceptar solicitudes y el mismo modelo se comparte entre ellas. Las dos APIs aplican ese patrón y ejecutan Uvicorn con un solo worker para no duplicar pesos en la GPU.

