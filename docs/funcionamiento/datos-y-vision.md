# Datos, visión y procedencia

## Fuentes sintéticas

El backend incluye escenarios de aceptación, analítica de dos tiempos y directo. Sus generadores están en `adapters/sources/` y usan semillas para repetir entradas. Los nombres, marcadores y eventos de la demo se consideran sintéticos.

Los escudos y fotos del frontend son recursos visuales asignados mediante `branding.js`; no convierten a un jugador sintético en una persona identificada por un modelo.

## Observaciones y experimentos

Roboflow Sports aporta detección/seguimiento espacial; SoccerNet TeamSpotting, observaciones temporales de acciones. La fusión usa tiempos y señales compatibles para proponer candidatos. Se conservan procedencia, confianza, identificadores y límites.

Una caja, un color de equipo o un `track_id` no identifica nominalmente al jugador. Una acción detectada no se publica automáticamente como `MatchEvent` confirmado. Los experimentos y servicios de `experiments/` y `deploy/` tienen requisitos propios de pesos, datos, GPU y licencia.

SoccerNet GameState dispone de adaptador y comprobaciones, pero `infra/azure/preflight-soccernet-gamestate.sh` mantiene un bloqueo explícito mientras no se cumplan sus condiciones de inferencia. No se elimina ese control al reorganizar documentos.

## Permisos del material

Usar vídeo sintético, propio o con autorización verificable. Cada ejecución debe conservar origen, hash del medio y referencia al permiso o licencia concreta. Este documento **no otorga permiso sobre un vídeo** ni certifica derechos del material usado en pruebas pasadas.

Los lanzadores aceptan `MENTOX_PERMISSION_REFERENCE`. Cuando se utilice material nuevo, establecer una referencia específica y comprobable. La referencia documental predeterminada explica la política, pero no reemplaza la evidencia del permiso. El antiguo registro DV-US-17 permanece en el archivo local y en Git; no se aplica automáticamente a otros vídeos.

## Resultados precomputados versionados

Para construir la imagen backend se conservan estos archivos en `apps/backend/data/vision/`:

| Archivo | Contenido |
|---|---|
| `roboflow-sports-predictions.json` | Predicciones espaciales del lote histórico |
| `soccernet-predictions.json` | Predicciones temporales del mismo lote |
| `dv-us-21-report-recalculado.json` | Informe de fusión recalculado para esas entradas |

Se conservaron desde la documentación archivada. En las dos predicciones se restauraron finales de línea LF: las copias locales anteriores tenían CRLF y no coincidían con los hashes registrados por la fusión. El contenido JSON no cambia; ahora los hashes coinciden con el informe. `.gitattributes` evita nuevas conversiones en ese directorio. Los originales archivados permanecen intactos. Son resultados ya calculados, no pruebas de una nueva inferencia en esta máquina.

## Rutas y configuración local

`PipelinePaths.from_repository` conserva sus rutas predeterminadas bajo `experiments/*/output-real` y `experiments/fusion-calibration/output`. Esas rutas pueden no existir en un clon. Para usar el lote incluido sin mover archivos, definir antes de iniciar Uvicorn, desde la raíz:

```powershell
$env:MENTOX_ROBOFLOW_ARTIFACT = (Resolve-Path 'apps/backend/data/vision/roboflow-sports-predictions.json').Path
$env:MENTOX_SOCCERNET_ARTIFACT = (Resolve-Path 'apps/backend/data/vision/soccernet-predictions.json').Path
$env:MENTOX_FUSION_ARTIFACT = (Resolve-Path 'apps/backend/data/vision/dv-us-21-report-recalculado.json').Path
```

También pueden guardarse rutas absolutas en `apps/backend/.env`. El vídeo original no se incluye aquí; las operaciones que necesiten reproducirlo requieren `MENTOX_INTEGRATION_VIDEO` o una fuente de Blob configurada y autorizada.

El Dockerfile backend establece las tres rutas de artefactos dentro de su imagen. Esta reorganización cambia su ubicación de empaquetado, sin cambiar la selección predeterminada del pipeline local.

## Captura y transporte

`ROBOFLOW_SUITE_ENDPOINT`, su clave de servidor y los límites de captura configuran inferencia remota de fotogramas. `VISION_OBSERVATION_TRANSPORT=memory` mantiene el flujo local; `azure_event_hubs` requiere namespace, hub y permisos.

Los controles de reproducción publican el tramo cruzado por el reloj, no todo el historial como si fuera nuevo. Las observaciones se sincronizan en la interfaz y se deduplican por sus identificadores.

## Validación necesaria

Comprobar hashes del medio y entradas de fusión, continuidad temporal, identidad opcional, confianza, retraso y límites de memoria. Una evaluación local con resultados guardados se registra aparte de una inferencia real por GPU. Los fallos previos y las comprobaciones de esta revisión están en [validación](../desarrollo/validacion.md).
