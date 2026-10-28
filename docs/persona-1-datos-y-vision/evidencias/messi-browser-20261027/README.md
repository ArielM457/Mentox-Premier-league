# The Prime Moment: comprobación del navegador

Prueba local del flujo híbrido con el MP4 limpio original de 180 segundos.
Chrome reproduce el vídeo real y envía JPEG mediante la UI real. Los
proveedores HTTP de Roboflow y TeamSpotting son dobles controlados; las colas
están en memoria. No prueba precisión de modelos ni disponibilidad de Azure.

- [Resultado y doce comprobaciones](browser-result.json).
- [Partido pausado](partido-pausa.png).
- [Tiros legibles y ruta importante](partido-tiros.png).
- [Vista móvil](partido-mobile.png).
- [Registro HTTP del servidor local](browser-server.log).

Las cajas de las capturas proceden del doble de inferencia; no se presentan
como detecciones acertadas sobre el vídeo. No se incluyen claves reales.

## Repetir

Requiere Google Chrome en `/usr/bin/google-chrome`, frontend compilado y los
cinco artefactos descargados del mismo replay. En `/ruta/replay` deben llamarse
`match.mp4`, `reference-manifest.json`, `reference-events.jsonl`,
`reference-tracking.jsonl` y `reference-metadata.jsonl`.

Desde la raíz del repositorio:

```bash
npm --prefix apps/frontend run build
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 --with playwright==1.58.0 \
  python apps/backend/scripts/validate_hybrid_browser.py \
  --replay-dir /ruta/replay --output /tmp/prime-browser-validation
```

El script abre un servidor de prueba en `127.0.0.1:8127`, captura resultados
y lo detiene al terminar, incluso si una comprobación falla. No modifique
endpoints de producción para apuntarlos a este servidor de prueba.
