# Estado actual de Persona 1 · Datos y visión

## Corte del informe

- **Fecha:** 13 de octubre de 2026.
- **Rama:** `main`.
- **Commit publicado:** `3ce1a86` · `Complete Persona 1 integration foundations`.
- **Estado de Git al iniciar este informe:** rama sincronizada con `origin/main` y sin cambios previos pendientes.
- **Python:** 3.12.13.
- **uv:** 0.11.32.
- **pytest:** 9.1.1.
- **Última suite registrada:** 141 pruebas aprobadas.

## Resumen ejecutivo

Persona 1 tiene implementado el flujo local de datos sintéticos, validación, reproducción, deduplicación, observación de eventos tardíos, transporte intercambiable, adaptadores Azure, almacenamiento de artefactos, sincronización con vídeo, evaluación experimental de visión, protección de identidad y fusión trazable.

DV-US-01 a DV-US-13 tienen código y evidencia local. Azure ya fue desplegado y autorizado: DV-US-14, DV-US-15 y DV-US-16 están verificadas en integración. Event Hubs comprobó transporte y duplicados; Blob Storage comprobó `matches`, `observations`, integridad y rechazo de sobrescritura.

Ya existe un vídeo sintético permitido y una interfaz mínima aislada conectada al coordinador Python. Sus pruebas automáticas aprobaron; falta el recorrido visual con capturas y registro exportado. Después corresponden las ejecuciones reales de Roboflow Sports y SoccerNet.

DV-US-17 está verificada localmente. Google Research Football produjo un MP4 sintético de 30 segundos, 800 × 450 y 10 FPS; su SHA-256 coincidió con el manifiesto y una tabla manual registra el balón en tres momentos. El archivo permanece local y fuera de Git.

## Estado de las historias implementadas

| Historia | Resultado disponible | Estado real |
|---|---|---|
| DV-US-01 | Partido sintético determinista | Verificada localmente |
| DV-US-02 | Reproducción, pausa, reinicio y velocidad | Verificada localmente |
| DV-US-03 | Validación por lotes y rechazo estructurado | Verificada localmente |
| DV-US-04 | Deduplicación por partido y evento | Verificada en memoria y contra Event Hubs real mediante DV-US-15 |
| DV-US-05 | Detección y registro de eventos tardíos | Verificada localmente; reconstrucción pendiente con Persona 2 |
| DV-US-06 | Bicep parametrizado para Event Hubs y Storage | Desplegado y verificado en Azure mediante DV-US-14 |
| DV-US-07 | Productor y consumidor asíncronos de Event Hubs | Verificados en Azure mediante DV-US-15 |
| DV-US-08 | Selección entre memoria y Event Hubs | Ambos transportes comprobados mediante DV-US-15 |
| DV-US-09 | Almacenamiento trazable en Blob Storage | `matches`, `observations`, integridad y colisión verificados mediante DV-US-16; vídeo pendiente de DV-US-17 |
| DV-US-10 | Sincronización por posición de vídeo | Verificada localmente; vídeo e interfaz pendientes |
| DV-US-11 | Evaluador de Roboflow Sports y SoccerNet | Evaluador verificado; modelos y vídeo reales pendientes |
| DV-US-12 | Separación entre `track_id` e identidad nominal | Regla verificada; asociación real pendiente |
| DV-US-13 | Fusión temporal y espacial trazable | Política verificada; observaciones reales pendientes |
| DV-US-17 | Paquete de vídeo permitido | MP4 sintético de 30 segundos y anotación manual verificados localmente |
| DV-US-18 | Interfaz mínima de sincronización | Aplicación aislada, API y controles verificados con dos registros reales; capturas aplazadas |
| DV-US-19 | Roboflow Sports sobre la muestra | Experimento verificado localmente; modelo `rejected` para integración por calidad y tiempo |
| DV-US-20 | SoccerNet sobre la muestra | Entorno Docker, checkpoint, preprocesamiento y exportador preparados; inferencia pendiente |

Los informes completos están en [evidencias](evidencias/README.md).

## Capacidades disponibles

### Datos sintéticos

- Partido de aceptación reproducible mediante semilla.
- Equipos, jugadores, direcciones de ataque y dimensiones del campo.
- Pases, tiros, entradas, presión, recuperaciones y cambios de posesión.
- Escenarios de control, transición y momento decisivo.
- Datos propios y sintéticos, sin redistribuir partidos reales de la Premier League.

### Ingesta y calidad

- Validación de `MatchEvent 1.0`.
- Rechazos con campo y motivo.
- Procesamiento posterior a un mensaje inválido.
- Deduplicación por `match_id` y `event_id`.
- Registro de duplicados y eventos tardíos.

### Reproducción y sincronización

- Reproducción progresiva local.
- Pausa, reanudación, reinicio y aceleración.
- Coordinación mediante `video_time_ms`.
- Salto hacia adelante o atrás con reconstrucción separada de mensajes visibles.
- Distinción explícita entre alineación temporal y detección automática.

### Azure desplegado y probado

- Infraestructura Bicep parametrizada.
- Namespace y event hub.
- Grupos de consumidores `backend` y `diagnostics`.
- Cuenta StorageV2 y contenedores privados:
  - `matches`;
  - `authorized-videos`;
  - `observations`.
