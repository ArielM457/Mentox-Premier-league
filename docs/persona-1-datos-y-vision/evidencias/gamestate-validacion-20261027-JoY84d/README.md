# Validación GPU de GameState · 27 de octubre de 2026

Alcance: servicio remoto GameState y su adaptador real de backend. Esta prueba
no valida Roboflow, TeamSpotting, Event Hubs, el worker ni la interfaz.

## Entrada

- MP4 sintético MESSI `messi-clean-2x180s-20261026/messi-001/match.mp4`.
- 180 segundos, 2700 fotogramas, 15 FPS, 1920 × 1080, 4 615 080 bytes.
- SHA-256: `188498f09109fbae2f4cb95e6c60b541358d29777c12ea3e261b0c2693807fd7`.
- Solo se envía el MP4. Tracking y metadatos del simulador no alimentan el modelo.
- No se configura una plantilla nominal verificada ni un mapeo de equipos.

## Resultado real

**Fallido. No se valida aún la salida analítica de GameState.**

- Análisis: `6dcc306a4fa34eb69a510940a8132fdd`.
- Inicio del pipeline: `2026-10-27T20:27:02.160201+00:00`.
- Fin: `2026-10-27T20:52:40.252213+00:00`.
- Duración hasta el fallo: 1538,092 segundos (25 minutos y 38 segundos).
- Duración total del cliente, incluido arranque: 1634,966 segundos.
- Error: `KeyError: 0`, en `sn_gamestate/calibration/nbjw_calib.py:179`.
- Código de salida del ejecutor: 1. No hay JSONL final ni métricas validadas.

El servicio usa pandas 2.3.3. La expresión
`metadatas["keypoints"][0]` busca la etiqueta `0`, no la primera posición del
lote. En un lote con índice `[1]` falla. La selección posicional
`metadatas["keypoints"].iloc[0]` evita ese error en una reproducción mínima
ejecutada dentro de la misma imagen, sin red ni GPU. No se aplicó un parche al
servicio ni se repitió todavía el pipeline completo con esa corrección.

La distinción entre etiqueta y posición se contrastó con la
[documentación de indexación de pandas](https://github.com/pandas-dev/pandas/blob/v2.2.3/doc/source/user_guide/indexing.rst),
consultada mediante Context7. La reproducción se ejecutó con pandas 2.3.3,
la versión instalada en la imagen.

Se validaron el arranque HTTP, autenticación, GPU y carga de pesos precargados.
No aparecen transferencias de pesos ni instalaciones en el log de esta prueba.
La GPU alcanzó 94–95 % de utilización en las instantáneas observadas: eliminar
descargas no elimina el coste del procesamiento. La duración medida es hasta
un fallo, **no** una medida de inferencia completa.

El adaptador descartó el identificador remoto al recibir el fallo. Por ello se
recuperaron manualmente el estado y el log finales antes de apagar la réplica.
El script de validación ahora conserva ese identificador para futuras pruebas;
esto no modifica el cliente de producción ni corrige el fallo de SoccerNet.

La repetición local de `test_gamestate_analysis.py` y
`test_soccernet_gamestate_adapter.py` aprobó sus 15 pruebas. Esas pruebas usan
entradas controladas: no sustituyen el análisis GPU, que falló. El script de
validación pasa `--help`, compilación de Python y `git diff --check`.

## Ejecución reproducible

Requiere el MP4 descargado, la clave correcta exportada en
`SOCCERNET_GAMESTATE_API_KEY` y una réplica GPU encendida. No incluya la clave
en archivos de evidencia.

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/validate_gamestate_remote.py \
  --endpoint https://ca-mentox-gamestate-dev.yellowdune-bc941df0.northcentralus.azurecontainerapps.io \
  --video /ruta/al/match.mp4 \
  --output /tmp/validacion-gamestate
```

El script utiliza el cliente de producción y sustituye únicamente la descarga
Blob por la lectura local del mismo MP4. El transporte de observaciones de esta
prueba es en memoria; no publica en las colas de la aplicación.

## Archivos

- `input-video.json`: inspección del MP4 con ffprobe.
- `health.json`: respuesta de disponibilidad, Tesla T4 y siete pesos precargados.
- `client-status.json` y `client.log`: evolución del adaptador.
- `analysis.log`: log del pipeline descargado del servicio.
- `server-status.json`: estado final remoto, con inicio, fin y fallo.
- `pandas-reproduction.json`: resultado de la reproducción mínima local.
- `gpu-diagnostic.json`: instantánea de actividad, no promedio ni perfil completo.
- `summary.json`: resultado final y duración del cliente, cuando termina.
- Si termina correctamente: observaciones originales, tracking convertido,
  métricas y respuesta de preparación.

Las referencias HTTP de MMOCR en el log identifican el origen de un checkpoint;
por sí solas no prueban una descarga. Se distingue entre carga de caché y una
transferencia real.

El operador configura mínimo cero al finalizar la ejecución, también si falla.
La retirada efectiva de la réplica debe comprobarse por separado.

Comprobación final: `2026-10-27T20:59:35Z`, revisión `0000006`, escala `0-1`,
lista de réplicas `[]`. GameState quedó sin réplica GPU activa. Véase
`shutdown.json`. No se apagaron ni modificaron servicios de otras suscripciones.
