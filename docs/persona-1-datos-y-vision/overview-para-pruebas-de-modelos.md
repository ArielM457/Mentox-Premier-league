# Overview de Mentox para probar los modelos en GPU

## Propósito de este documento

Este documento entrega contexto a la persona o IA que recibe el proyecto como
ZIP para ejecutar pruebas en una computadora con GPU NVIDIA. Su responsabilidad
es comprobar los modelos, conservar sus salidas y devolver evidencia. No debe
desarrollar la interfaz ni cambiar la arquitectura del proyecto.

Antes de modificar cualquier archivo debe leer `AGENTS.md`. Para ejecutar las
pruebas debe seguir [la guía desde cero](guia-ejecucion-desde-cero.md).

## Qué es Mentox

Mentox es una plataforma experimental de inteligencia para partidos de fútbol.
Recibe eventos deportivos, conserva el estado del partido y prepara información
explicable y sincronizada con vídeo. El objetivo general contempla estadísticas,
narración, personalización y resúmenes, pero la tarea descrita aquí cubre
únicamente la evaluación de modelos de visión y acciones.

El sistema diferencia tres niveles de información:

1. `VisionObservation`: observación propuesta por un modelo, todavía no
   confirmada como hecho deportivo.
2. `FusionCandidate`: relación experimental entre observaciones compatibles.
3. `MatchEvent`: evento normalizado que el núcleo puede aceptar como hecho.

Una predicción de un modelo no se convierte automáticamente en `MatchEvent`.
Debe conservar procedencia, confianza y trazabilidad, y puede ser rechazada.

## Vídeo utilizado

Existen dos clases de vídeo en el trabajo de Persona 1:

- Un vídeo sintético generado con Google Research Football, utilizado en las
  primeras pruebas controladas.
- `experiments/authorized-video/input/2e57b9_0.mp4`, una muestra de demostración
  del ejemplo oficial de Roboflow Sports. Dura 30 segundos, usa H.264, tiene una
  resolución de 1920 × 1080 y 25 FPS. Los comandos `run-real.sh` usan esta
  muestra.

El MP4 está fuera de Git. No debe redistribuirse ni reemplazarse por material de
la Premier League sin autorización.

## Modelos que deben probarse

### Roboflow Sports

La suite preparada usa tres pesos del ejemplo oficial:

- detección de participantes;
- detección especializada del balón;
- puntos clave del campo.

El detector de participantes usa ByteTrack para producir `track_id`. Un
`track_id` solo representa una trayectoria visual: no confirma la identidad ni
el nombre de un jugador. Los campos `player_id` permanecen vacíos sin evidencia
externa.

Con una GPU de 6 GB, el lanzador selecciona automáticamente 640 px, FP16 y
ejecuta el modelo del campo cada 10 cuadros. La ejecución ampliada con los tres
pesos está implementada, pero todavía necesita verificación completa en GPU.

### SoccerNet TeamSpotting

Usa el baseline T-DEED para proponer acciones temporales como pase, conducción,
cabezazo, pase alto, salida, centro, saque de banda, tiro, bloqueo, entrada,
tiro libre y gol. También propone lado izquierdo o derecho, pero no identifica
nominalmente a un jugador.

Una ejecución anterior en CPU sobre el vídeo permitido produjo 127
observaciones en aproximadamente 90,8 segundos. La ruta GPU usa precisión mixta
AMP. La ejecución posterior en una RTX 3060 Laptop de 6 GB produjo las mismas
127 observaciones en aproximadamente 5,66 segundos.

### SoccerNet GameState

El baseline oficial se prepara para evaluar detección, tracking,
reidentificación, calibración, dorsal, equipo y posición 2D. Está separado del
backend porque exige Python 3.9 y dependencias propias.

Actualmente es un smoke oficial sobre datos SoccerNet GSR; todavía no procesa el
MP4 de Mentox ni alimenta la interfaz. Con 6 GB de VRAM se limita automáticamente
a 100 cuadros, pero aun así puede quedarse sin memoria. Un fallo de memoria debe
registrarse como resultado real, no ocultarse.

El dataset GSR no se incluye en el ZIP ni en Git. La guía oficial indica que
TrackLab descarga automáticamente el dataset y los pesos durante la primera
ejecución. Los volúmenes `experiments/soccernet-gamestate/data/` y `models/`
conservan esas descargas. Si se solicita autenticación o aceptación de
condiciones, debe utilizarse una cuenta autorizada y nunca compartir su token.

## Flujo técnico existente

El backend está escrito en Python 3.12 con FastAPI y mantiene límites de
arquitectura hexagonal. El transporte puede funcionar en memoria o con Azure
Event Hubs. Azure Blob Storage conserva artefactos trazables. Ambos servicios
Azure fueron desplegados y probados previamente, pero no son necesarios para
estas pruebas GPU.

El flujo general del proyecto es:

```text
Vídeo permitido
  → modelos aislados en Docker
  → observaciones JSON con tiempo, confianza y procedencia
  → evaluación y posible fusión experimental
  → backend de integración
  → interfaz técnica
```

La persona con la GPU solo ejecuta el tramo entre vídeo y observaciones JSON.
El responsable del proyecto ejecutará después la fusión, el backend y la
interfaz.

