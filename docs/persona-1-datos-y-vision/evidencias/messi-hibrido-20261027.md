# Integración híbrida: Roboflow, TeamSpotting y MESSI

Fecha local: 27 de octubre de 2026. Responsable: Persona 1, con cambios
integrados en API y presentación de Persona 4. Requisitos relacionados:
RF-01, RF-02, RF-03, RF-11, RF-13, RF-37, RF-49, RF-51 y RNF-03.

Actualización posterior: la [prueba real en Azure](messi-azure-20261027/README.md)
ya verifica el MP4 completo con ambas GPUs, colas y worker. El presente
documento conserva el alcance de las pruebas locales iniciales.

Estado: **implementada y verificada localmente**. El flujo HTTP usa dobles
de los modelos para probar la integración sin GPU. La conversión también se
ejecutó sobre los archivos reales del primer MP4 limpio generado en Azure.
La interfaz se verificó en Chrome con ese MP4, dobles HTTP de inferencia y
colas en memoria. No se marca como verificada la calidad de inferencia remota
ni una ejecución nueva con ambas GPUs encendidas.

## Decisión y límites de procedencia

GameState queda desactivado por defecto mediante
`SOCCERNET_GAMESTATE_ENABLED=false`, incluso si hay un endpoint antiguo en
el entorno. Su código permanece como experimento optativo, pero no participa
en la demo actual.

Roboflow entrega objetos y cajas; TeamSpotting entrega propuestas temporales.
Los eventos normalizados y la identidad de los jugadores proceden de MESSI,
con `source=synthetic`, `situation=messi_simulator` y referencias al evento
original. Nunca se convierten en `video_model` al añadir evidencia temporal.
La referencia del simulador sirve también para evaluar modelos después; no
se presenta como una confirmación automática de sus aciertos.

## Cambios implementados

- Adaptador para `replay/3`, `events/6` y `tracking/2` del generador fijado.
- Manifiesto, tamaños y SHA-256 de MP4, eventos, seguimiento y metadatos.
  Un fallo de integridad no se reemplaza silenciosamente por datos de Ariel.
- Plantilla del mismo vídeo: equipo local/visitante y slots visibles 0–10,
  sin inventar dorsales OCR ni nombres reales. No se adaptan sustituciones
  fuera de la plantilla inicial en esta versión: se rechazan explícitamente.
- Eventos de pase, tiro/gol, entrada, recuperación, posesión y reanudación,
  únicamente cuando el registro aporta los campos necesarios. Tipos no
  soportados y posesiones sin equipo se contabilizan como ignorados.
- Una acción por resultado de pase o tiro, no una por `touch` y otra por
  resultado. El resultado se publica en `outcome_frame`, no en el timestamp
  de lanzamiento que usa el exportador. Así no se revela un receptor o un
  gol antes de ocurrir. Resultados desconocidos permanecen desconocidos.
- Posiciones centradas en metros convertidas al campo fijo. Se conserva
  `source=synthetic_simulator` en seguimiento y evidencia de sus métricas.
- Identificadores estables que incluyen la huella del vídeo para no
  confundir eventos de dos replays bajo el mismo identificador de sesión.
- Registro y duración real del vídeo en la sesión oficial. Los otros
  partidos conservan los escenarios existentes. Sin paquete verificable,
  el escenario de Ariel sigue disponible como cancha sintética, sin asignarle
  el MP4 ni presentar sus eventos como los del vídeo.
- Publicación al avanzar durante Play: ingreso → filtro → métricas o ruta
  importante. Pausa detiene nuevas entregas. Saltos y reinicios no vuelven
  a contabilizar los eventos ya enviados durante la vida del proceso.
- Generación de reproducción para ignorar avances tardíos de antes de un
  salto o pausa. Fallos de entrega se devuelven como HTTP 503 para reintentar.
- Recuperación por ventana temporal tras saltar, reiniciar o perder el
  WebSocket, sin repetir la inferencia temporal ni publicar en las colas
  por el mero hecho de consultar esa ventana.
- En Partido: jugadores, receptor, equipo, resultado, distancia y velocidad
  de salida simulada cuando existen. MESSI, Roboflow y TeamSpotting tienen
  estados y procedencias separados; ya no aparece GameState como dependencia.
- Coincidencias de TeamSpotting por clase y ventana de ±1000 ms respecto al
  lanzamiento, sin elegir arbitrariamente un actor. Varias coincidencias
  quedan como candidatos ambiguos, no añaden goles ni pases a las estadísticas.
  Tampoco se muestran candidatos futuros dentro del evento del simulador.