- Autenticación prevista mediante `DefaultAzureCredential` y RBAC.
- Claves compartidas deshabilitadas en la infraestructura.
- Scripts de prueba para Event Hubs y Blob Storage.
- Despliegue incremental `Succeeded` en `centralus`.
- RBAC de datos limitado al namespace y a la cuenta Storage.
- Event Hubs real: dos publicaciones, un aceptado, un duplicado y cero fallos.
- Blob real: partido de 5317 bytes y observación de 232 bytes recuperados con integridad confirmada.
- Una segunda escritura fue rechazada y el contenido original permaneció intacto.

### Artefactos

- Clasificación de partidos sintéticos, vídeos autorizados y observaciones.
- Nombre trazable por partido y artefacto.
- Metadatos de procedencia.
- SHA-256 y comprobación de integridad al recuperar.
- Escritura sin sobrescritura accidental.

### Visión experimental

- Contrato para registrar medio, permiso, hash, modelo, versión, revisión, clases y configuración.
- Evaluación espacial mediante clase, tiempo e IoU.
- Evaluación temporal mediante clase y tolerancia.
- Precisión, recobrado, F1, falsos positivos y omisiones.
- Tiempo de procesamiento separado de la calidad.
- Los fixtures simulados no pueden habilitar un modelo para la demo.

### Identidad y fusión

- Un seguimiento visual conserva `track_id` y omite `player_id` sin evidencia.
- La confianza del detector no confirma identidad nominal.
- La asociación confirmada exige referencia, responsable y jugador de la plantilla.
- La fusión compara partido, seguimiento, equipo, tiempo y posición.
- Una contradicción o evidencia insuficiente no produce `MatchEvent`.
- Las observaciones originales permanecen asociadas al resultado.

## Componentes principales

| Área | Archivos principales |
|---|---|
| Contratos deportivos | `apps/backend/src/match_intelligence/domain/contracts.py` |
| Generador sintético | `apps/backend/src/match_intelligence/adapters/sources/synthetic.py` |
| Reproducción | `apps/backend/src/match_intelligence/application/replay.py` |
| Validación y orden | `application/validation.py`, `deduplication.py`, `event_order.py` |
| Event Hubs | `adapters/messaging/azure_event_hubs.py` |
| Selección de transporte | `adapters/messaging/configuration.py` |
| Blob Storage | `adapters/storage/azure_blob.py` |
| Sincronización | `application/video_sync.py` |
| Evaluación de visión | `application/vision_evaluation.py` |
| Identidad visual | `application/visual_identity.py` |
| Fusión | `application/observation_fusion.py` |
| Infraestructura | `infra/azure/` |

## Comandos disponibles

### Suite local

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 pytest -q
```

### Event Hubs real

Requiere DV-US-14 terminado y variables de entorno configuradas:

```bash
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/event_hubs_smoke.py
```

### Blob Storage real

Requiere DV-US-14 terminado y `AZURE_BLOB_SERVICE_ENDPOINT`:

```bash
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/blob_storage_smoke.py
```

### Evaluación de predicciones

El ejemplo es simulado y debe devolver `pending_real_run`:

```bash
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/evaluate_vision_predictions.py \
  docs/persona-1-datos-y-vision/experimentos-vision/input.example.json
```

## Lo que todavía no está demostrado

- Política final de reconstrucción de eventos tardíos con Persona 2.
- Vídeo propio, generado o autorizado con permiso documentado.
- Página de diagnóstico conectada al coordinador Python.
- Calidad y rendimiento reales de Roboflow Sports.
- Calidad y rendimiento reales de SoccerNet.
- Asociación nominal comprobada sobre un vídeo.
- Tolerancias de fusión calibradas con observaciones reales.

## Backlog de integración real

| Orden | Historia | Objetivo |
|---:|---|---|
| 1 | DV-US-20 | Ejecutar SoccerNet |
| 2 | DV-US-21 | Calibrar identidad y fusión |
| 3 | DV-US-22 | Ejecutar el ensayo integrado |

El paso a paso completo está en [plan de pruebas con servicios reales](plan-pruebas-servicios-reales.md).

## Próximo paso: DV-US-20

DV-US-19 procesó el vídeo sintético completo con Roboflow Sports. El modelo produjo seis detecciones, ninguna trayectoria y no acertó ninguno de los tres balones de referencia. El evaluador registró precisión, recobrado y F1 de 0,00, además de un factor de tiempo real de 13,81 en CPU. El resultado es `rejected` para integración y el flujo sintético continúa siendo la vía operativa.

El siguiente paso es ejecutar SoccerNet sobre la misma muestra para medir detección temporal de acciones. El peso y las salidas de Roboflow Sports permanecen fuera de Git. La licencia del peso no está declarada de forma inequívoca, por lo que su uso continúa siendo experimental y no autoriza redistribución.

## Criterio para declarar terminado el módulo

Persona 1 no se considera terminada solo por aprobar pruebas locales. Debe distinguir:

- lo verificado localmente;
- lo verificado contra Azure;
- lo probado con vídeo permitido;
- los modelos aceptados o rechazados con métricas reales;
- las decisiones que siguen pendientes de otras personas.

El modo sintético debe continuar funcionando aunque Azure o los modelos externos fallen.
