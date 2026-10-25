# Evidencia técnica de DV-US-18

## Identificación

- **Historia:** DV-US-18 · Validar sincronización mediante una interfaz mínima.
- **Estado:** implementada y verificada automáticamente; recorrido visual manual pendiente.
- **Prioridad:** P0.
- **Última verificación:** 13 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión, en coordinación futura con Persona 4.
- **Eleva:** DV-US-10 y DV-RF-10.

## Decisión de integración

No se modificó `apps/frontend` porque otra persona trabaja en la interfaz oficial. Se creó una aplicación aislada en `experiments/video_sync_diagnostic/` que utiliza FastAPI, HTML y JavaScript sin sistema de construcción adicional.

La API experimental importa `VideoSynchronizedReplay` desde el backend real. Por ello, la página no vuelve a implementar la política de sincronización en JavaScript. El navegador comunica las operaciones de reproducción, pausa, avance, salto y reinicio al caso de uso Python.

## Flujo implementado

```text
MP4 sintético de DV-US-17
          │
          ▼
Página aislada de diagnóstico
          │ controles y currentTime
          ▼
API FastAPI experimental
          │
          ▼
VideoSynchronizedReplay de DV-US-10
     ├── avance normal → canal visible
     └── seek/restart  → estado reconstruido
```

## Archivos

| Archivo | Función |
|---|---|
| `experiments/video_sync_diagnostic/app.py` | API experimental, sesión y servicio del MP4 |
| `experiments/video_sync_diagnostic/static/index.html` | Página de diagnóstico independiente |
| `experiments/video_sync_diagnostic/static/app.js` | Controles del vídeo, llamadas a API y exportación JSON |
| `experiments/video_sync_diagnostic/static/styles.css` | Presentación adaptable de la herramienta |
| `experiments/video_sync_diagnostic/test_app.py` | Pruebas del contrato HTTP y de la sesión |
| `experiments/video_sync_diagnostic/README.md` | Ejecución y recorrido de validación manual |
| `docs/persona-1-datos-y-vision/evidencias/dv-us-18-session-log.json` | Primer registro real de reproducción completa en navegador |
| `docs/persona-1-datos-y-vision/evidencias/dv-us-18-session-log (1).json` | Segundo registro real de saltos, reconstrucción y reinicio |

No se modificó ningún archivo bajo `apps/frontend`.

## Contrato experimental

| Método y ruta | Efecto |
|---|---|
| `POST /api/integration/video-sync/session` | Reinicia la sesión aislada |
| `GET /api/integration/video-sync/session` | Consulta posición, cursor, visibles y reconstrucción |
| `POST /api/integration/video-sync/play` | Cambia el coordinador a reproducción |
| `POST /api/integration/video-sync/pause` | Impide el avance y eventos futuros |
| `POST /api/integration/video-sync/advance` | Entrega eventos cruzados durante reproducción normal |
| `POST /api/integration/video-sync/seek` | Reconstruye el prefijo sin republicarlo como visible |
| `POST /api/integration/video-sync/restart` | Pausa y vuelve a posición y estado iniciales |
| `GET /api/integration/video-sync/log` | Exporta acciones y estado sin secretos |

Este contrato pertenece al experimento. No se declara como API pública aprobada para el producto.

## Datos mostrados

La interfaz presenta:

- `currentTime` del elemento HTML `video`;
- `video_time_ms` procesado por Python;
- estado `playing` o `paused`;
- cursor y total de eventos;
- `event_id`, `clock_ms`, `video_time_ms`, `source`, `player_id` y `track_id`;
- conteo e identificadores del estado reconstruido;
- procedencia `manual_alignment`;
- base temporal `provided_event_timestamp`;
- aviso visible de que no existe detección automática.

Los cinco eventos del experimento se alinean manualmente en 5, 10, 15, 20 y 25 segundos. Se utilizan para probar relojes y controles; no afirman que un modelo haya reconocido esas acciones en las imágenes.

## Cobertura de criterios de aceptación

| Criterio | Evidencia | Estado |
|---|---|---|
| Vídeo permitido y campos temporales | MP4 de DV-US-17, telemetría y tarjetas estructuradas | Implementado; revisión visual pendiente |
| Pausa impide eventos futuros | Prueba de avance hasta 6 s, pausa y solicitud hasta 16 s | Cumplido automáticamente |
| Saltos reconstruyen sin mensajes históricos | Endpoint `seek`, canal visible vacío y cuatro eventos reconstruidos a 21 s | Cumplido automáticamente |
| Reinicio vuelve a cero | Posición, cursor, reconstrucción y visibles vuelven a cero | Cumplido automáticamente |
| Diferenciar alineación de detección | Aviso en pantalla y campos `manual_alignment` y `not_automatic_detection` | Cumplido automáticamente |
| Capturas y registro JSON | Exportación implementada; capturas y archivo de sesión requieren recorrido en navegador | Pendiente manual |

