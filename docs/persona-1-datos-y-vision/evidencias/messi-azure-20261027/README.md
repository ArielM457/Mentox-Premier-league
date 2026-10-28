# The Prime Moment: prueba real del flujo híbrido en Azure

Fecha local: 27 de octubre de 2026. Reproducción en Chrome del MP4 limpio
de 180 segundos, con Roboflow Suite y TeamSpotting remotos en Tesla T4,
Blob Storage privado, Event Hubs, Service Bus y Container Apps Job reales.
GameState permanece retirado. No se usaron dobles de inferencia en esta prueba.

## Resultado

- Vídeo verificado: SHA-256
  `188498f09109fbae2f4cb95e6c60b541358d29777c12ea3e261b0c2693807fd7`.
- [Reproducción completa](azure-browser-result.json): aprobada, de
  `2026-10-28T01:39:00Z` a `01:42:22Z` UTC, sin errores JavaScript ni HTTP de
  API. Una ejecución corta previa había comprobado las primeras capturas;
  los contadores del backend son acumulados desde su arranque.
- TeamSpotting: una inferencia del mismo MP4, 177 predicciones, T4;
  `processing_time_ms=19128.686` devuelto por el servicio. Ese tiempo no
  incluye necesariamente todo el arranque, transferencia y preparación.
- Roboflow: 101 fotogramas procesados acumulados, 1.525 observaciones
  espaciales, cero fallos. Las 98 respuestas aceptadas registradas durante
  la reproducción completa confirman `models=3`: player, ball y pitch.
  Inferencia conjunta: media 153,52 ms, mínimo 98,48 ms y máximo 170,04 ms;
  no es latencia completa entre captura y pantalla.
- Captura configurada a 1.000 ms, sin acumular solicitudes concurrentes.
  Hubo 117 solicitudes recibidas y 16 omisiones por límites temporales o
  pausa; no equivale a una garantía de procesar exactamente un cuadro cada
  segundo. El vídeo siguió a velocidad normal.
- MESSI: 170 eventos del simulador, con origen explícito. Los 164 tipos
  admitidos por el filtro se entregaron: 162 a métricas y dos importantes.
  Las seis reanudaciones se muestran sin forzar su tipo en el filtro.
- Event Hubs: 1.872 observaciones publicadas y aceptadas, sin rechazos ni
  fallos. Incluyen las 1.525 espaciales, 177 temporales y 170 del simulador.
- Service Bus y worker: [ejecución exitosa](worker-result.json), dos mensajes
  procesados, cero abandonos y cero mensajes muertos; cola final vacía.
- Play y pausa comprobados desde la interfaz. Reanudar reutilizó la inferencia
  de TeamSpotting, sin nueva ejecución del MP4.

## Corrección encontrada al probar con Vite

El proxy HTTP de desarrollo no reenviaba el Upgrade de WebSocket. Las
consultas por ventana funcionaban, pero el panel mostraba canal desconectado.
Se habilitó `ws: true` en `apps/frontend/vite.config.js`.

Después de esa corrección, una [prueba adicional en Chrome](websocket-result.json)
recibió 68 observaciones por el socket de la UI, con fuentes
`roboflow-player`, `roboflow-ball` y `roboflow-pitch`, sin errores JavaScript.
La prueba completa anterior valida reproducción/HTTP/colas; esta prueba
adicional valida explícitamente el WebSocket corregido.

- [UI pausada durante la prueba completa](partido-pausa-azure.png).
- [UI durante las jugadas de tiro](partido-tiros-azure.png).
- [Final de la reproducción](partido-final-azure.png).
- [Canal conectado después de corregir el proxy](partido-websocket-azure.png).

Las cajas son resultados reales del detector, no anotaciones de referencia.
No se evaluó precisión estadística: un modelo entrenado con imágenes de fútbol
real puede equivocarse sobre los jugadores estilizados del simulador.
Las identidades, pases completados y métricas MESSI siguen siendo datos del
simulador; no se convierten en hechos confirmados por IA.

El worker confirma y consume el despacho usando `DispatchRecordingHandler`.
Esta prueba no demuestra una nueva ejecución de agentes narrativos LLM
remotos. El backend local usa el proveedor narrativo provisional.

## Repetir

Con los servicios de inferencia listos y backend/frontend configurados según
la [guía](../../guia-flujo-hibrido-messi.md), desde la raíz:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 --with playwright==1.58.0 \
  python apps/backend/scripts/validate_live_azure_browser.py \
  --output /tmp/prime-azure-browser
```

Requiere Google Chrome en `/usr/bin/google-chrome`. Publica eventos reales
de la demo e incurre en uso de inferencia y mensajería. No enciende ni apaga
recursos y no recibe ni almacena claves. La prueba deja la captura pausada.
Las GPU deben apagarse al terminar la sesión manual del equipo.

La prueba adicional inicial corrigió una espera de la automatización:
tras el clic de reanudar hay que esperar a que termine la comprobación de
salud remota antes de exigir que el elemento de vídeo esté reproduciendo.

Documentación consultada mediante Context7: Azure CLI (`containerapp update`,
`secret list`), Playwright Python y `server.proxy` de Vite. La clave Roboflow
se leyó en memoria desde el secreto existente; no se cambió ni se registró.