## Estado relevante

| Componente | Estado comprobado |
|---|---|
| Backend Python | 161 pruebas aprobadas después de desacoplar conteos generados |
| Azure Event Hubs | Publicación, consumo y duplicado verificados |
| Azure Blob Storage | Escritura, recuperación, SHA-256 y colisión verificados |
| Vídeo sintético | Generado y verificado localmente |
| Vídeo permitido de Roboflow | Procesado previamente en CPU |
| Roboflow con un peso anterior | Ejecutado en CPU; resultados experimentales |
| Roboflow ampliado a tres pesos | Ejecutado en GPU de 6 GB: 750 cuadros, 16.324 cajas y 75 observaciones de campo |
| TeamSpotting | Ejecutado en GPU de 6 GB: 127 observaciones en 5,66 segundos |
| GameState | Contenedor preparado; construcción e inferencia GPU pendientes |
| Interfaz integrada | Existe, pero está fuera del alcance de esta persona |

El documento `estado-actual.md` conserva un corte histórico anterior. Para el
estado reciente de los modelos deben consultarse las evidencias `DV-US-20.md`,
`DV-US-26.md` y `DV-US-27.md`.

## Alcance exacto de la persona con GPU

Debe:

1. Extraer el ZIP y entrar a su directorio raíz.
2. Instalar Docker, NVIDIA Container Toolkit, `uv` y Python 3.12 siguiendo la
   guía.
3. Confirmar que Docker puede ver la GPU.
4. Ejecutar Roboflow sobre el vídeo permitido.
5. Ejecutar TeamSpotting sobre el mismo vídeo.
6. Ejecutar el smoke de GameState si la memoria lo permite.
7. Abrir localmente el vídeo anotado de Roboflow y revisar el resultado.
8. Generar el paquete automático de evidencias.
9. Enviar el paquete, una captura del vídeo anotado y observaciones escritas.

No debe:

- modificar el frontend oficial ni la interfaz técnica;
- ejecutar Compose para validar Play o Pause;
- configurar Azure o compartir credenciales;
- convertir predicciones directamente en `MatchEvent`;
- inventar identidades de jugadores;
- ajustar umbrales solo para aparentar mejores resultados;
- confirmar pesos, vídeos o salidas grandes en Git;
- ejecutar `git push`.

## Comandos principales

Todos se ejecutan desde la raíz extraída del proyecto.

Roboflow:

```bash
mkdir -p experiments/evidence-logs
set -o pipefail
bash experiments/roboflow-sports/run-real.sh 2>&1 | \
  tee experiments/evidence-logs/roboflow-gpu.log
```

TeamSpotting:

```bash
set -o pipefail
bash experiments/soccernet-teamspotting/run-real.sh 2>&1 | \
  tee experiments/evidence-logs/teamspotting-gpu.log
```

GameState:

```bash
set -o pipefail
bash experiments/soccernet-gamestate/run.sh 2>&1 | \
  tee experiments/evidence-logs/gamestate-gpu.log
```

Paquete final:

```bash
bash experiments/collect-model-evidence.sh
```

## Evidencia que debe devolver

Debe enviar:

- el `.tar.gz` creado dentro de `evidencias-generadas/`;
- una captura del vídeo anotado de Roboflow;
- una captura de GameState si genera una visualización;
- confirmación de cuáles comandos terminaron o fallaron;
- una descripción breve de detecciones correctas e incorrectas;
- cualquier mensaje de falta de memoria, bloqueo o reinicio.

El paquete automático contiene información de GPU, versiones, logs,
predicciones JSON, huella del vídeo y hashes de integridad. No contiene el MP4,
el vídeo anotado, pesos ni secretos.

## Documentos de referencia

Lectura mínima para la otra IA:

1. `AGENTS.md`.
2. `docs/persona-1-datos-y-vision/overview-para-pruebas-de-modelos.md`.
3. `docs/persona-1-datos-y-vision/guia-ejecucion-desde-cero.md`.
4. `experiments/roboflow-sports/README.md`.
5. `experiments/soccernet-teamspotting/README.md`.
6. `experiments/soccernet-gamestate/README.md`.
7. `docs/persona-1-datos-y-vision/evidencias/DV-US-20.md`.
8. `docs/persona-1-datos-y-vision/evidencias/DV-US-26.md`.
9. `docs/persona-1-datos-y-vision/evidencias/DV-US-27.md`.

Para comprender todo el proyecto, no solo estas pruebas:

- `docs/README.md`;
- `docs/01-objetivos-y-alcance.md`;
- `docs/02-responsabilidades.md`;
- `docs/03-requisitos.md`;
- `docs/07-decisiones-tomadas.md`;
- `docs/08-formato-de-eventos.md`;
- `docs/persona-1-datos-y-vision/historias-de-usuario.md`;
- `docs/persona-1-datos-y-vision/evidencias/README.md`.

## Regla de cierre

Una ejecución se considera evidencia aunque el modelo falle, siempre que el
log conserve el error y la configuración. No debe declararse un modelo
verificado únicamente porque Docker construyó la imagen: debe completar la
inferencia, producir su salida esperada y permitir revisar el resultado.