- Corrección de las traducciones inglesas de visión, que estaban en
  `editorial` en lugar de `match`. La UI consulta estado periódicamente
  aunque el vídeo siga pausado mientras prepara los modelos.
- Colección Postman actualizada con las cinco operaciones de visión que
  faltaban en su prueba de cobertura.
- Snapshot del MP4 verificado en memoria: rangos HTTP 206 y ETag sobre los
  mismos bytes enviados a TeamSpotting, sin descargar Blob en cada rango.
  `/integration/status` informa sobre este vídeo, no sobre el antiguo clip
  local de 30 segundos.
- Reintentos acotados de arranque en frío y comprobación de salud al reanudar;
  no se repite el análisis temporal si sus resultados siguen en caché.
- Entregas fallidas conservadas para reintento. Un fallo del canal visual no
  bloquea los tiros siguientes en la ruta importante. No se afirma entrega
  exactamente una vez entre reinicios o fallos parciales de transporte.
- El vídeo permanece montado al cambiar de pestaña. Iniciar el MP4 no ejecuta
  el guion de Ariel; preferencias guardadas de otro partido se filtran antes
  de consultar resúmenes, narrativas y asistente.

## Archivos principales

- `apps/backend/src/match_intelligence/adapters/sources/messi_replay.py`.
- `apps/backend/src/match_intelligence/application/simulated_video.py`.
- `adapters/http/{integration_router,match_router,match_schemas,registry}.py`.
- `application/{match_session,teamspotting_analysis}.py`.
- `domain/analytics/{tracking,models}.py`.
- `apps/frontend/src/components/match/LiveExperiencePanels.jsx`.
- `apps/frontend/src/screens/MatchCenter.jsx`, `api/client.js`, `i18n/strings.js`.
- `apps/frontend/src/lib/simulatedEvent.js` y su prueba.
- `apps/backend/scripts/validate_simulated_replay.py`.
- `apps/backend/scripts/validate_hybrid_browser.py` y
  `apps/backend/tests/browser_hybrid_server.py` (solo pruebas locales).
- `compose.integration.yml`, `apps/backend/.env.example` y guía operativa.

Las rutas abreviadas de backend son relativas a
`apps/backend/src/match_intelligence/`.

## Entrada real y resultado offline

Blob de referencia: `synthetic-videos/messi/messi-clean-2x180s-20261026/messi-001/match.mp4`.
SHA-256 del MP4:
`188498f09109fbae2f4cb95e6c60b541358d29777c12ea3e261b0c2693807fd7`.

Resultado en [el informe JSON](messi-hibrido-20261027-resultados.json):

- duración: 180000 ms;
- 22 jugadores, 181 cuadros de seguimiento;
- 170 eventos: 89 pases, 3 tiros, 5 entradas, 28 recuperaciones,
  39 cambios de posesión y 6 reanudaciones;
- 73 pases completados, 15 fallidos y uno sin resolver;
- dos tiros atajados y otro con resultado no mapeado: no se fabrican goles;
- normalización local de archivos ya descargados: 50,308 ms en
  esta máquina. No incluye Blob, TeamSpotting ni inferencia de Roboflow.
- reproducción completa por avances de un segundo: 170 observaciones,
  164 ingresos al filtro, 162 entregas de métricas y dos importantes;
  sin fallos de telemetría ni duplicación al reiniciar el vídeo. Las seis
  reanudaciones se muestran, pero no se fuerzan al contrato del filtro.

Este replay guarda posiciones aproximadamente cada segundo. El motor exige
muestras más densas para movimiento continuo: velocidades y distancia
recorrida derivadas de esta trayectoria pueden quedar no disponibles. Las
distancias y velocidades de salida explícitas de los eventos se muestran
como telemetría simulada, no como mediciones obtenidas del vídeo.

## Pruebas y comandos

Entorno: Python 3.12.13, Node v22.17.0, React 19, Vite 8.3.3.
No se incorporaron nuevas dependencias de producción. La comprobación del
navegador usa Playwright 1.58.0 en un entorno temporal de `uv`.

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 --offline pytest -q apps/backend/tests

node apps/frontend/src/lib/simulatedEvent.test.js
node apps/frontend/src/lib/matchPreferences.test.js
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 --offline \
  pytest -q deploy/azure-messi-generator/test_generate_batch.py
