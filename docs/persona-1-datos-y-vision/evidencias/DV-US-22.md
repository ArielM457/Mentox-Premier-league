# Evidencia técnica de DV-US-22

## Identificación

- **Historia:** DV-US-22 · Ejecutar el ensayo de aceptación integrado.
- **Estado:** verificada en integración.
- **Prioridad:** P0.
- **Última verificación:** 14 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.
- **Requisitos relacionados:** DV-RNF-01 a DV-RNF-07.

## Resultado actual

Se creó un ejecutor de aceptación que recorre el transporte local, prueba un fallo externo controlado y comprueba por integridad las salidas reales de sincronización, Roboflow Sports, SoccerNet y la calibración de fusión. El frontend oficial no fue modificado.

El 23 de octubre de 2026 se añadió un lanzador único para repetir el recorrido
de backend. La revalidación sin repetir inferencias recalculó la fusión,
comprobó las huellas de entrada, aprobó 162 pruebas, inició FastAPI, consultó
`/api/v1/integration/status` y `/api/v1/integration/timeline`, y creó un paquete
de evidencia. Azure se omitió expresamente en esta repetición; conserva la
verificación real documentada anteriormente.

La suite completa pasó con `154 passed in 0.76s`. El total anterior era 151; las tres pruebas nuevas cubren el recorrido local, la continuidad después del fallo y la integridad de los artefactos reales.

La repetición desde la sesión de Codex alcanzó el namespace real, pero Azure rechazó la publicación porque esa sesión usaba una identidad diferente del principal de servicio autorizado. El error fue `Unauthorized access. 'Send' claim(s) are required`. No se cambió RBAC, no se solicitó ni almacenó el secreto y el modo local continuó disponible.

Después, el operador ejecutó las dos pruebas desde su terminal con el principal autorizado. Event Hubs publicó dos veces el mismo evento, aceptó una copia y registró la segunda como duplicada. Blob Storage escribió y recuperó un partido y una observación, rechazó la colisión y preservó el contenido original. Con esta repetición, la historia queda verificada en integración.

## Orden ejecutado

1. Suite local y comprobaciones estáticas.
2. Transporte en memoria con un partido sintético completo y un duplicado.
3. Fallo de red controlado del adaptador Azure y repetición inmediata en memoria.
4. Verificación de sesión de sincronización exportada.
5. Verificación de exportación real de Roboflow Sports.
6. Verificación de exportación real de SoccerNet.
7. Verificación de calibración DV-US-21.
8. Intento real de Event Hubs con la identidad de la sesión.
9. Inventario de recursos y consulta de costos.
10. Repetición de Event Hubs y Blob Storage desde la terminal con el principal autorizado.

No se repitieron las inferencias porque sus archivos conservan el SHA-256 esperado y tardaron aproximadamente 11,5 y 1,5 minutos. Esto evita gastar CPU sin aportar evidencia nueva.

## Resultado local integrado

| Comprobación | Resultado |
|---|---:|
| Eventos publicados en memoria | 11 |
| Eventos aceptados | 10 |
| Duplicados | 1 |
| Rechazados | 0 |
| Fallo controlado observado | `ConnectionError` |
| Evento alterado por el fallo | No |
| Modo local después del fallo | Aprobado |
| Suite completa | 154 aprobadas |

El informe JSON generado no contiene secretos y se mantiene ignorado por Git porque incorpora una fecha de ejecución variable.

## Medios y modelos reales

Las tres salidas comparten el SHA-256 de medio `7788719b32b944e42d8f1024fb4802f681bc2053d6301218a5bff6705b549f96`.

| Etapa | Resultado | Duración medida |
|---|---:|---:|
| Sincronización DV-US-18 | 36 registros sin datos sensibles | sesión manual |
| Roboflow Sports | 16.018 detecciones, 750 cuadros | 688.261,66 ms |
| SoccerNet | 127 acciones, 375 cuadros de modelo | 90.792,69 ms |
| Fusión DV-US-21 | 2 hipótesis, 1 candidato final | incluida en calibración |
| `MatchEvent` visual publicado | 0 | no aplica |

El candidato visual continúa siendo experimental. Event Hubs transporta eventos sintéticos válidos; no transforma una hipótesis visual en un hecho deportivo.

## Azure real

### Recursos observados

| Recurso | SKU | Región | Decisión actual |
|---|---|---|---|
| Namespace de Event Hubs | Standard | Central US | Conservar temporalmente para completar la prueba |
| Cuenta de Blob Storage | Standard_LRS | Central US | Conservar temporalmente para completar la prueba |

La consulta de consumo encontró registros para ambos recursos, pero Azure CLI devolvió `pretaxCost=None` y sin moneda. Por tanto, esta ejecución no aporta un importe verificable. El costo queda **pendiente** de revisar en Cost Management después de la actualización del ciclo de facturación.

### Fallo real observado

- Servicio alcanzado: sí.
- Operación: envío a `match-events`.
- Resultado: rechazado por falta del permiso de datos `Send` para la identidad usada por Codex.
- Evento original: preservado.
- Modo local: aprobado después del fallo.
- Acción de seguridad: no ampliar RBAC automáticamente y no compartir secretos con Codex.

Este fallo demuestra que una identidad sin el rol de datos no puede publicar. La ejecución posterior con el principal autorizado demostró que no era una caída del servicio ni una regresión del adaptador.

### Event Hubs con el principal autorizado

