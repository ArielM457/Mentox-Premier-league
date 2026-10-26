# Evidencia técnica de DV-US-33

## Identificación

- **Historia:** DV-US-33 · Adaptar un MP4 a SoccerNet GameState.
- **Estado:** verificada localmente para contratos; inferencia GPU pendiente.
- **Prioridad:** P2.
- **Última actualización:** 25 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.

## Objetivo y alcance

Permitir que el experimento GameState reciba un MP4 sintético o autorizado,
exporte el `TrackerState` de TrackLab a un formato JSONL auditable y convierta
esas filas a `VisionObservation` y `TrackingFrame v1`.

La implementación no afirma que GameState haya terminado una inferencia sobre
MESSI ni que su calidad sea suficiente. Esa verificación requiere GPU, pesos y
una ejecución completa. Tampoco convierte dorsal, equipo o pista en una
identidad nominal.

## Fuentes y decisiones

- SoccerNet GameState permanece fijado al commit
  `1c958345067218297d221e45e1a6405f975f83e0`.
- TrackLab permanece fijado en `1.3.24`.
- La inspección de esa versión confirmó el dataset oficial
  `tracklab.wrappers.ExternalVideo`, que acepta MP4 y crea los metadatos de
  cuadros necesarios. Por ello no se fabrica un dataset SoccerNet artificial.
- El `.pklz` se deserializa únicamente dentro del contenedor controlado Python
  3.9. El backend recibe JSONL y no carga pickle externo.
- Las coordenadas `bbox_pitch` centradas se trasladan al campo fijo en metros.
  Una posición ausente o fuera del campo no produce un `TrackingFrame`.

## Archivos

| Archivo | Función |
|---|---|
| `experiments/soccernet-gamestate/run-gpu.sh` | Monta el MP4 como solo lectura |
| `experiments/soccernet-gamestate/run_official_baseline.sh` | Selecciona `dataset=video` y ejecuta el pipeline |
| `experiments/soccernet-gamestate/export_tracker_state.py` | Exporta `.pklz` a JSONL simple |
| `apps/backend/src/match_intelligence/adapters/sources/soccernet_gamestate.py` | Normaliza observaciones y seguimiento |
| `apps/backend/scripts/adapt_soccernet_gamestate.py` | Comando reproducible de conversión |
| `apps/backend/tests/test_soccernet_gamestate_adapter.py` | Pruebas de tiempos, identidad y calibración ausente |

## Matriz de aceptación

| Criterio | Resultado | Estado |
|---|---|---|
| Aceptar MP4 sin dataset ficticio | Override `dataset=video` de TrackLab | Verificado estáticamente |
| Exportar estado auditable | `.pklz` a JSONL dentro del contenedor | Verificado por compilación |
| Emitir contratos internos | Observaciones y cuadros con tiempo por FPS | Verificado localmente |
| No inventar identidad | `player_id=None` incluso con dorsal | Verificado localmente |
| Tratar calibración ausente | Observación conservada, cuadro omitido | Verificado localmente |
| Inferencia GameState real | Requiere GPU y pesos | Pendiente |

## Comandos y resultados

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest -q \
  apps/backend/tests/test_soccernet_gamestate_adapter.py \
  apps/backend/tests/test_vision_observation_transport.py \
  apps/backend/tests/test_vision_records.py
```

Resultado: **9 pruebas aprobadas en 0,34 segundos**.

```bash
python3.12 -m py_compile \
  experiments/soccernet-gamestate/export_tracker_state.py

bash -n \
  experiments/soccernet-gamestate/run.sh \
  experiments/soccernet-gamestate/run-gpu.sh \
  experiments/soccernet-gamestate/run_official_baseline.sh

git diff --check
```

Resultado: compilación, sintaxis y whitespace aprobados.

## Limitaciones y siguiente verificación

1. Construir el contenedor GameState en el equipo GPU.
2. Ejecutar primero un tramo corto de un MP4 MESSI.
3. Registrar GPU, VRAM, duración, cantidad de observaciones y cuadros calibrados.
4. Revisar visualmente equipo, dorsal, pista y estabilidad de `track_id`.
5. Publicar una muestra mediante el transporte de observaciones.
6. Solo después evaluar un despliegue Azure; el adaptador local no demuestra
   que el pipeline completo quepa en una T4 ni que opere en tiempo real.
