# Evidencia técnica de DV-US-25

## Identificación

- **Historia:** DV-US-25 · Controlar observaciones con la reproducción.
- **Estado:** implementada y verificada localmente; recorrido visual con Compose pendiente.
- **Fecha:** 14 de octubre de 2026.
- **Requisitos relacionados:** RF-20, RF-37, DV-RF-05, DV-RF-10 y DV-RNF-02.

## Resultado

La reproducción de observaciones precomputadas dejó de comenzar al arrancar
Compose. El backend conserva una sesión con estado `paused` o `playing`, posición
del vídeo y cursor. Solo publica el tramo temporal cruzado mientras la sesión está
activa.

```text
Play/pausa/salto del vídeo
          ↓
Coordinador de reproducción del backend
          ↓
memoria o vision-observations en Event Hubs
          ↓
consumidor → cola acotada → WebSocket → interfaz técnica
```

El cambio no convierte observaciones en `MatchEvent`. Roboflow y SoccerNet
conservan sus identificadores, origen, clase y tiempo del vídeo.

## Criterios cubiertos

| Criterio | Implementación y comprobación |
|---|---|
| No publicar antes de Play | `advance` no cambia posición ni publica mientras la sesión está pausada |
| Pausar | Publica como máximo hasta la posición recibida y luego bloquea avances |
| Saltar | Recalcula el cursor con búsqueda binaria y no republica el historial |
| Reiniciar | Vuelve a cero, pausa la sesión y reinicia sus contadores |
| Conservar transporte | El coordinador usa `VisionObservationRuntime`, común a memoria y Azure |
| Actualizar la interfaz | Los controles del vídeo invocan la API y WebSocket recibe únicamente resultados transportados |

## Archivos

- `apps/backend/src/match_intelligence/application/observation_playback.py`
- `apps/backend/src/match_intelligence/adapters/http/integration_router.py`
- `experiments/video_sync_diagnostic/static/app.js`
- `compose.integration.yml`
- `apps/backend/tests/test_observation_playback.py`
- `apps/backend/tests/test_integrated_pipeline_api.py`

## Decisiones

- El backend es la autoridad de la sesión; el navegador no publica observaciones.
- En Azure, el backend agrupa hasta 100 observaciones de una misma fuente por envío.
- El salto reconstruye el cursor, pero no presenta resultados históricos como nuevos.
- Compose ya no inicia un worker autónomo que ignore el estado del vídeo.
- La interfaz es una herramienta de diagnóstico y no modifica el frontend oficial.
- La interfaz no consulta ni muestra la ventana histórica al abrirse; el panel en
  vivo comienza vacío y solo presenta observaciones que cruzaron el transporte.
- La prueba reproduce resultados calculados previamente; la captura real de un
  worker conectado a una señal entrante sigue teniendo su propio reloj y retraso.

## Verificación reproducible

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 pytest -q

node --check experiments/video_sync_diagnostic/static/app.js
docker-compose -f compose.integration.yml config --quiet
```

Resultado vigente: `167 passed in 1.24s`.

Las pruebas específicas del coordinador, API e interfaz terminaron con
La comprobación específica más reciente terminó con `15 passed`; también
aprobaron `compileall`, `node --check`, la validación de
Compose y `git diff --check`.

## Prueba visual pendiente

```bash
sudo docker-compose -f compose.integration.yml up --build
```

Recorrido esperado:

1. Abrir `http://127.0.0.1:8018` y comprobar que el panel en vivo está vacío.
2. Pulsar Play y confirmar que llegan observaciones del tramo reproducido.
3. Pulsar pausa y confirmar que el contador deja de crecer.
4. Saltar hacia adelante o atrás y comprobar que el historial no reaparece como nuevo.
5. Reiniciar y confirmar posición cero, sesión pausada y panel vacío.

## Limitaciones

- En Azure, incluso los envíos agrupados pueden acumular retraso; Event Hubs
  desacopla el flujo, pero no acelera la inferencia ni el productor.
- El navegador puede omitir elementos visuales si su cola se llena, sin bloquear
  al productor ni perder el registro retenido por Event Hubs.