## Pruebas ejecutadas

Pruebas específicas:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest -q \
  experiments/video_sync_diagnostic/test_app.py \
  apps/backend/tests/test_video_sync.py
```

Resultado:

```text
...................                                                      [100%]
20 passed in 0.26s
```

Suite completa:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 pytest -q
```

Resultado:

```text
........................................................................ [ 51%]
.....................................................................    [100%]
141 passed in 0.67s
```

La aplicación Uvicorn inició correctamente en `127.0.0.1:8018`. La comprobación HTTP entre procesos no pudo realizarse desde la herramienta de ejecución aislada; el contrato JSON fue ejercitado directamente como aplicación ASGI mediante `httpx.ASGITransport`. La página y el `FileResponse` del MP4 se comprobaron directamente, incluida la presencia del HTML, el tipo `video/mp4` y el tamaño de 434.492 bytes.

## Context7

Se consultó la documentación de React 19.2.8. Confirmó que React conecta directamente eventos multimedia como `play`, `pause`, `seeked` y `timeupdate` al elemento de vídeo. La interfaz aislada no usa React para evitar interferir con el frontend oficial, pero conserva la misma separación basada en eventos nativos del medio y llamadas explícitas a la API.

## Ejecución manual pendiente

### Primer registro recibido

El archivo `dv-us-18-session-log.json` fue exportado desde la página real y validado como JSON. Tiene 22.228 bytes y SHA-256 `050c97816012f89d74e672bda6692b26e9057f957b10fe1cdf80c3000a0ae97c`.

Contiene una creación de sesión, una reproducción, 113 avances y una pausa final. Los eventos fueron entregados una sola vez y en orden al cruzar aproximadamente 5, 10, 15, 20 y 25 segundos. El estado final quedó pausado en 29,994 segundos (`video_time_ms=29994`) con cursor `5 / 5`. No contiene coincidencias con nombres habituales de secretos, tokens, credenciales, suscripciones o datos personales.

Este primer registro demuestra reproducción progresiva, pero no contiene acciones `seek` ni `restart`. Por ello no cierra todavía la comprobación manual de salto, retroceso y reinicio.

### Segundo registro recibido

El archivo `dv-us-18-session-log (1).json` fue validado como JSON. Tiene 6.311 bytes y SHA-256 `229743785ef53b7b1188b465c570fda3fc2947424648a1efd9c912385d2541eb`. No contiene coincidencias con nombres habituales de secretos, tokens, credenciales, suscripciones o datos personales.

El registro conserva tres saltos y un reinicio:

| Operación | Posición | Resultado registrado |
|---|---:|---|
| Salto hacia adelante | 19,489 s (`19489 ms`) | Tres eventos reconstruidos y `visible_history_republished=false` |
| Reproducción posterior | Hasta 21,342 s (`21342 ms`) | Continuación desde el cursor reconstruido |
| Salto hacia atrás | 8,184 s (`8184 ms`) | Un evento reconstruido y ningún historial republicado |
| Reproducción posterior | Hasta 12,161 s (`12161 ms`) | Continuación desde el tramo retrocedido |
| Reinicio | 0 ms | Pausado, cursor cero, reconstrucción vacía y canal visible vacío |

El estado final declara `provided_event_timestamp` y `not_automatic_detection`. Por tanto, el segundo registro completa la comprobación manual de salto, retroceso y reinicio. Solo falta conservar la secuencia de capturas requerida por el criterio documental antes de cambiar el estado a verificada en integración.

### Recorrido que falta registrar

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  uvicorn video_sync_diagnostic.app:app \
  --app-dir experiments \
  --host 127.0.0.1 \
  --port 8018
```

Después se abre <http://127.0.0.1:8018> y se sigue el recorrido de `experiments/video_sync_diagnostic/README.md`. Para cerrar la verificación en integración se deben conservar:

1. Una captura al cruzar un evento durante reproducción.
2. Una captura después de saltar, con reconstrucción y canal visible vacío.
3. Una captura después de reiniciar.
4. El archivo `dv-us-18-session-log.json` exportado desde la página.

## Limitaciones

- La aplicación mantiene una sola sesión en memoria y solo escucha en la interfaz local indicada.
- Los eventos están alineados manualmente y no provienen de Roboflow Sports ni SoccerNet.
- El clip no contiene un gol; sirve para probar controles y sincronización, no el cambio de marcador.
- El registro usa tiempos de pared para auditoría, pero no mide todavía latencia perceptual cuadro a pantalla.
- La herramienta aislada no sustituye la futura integración con el frontend oficial de Persona 4.