| Métrica | Resultado |
|---|---:|
| Publicaciones | 2 |
| Fallos de publicación | 0 |
| Eventos aceptados | 1 |
| Duplicados | 1 |
| Rechazados | 0 |
| Fallos del consumidor | 0 |
| Primera publicación | 3.659,654 ms |
| Segunda publicación | 178,673 ms |
| Latencia de transporte observada | 3.703,740 ms |

La primera operación incluye establecimiento de conexión y autenticación. La segunda publicación fue considerablemente menor. Esta muestra valida el recorrido, pero no basta para definir un objetivo de rendimiento de producción.

### Blob Storage con el principal autorizado

| Artefacto | Contenedor | Bytes | SHA-256 | Recuperación |
|---|---|---:|---|---|
| Partido sintético | `matches` | 5.317 | `8bb02899f54f97b1cb2db73fc4ad80c1eafa56fee0d5a950f8116742227f8214` | Coincide |
| Observación experimental | `observations` | 232 | `2053e531c53f21fa90898b953ce4955db82c1f4d30ed7ba83a4506b3dd7f4b4c` | Coincide |

El intento de guardar nuevamente la misma observación produjo `ResourceExistsError`. La comprobación posterior confirmó que el contenido original permaneció intacto.

## Archivos

| Archivo | Cambio |
|---|---|
| `apps/backend/scripts/run_integrated_acceptance.py` | Ejecutor local y consolidador de artefactos |
| `apps/backend/tests/test_integrated_acceptance.py` | Tres pruebas de aceptación |
| `.gitignore` | Exclusión del informe generado |
| `DV-US-22.md` | Evidencia, clasificación y comandos |
| `experiments/run-backend-integration.sh` | Orquestación completa, API real, Azure opcional y evidencia |
| `guia-integracion-backend.md` | Instrucciones para otro operador sin frontend |

## Comandos reproducibles

### Fase local

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 pytest -q

UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/run_integrated_acceptance.py \
  --output docs/persona-1-datos-y-vision/evidencias/dv-us-22-acceptance-report.json
```

### Fase Azure con el principal autorizado

Las variables `AZURE_TENANT_ID`, `AZURE_CLIENT_ID` y `AZURE_CLIENT_SECRET` deben existir únicamente en la terminal del operador. No se escriben en archivos ni se pegan en evidencia.

```bash
export EVENT_HUB_FULLY_QUALIFIED_NAMESPACE="eh-damon-dev-hxwjzbiyupwqc.servicebus.windows.net"
export EVENT_HUB_NAME="match-events"
export EVENT_HUB_CONSUMER_GROUP="diagnostics"
export AZURE_BLOB_SERVICE_ENDPOINT="https://stdamonhxwjzbiyupwqc.blob.core.windows.net/"

UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/event_hubs_smoke.py

UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/blob_storage_smoke.py
```

## Versiones y comprobaciones

- Python: 3.12 mediante `uv`.
- Azure CLI: 2.88.0.
- Bicep: 0.48.1.
- Docker Server: 27.0.3.
- Dependencias: bloqueo de 148 paquetes resuelto correctamente.
- `pytest`: 154 aprobadas.
- `compileall`: aprobado.
- `uv lock --check`: aprobado.
- `git diff --check`: aprobado.

## Matriz de aceptación

| Criterio | Resultado | Estado |
|---|---|---|
| Suite local aprobada o nuevo total justificado | 154; tres pruebas nuevas | Cumplido |
| Azure, vídeo y modelos en orden documentado | Event Hubs, Blob, vídeo, Roboflow, SoccerNet y fusión comprobados | Cumplido |
| Evidencia anonimizada por historia | Evidencias DV-US-01 a DV-US-22 | Cumplido, sujeta a revisión final |
| Fallo controlado sin detener modo local | Doble de red y rechazo RBAC real | Cumplido |
| Costo, duración, recursos y decisión | Duraciones y recursos registrados; costo no disponible en CLI; conservar temporalmente | Cumplido con limitación documentada |
| Clasificación final de estados | Incluida abajo | Cumplido provisionalmente |

## Clasificación provisional

### Verificada localmente

- DV-US-01 a DV-US-05.
- DV-US-10 a DV-US-13 en su alcance local.
- DV-US-17 y DV-US-18, sin capturas de interfaz.

### Verificada en integración

- DV-US-06 a DV-US-09 mediante DV-US-14 a DV-US-16.
- DV-US-19 y DV-US-20 como experimentos ejecutados sobre vídeo permitido.
- DV-US-21 como calibración experimental, no como productor de hechos.

### Rechazada para el flujo principal

- Publicación automática del candidato visual como `MatchEvent`.
- Identidad nominal obtenida solo desde `track_id`.
- Uso de resultados de modelos como verdad sin anotación manual completa.

### Pendiente

- Obtener un costo monetario confirmado en Azure Cost Management.
- Decidir con el equipo cuándo eliminar los recursos.
- Completar anotaciones manuales si se desea medir F1 real.

## Decisión

DV-US-22 queda **verificada en integración**. El ensayo cubrió el flujo local, Event Hubs, Blob Storage, vídeo, modelos, fusión experimental y un fallo real de permisos sin detener el modo local. Los recursos se conservan temporalmente; su costo confirmado y fecha de eliminación continúan como decisiones operativas del equipo. No se necesitó modificar ni ejecutar el frontend oficial para cerrar esta historia.
