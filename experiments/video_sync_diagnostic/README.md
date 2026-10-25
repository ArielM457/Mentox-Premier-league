# Validación del pipeline integrado

Esta aplicación demuestra DV-US-18 y DV-US-23 sin modificar `apps/frontend`. Sirve una página técnica, el MP4 permitido y la API oficial de integración. Consulta las exportaciones reales de Roboflow Sports, SoccerNet y DV-US-21.

## Ejecución

Desde la raíz del repositorio:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  uvicorn video_sync_diagnostic.app:app \
  --app-dir experiments \
  --host 127.0.0.1 \
  --port 8018
```

Abra <http://127.0.0.1:8018>.

El MP4 predeterminado debe existir en:

```text
experiments/authorized-video/input/2e57b9_0.mp4
```

## Recorrido manual

1. Confirme que aparecen 16.018 detecciones, 127 acciones y un candidato.
2. Salte alrededor de 19,7 segundos y revise el candidato con track 140.
3. Confirme que `player_id` está ausente y que hay cero `MatchEvent` visuales.
4. Pause, avance y retroceda para revisar ventanas de ±500 ms.
5. Reinicie y confirme tiempo, cursor y canal visible en cero.
6. Exporte el registro JSON y compruebe que no contiene credenciales ni datos personales.

## Límites

- Es un cliente técnico de la API oficial, no la interfaz de producto.
- Los eventos visibles siguen siendo sintéticos y están separados de los modelos.
- Las observaciones fueron calculadas previamente; la página no ejecuta inferencia durante la reproducción.
- El candidato es experimental y no se convierte en `MatchEvent`.
- Mantiene una sola sesión en memoria y está pensada para una persona revisora.
