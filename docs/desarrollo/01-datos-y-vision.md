# SDD-01 · Datos, reproducción y visión

## Especificación

**Objetivo:** disponer de entradas repetibles y trazables antes de interpretar el partido. Los eventos deportivos, las observaciones de modelos y los candidatos de fusión tienen contratos separados.

**Entradas:** metadatos, eventos sintéticos, señales de reproducción y, en experimentos configurados, vídeo permitido y salidas de Roboflow/SoccerNet. **Salidas:** eventos validados, marcas de duplicado/tardanza, ventanas sincronizadas y observaciones con procedencia.

Requisitos relacionados: RF-01 a RF-06, RF-13, RF-37, RF-49, RF-50 y los RNF de trazabilidad, repetibilidad e idempotencia. Sus enunciados permanecen en [requisitos](requisitos.md).

### Criterios de aceptación

1. El mismo escenario y semilla producen los mismos metadatos y eventos.
2. Una entrada inválida se rechaza y un evento duplicado no produce un segundo efecto.
3. Un evento tardío queda marcado sin retroceder la marca de agua del partido.
4. Pausa y salto actualizan el cursor; las salidas posteriores al tiempo actual no se muestran como ocurridas.
5. Una detección conserva tiempo, origen y confianza; la fusión mantiene su condición de candidato.
6. Un resultado de visión de otro medio o con hashes incompatibles no se acepta como parte del mismo lote.

## Diseño implementado

`domain/contracts.py` define eventos y metadatos; `domain/vision.py`, observaciones. `application/validation.py`, `deduplication.py` y `event_order.py` validan, deduplican y marcan tardanza. `replay.py`, `video_sync.py` y `observation_playback.py` coordinan los relojes.

`adapters/sources/` contiene los escenarios sintéticos y conversiones de seguimiento. `integrated_pipeline.py` lee resultados de visión y verifica compatibilidad. `live_vision_capture.py` envía fotogramas a un predictor remoto cuando hay endpoint y configuración; el frontend no recibe su clave.

Los experimentos de `experiments/` y servicios de `deploy/` tienen dependencias específicas y no forman parte de la instalación mínima de la API. SoccerNet GameState tiene un preflight que declara sus límites; no se documenta como servicio listo por el solo hecho de existir su adaptador.

## Tareas y estado

- [x] Definir contratos, generadores y validación de lotes.
- [x] Separar deduplicación y política `forward_and_flag`.
- [x] Implementar reproducción por tiempo de vídeo y canal de observaciones.
- [x] Incorporar lectura de resultados y captura remota configurable.
- [x] Separar los tres JSON requeridos por Docker en `apps/backend/data/vision/` y restaurar LF en las predicciones para respetar los hashes existentes del informe.
- [ ] Validar inferencia GPU completa por cada modelo y medio permitido en el entorno de entrega.
- [ ] Completar y probar la conversión automática de observaciones a todos los eventos deportivos requeridos.
- [ ] Demostrar identificación nominal de jugadores con una fuente verificable adicional al detector.

## Validación

Pruebas relacionadas: `test_synthetic_match.py`, `test_event_validation.py`, `test_event_deduplication.py`, `test_event_order.py`, `test_video_sync.py`, `test_vision_records.py`, `test_observation_fusion.py`, `test_observation_playback.py`, `test_live_vision_capture.py` y las pruebas integradas.

Los fallos de integración por resultados ausentes en las rutas predeterminadas ya existían antes del archivo documental. Los detalles y comandos están en [validación](validacion.md). Los permisos y variables de artefactos están en [datos y visión](../funcionamiento/datos-y-vision.md).
