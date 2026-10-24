# Evidencia técnica de DV-US-16

## Identificación

- **Historia:** DV-US-16 · Probar Blob Storage de extremo a extremo.
- **Estado:** verificada en integración.
- **Prioridad:** P0.
- **Última verificación:** 13 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.
- **Eleva:** DV-US-09.

## Objetivo comprobado

Un partido generado localmente y marcado como sintético se cargó en el contenedor privado `matches`. Una observación experimental sintética se cargó en `observations`. Ambos artefactos se descargaron mediante el adaptador real y conservaron exactamente sus bytes y hashes SHA-256.

Una segunda escritura de la misma observación produjo `ResourceExistsError`. La descarga posterior confirmó que Azure conservó intacto el contenido original. `authorized-videos` permaneció fuera de prueba porque todavía depende del permiso documentado en DV-US-17.

## Entrada y resultado real

| Elemento | Resultado |
|---|---|
| Tipo | `synthetic_match` |
| Procedencia | `synthetic` |
| Origen | `dv-us-09-smoke` |
| Contenedor | `matches` |
| Nombre | `<match-id-aleatorio>/<artifact-id-aleatorio>.json` |
| Tamaño recuperado | 5317 bytes |
| SHA-256 | `6e183db7786b5c094994ba768c1d9b39dd5b2eaaec986a1e6ddcd63c3fbe76cc` |
| Integridad | `content_matches=true` |

### Observación experimental

| Elemento | Resultado |
|---|---|
| Tipo | `observation` |
| Procedencia | `experimental` |
| Origen | `dv-us-16-smoke` |
| Contenedor | `observations` |
| Nombre | `<match-id-aleatorio>/<observation-id-aleatorio>.json` |
| Tamaño recuperado | 232 bytes |
| SHA-256 | `463b477e5e95c25ff3669f3ac6fa6970474d28005a49f5691a30fdcba497d615` |
| Integridad | `content_matches=true` |

### Colisión controlada

| Elemento | Resultado |
|---|---|
| Segunda escritura | Rechazada |
| Error | `ResourceExistsError` |
| Contenido original | Conservado sin cambios |

No se utilizaron datos reales de la Premier League ni vídeos.

## Archivos involucrados

| Archivo | Función |
|---|---|
| `apps/backend/scripts/blob_storage_smoke.py` | Partido, observación, integridad y colisión contra Azure real |
| `apps/backend/src/match_intelligence/adapters/storage/azure_blob.py` | OAuth, metadatos, contenido e integridad |
| `apps/backend/src/match_intelligence/application/artifacts.py` | Clasificación, procedencia, nombres y SHA-256 |
| `apps/backend/tests/test_azure_blob_storage.py` | Cobertura local de contenedores, colisión e integridad |

El script se amplió después de la primera ejecución para cubrir también una observación experimental y repetir exactamente su carga. Captura únicamente `ResourceExistsError`; cualquier fallo distinto continúa visible. Tras el rechazo vuelve a descargar el blob y comprueba que conserva los bytes originales.

## Documentación vigente consultada

Context7 consultó `/azure/azure-sdk-for-python` el 13 de octubre de 2026. Se confirmó el uso asíncrono de `upload_blob` con `overwrite=False` y la recuperación mediante `download_blob()` seguida de `readall()`.

## Cobertura de criterios de aceptación

| Criterio | Evidencia | Estado |
|---|---|---|
| Partido sintético en `matches` con trazabilidad | Nombre jerárquico, partido, origen y procedencia en la salida real | Cumplido |
| Observación experimental en `observations` | 232 bytes recuperados, procedencia `experimental` e integridad confirmada | Cumplido |
| No probar `authorized-videos` sin permiso | No se cargó ningún vídeo | Cumplido |
| Conservación exacta y SHA-256 | 5317 bytes y `content_matches=true` | Cumplido |
| Sobrescritura visible | Segunda carga produjo `ResourceExistsError`; descarga posterior preservó el original | Cumplido |
| No usar datos reales de Premier League | Generador sintético y procedencia explícita | Cumplido |

## Reproducción

```bash
export AZURE_BLOB_SERVICE_ENDPOINT="https://<storage-account>.blob.core.windows.net/"

UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/blob_storage_smoke.py

UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_azure_blob_storage.py -q
```

## Entorno y resultados

| Componente | Versión o resultado |
|---|---|
| Python | 3.12.13 |
| uv | 0.11.32 |
| Azure | StorageV2 `Standard_LRS` en `centralus` |
| Prueba real de `matches` | Aprobada: 5317 bytes e integridad confirmada |
| Prueba real de `observations` | Aprobada: 232 bytes e integridad confirmada |
| Colisión real | Rechazada y contenido original conservado |
| Pruebas específicas de Blob | 14 pruebas aprobadas en 0,22 s |
| Suite completa posterior | 135 pruebas aprobadas en 0,67 s |

## Limitaciones y siguientes pasos

- El blob sintético de esta ejecución permanece almacenado para auditoría y genera un costo mínimo.
- No usar `authorized-videos` hasta documentar el permiso en DV-US-17.
- El secreto temporal compartido no se registra y debe revocarse al terminar la integración.
- La prueba confirma una ejecución funcional, no rendimiento sostenido ni políticas de retención y eliminación.