npm --prefix apps/frontend run build
npm --prefix apps/frontend run lint
git diff --check
```

La suite completa del backend pasó con 473 pruebas aprobadas y una omitida
(15,12 segundos en la repetición final). Los tres casos de texto en español
e inglés y los dos casos de preferencias pasaron. Build correcto; lint
sin errores, con tres advertencias preexistentes en `useCatalog`, `Editorial`
y `MomentDetail`. Dentro del sandbox se bloquean pruebas HTTP que usan hilos;
la suite completa se ejecutó con permiso fuera de él.
Las ocho pruebas del generador MESSI también pasaron (0,23 segundos).
La sintaxis Bash de los scripts compartidos GPU, worker, generador,
operador de Ariel y despliegues Roboflow/TeamSpotting pasó con `bash -n`.
Esta comprobación no despliega infraestructura.

Pruebas específicas:

- `test_messi_replay.py`: integridad, identidad, tiempo de llegada, no
  duplicación, aislamiento de partido, caché y resultados causales.
- `test_simulated_video_integration.py`: preparación sin GameState, llamada
  a los tres roles Roboflow, TeamSpotting, vídeo y metadatos correctos,
  publicación a las dos rutas, pausa, salto, reinicio, recuperación de
  observaciones y rechazo de hashes de vídeo distintos.
- `test_model_preparation.py`: sigue verificando concurrencia y errores
  del experimento GameState mediante opt-in explícito en su prueba.
- `test_hybrid_failure_modes.py`: reintentos de entrega, pausa durante una
  espera de red, cola importante independiente del canal visual, respuestas
  temporales inválidas y rangos de vídeo.
- `test_model_http.py`: arranque en frío, plazo de reintentos, errores no
  reintentables y rechazo de respuestas Roboflow parciales o malformadas.

Para repetir la conversión, descargue los cinco archivos del mismo directorio
y ejecute el script offline con sus rutas:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 --offline \
  python apps/backend/scripts/validate_simulated_replay.py \
  --manifest /ruta/manifest.json --video /ruta/match.mp4 \
  --events /ruta/events.jsonl --tracking /ruta/tracking.jsonl \
  --metadata /ruta/metadata.jsonl --check-playback \
  --output /tmp/messi-validacion.json
```

La [guía de ejecución](../guia-flujo-hibrido-messi.md) incluye variables,
arranque y verificaciones del flujo completo.

## Navegador comprobado

La repetición final terminó el 28 de octubre de 2026 a las 01:19:58 UTC
(27 de octubre en Bolivia). Pasaron doce comprobaciones, sin errores de
JavaScript: Play, pausa, cajas, eventos legibles, tres roles Roboflow,
TeamSpotting reutilizado, saltos, tiros a la ruta importante, reinicio,
español/inglés, móvil de 390 px, preferencias antiguas y escenario de Ariel
conservado. Las comprobaciones relacionadas comparten algunos pasos.

El navegador envió seis JPEG; cada uno pasó por los tres roles del doble
Roboflow. TeamSpotting recibió el MP4 una sola vez. Se entregaron dos eventos
importantes y no quedaron entregas pendientes. Las cajas de estas capturas
son respuestas controladas de prueba, no resultados reales de precisión.

[Resultados, capturas y comando reproducible](messi-browser-20261027/README.md).

## Alcance de la verificación y límites

- La prueba nueva no usa inferencia GPU, Event Hubs, Service Bus ni el worker
  remotos. Valida sus contratos con dobles HTTP y transportes en memoria;
  no demuestra permisos o disponibilidad actuales de las suscripciones.
- No mide precisión de los modelos contra la referencia. La correspondencia
  temporal no prueba asociación de jugador.
- La caché de preparación y deduplicación permanece en memoria; reiniciar
  el backend pierde ese estado. La deduplicación durable depende de Service
  Bus y de los consumidores desplegados. No se afirma exactly-once.
- El worker existente no se transforma aquí en agentes narrativos remotos
  nuevos. Se utiliza su contrato de enrutamiento actual.
- No hay inferencia de presión, dificultad del pase, velocidad de jugador
  o identidad nominal desde vídeo por añadir estos datos MESSI.

No se encendieron GPUs ni se modificaron recursos de infraestructura durante
esta implementación. Solo se descargaron dos artefactos faltantes del replay
existente para la validación local; no se generaron vídeos nuevos.

Referencias de APIs consultadas mediante Context7:
[Azure Blob SDK](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-blob)
y [efectos React](https://react.dev/learn/synchronizing-with-effects).
