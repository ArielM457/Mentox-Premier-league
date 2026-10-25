# Evidencia técnica de DV-US-15

## Identificación

- **Historia:** DV-US-15 · Probar Event Hubs de extremo a extremo.
- **Estado:** verificada en integración.
- **Prioridad:** P0.
- **Última verificación:** 13 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.
- **Eleva:** DV-US-04, DV-US-07 y DV-US-08.

## Objetivo comprobado

El backend publicó dos veces el mismo `MatchEvent 1.0` sintético en el Event Hub desplegado y lo consumió mediante el grupo `diagnostics`. La primera entrega fue aceptada y la segunda quedó registrada como duplicado, sin rechazos ni fallos de publicación o consumo. Después se comprobó que el transporte en memoria continuaba funcionando.

## Alcance y decisiones

- Autenticación mediante `DefaultAzureCredential` y un principal de servicio temporal con RBAC.
- Sin cadenas de conexión ni claves de Event Hubs.
- Namespace y principal omitidos cuando constituyen identificadores operativos; ningún secreto se conserva.
- Partición elegida mediante `match_id`.
- Sobre `MatchEventEnvelope` validado antes de recuperar el evento.
- Deduplicación por `match_id` y `event_id`.
- Medición de duración de publicación y latencia desde producción hasta recepción.

## Entrada y resultado real

| Elemento | Resultado |
|---|---|
| Fuente | Partido generado por `generate_acceptance_match` |
| Evento | `evt-001`; identificador de partido aleatorio omitido del informe |
| Publicaciones | 2 |
| Aceptados | 1 |
| Duplicados | 1 |
| Rechazados | 0 |
| Fallos de publicación | 0 |
| Fallos de consumo | 0 |
| Duraciones de publicación | 4251,559 ms y 203,937 ms |
| Latencia de transporte aceptada | 4267,49 ms |

La primera operación incluye adquisición de token, inicialización de conexión y publicación; no debe interpretarse como una meta estable de latencia. Se necesita una muestra mayor antes de establecer un objetivo operativo.

## Archivos involucrados

| Archivo | Función |
|---|---|
| `apps/backend/scripts/event_hubs_smoke.py` | Prueba real de publicación, consumo y duplicado |
| `apps/backend/src/match_intelligence/adapters/messaging/azure_event_hubs.py` | Productor, consumidor, tiempos, errores y deduplicación |
| `apps/backend/src/match_intelligence/application/transport.py` | Contrato del sobre sin cambiar `MatchEvent 1.0` |
| `apps/backend/tests/test_transport_configuration.py` | Regresión del transporte en memoria |

## Cobertura de criterios de aceptación

| Criterio | Evidencia | Estado |
|---|---|---|
| Usar `DefaultAzureCredential` sin cadenas de conexión | Fábricas reales y variables de identidad de Entra | Cumplido |
| Recuperar el evento sin cambiar `MatchEvent 1.0` | Un evento aceptado; contrato comprobado también por pruebas automatizadas | Cumplido |
| Dos publicaciones producen un aceptado y un duplicado | `published=2`, `accepted=1`, `duplicates=1` | Cumplido |
| Conservar tiempos y calcular latencia | Recibos internos conservan producción, inicio y fin; salida registró duración y latencia | Cumplido |
| Hacer observable un fallo sin alterar el evento | Pruebas automatizadas de productor y consumidor; ejecución real terminó sin fallos | Cumplido |
| Mantener el transporte en memoria | `test_transport_configuration.py` ejecutado después de la prueba real | Cumplido |

## Reproducción

Las credenciales se exportan localmente y no se documentan:

```bash
export EVENT_HUB_FULLY_QUALIFIED_NAMESPACE="<namespace>.servicebus.windows.net"
export EVENT_HUB_NAME="match-events"
export EVENT_HUB_CONSUMER_GROUP="diagnostics"

UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/event_hubs_smoke.py

EVENT_TRANSPORT=memory UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_transport_configuration.py -q
```

## Entorno y resultados

| Componente | Versión o resultado |
|---|---|
| Python | 3.12.13 |
| uv | 0.11.32 |
| Azure | Event Hubs Standard en `centralus` |
| Prueba real | Aprobada |
| Regresión local combinada | 20 pruebas aprobadas en 0,32 s, incluidas configuración y Blob local |
| Suite completa posterior | 135 pruebas aprobadas en 0,67 s |

## Limitaciones y dependencias

- Una sola ejecución no caracteriza percentiles de latencia ni comportamiento sostenido.
- El consumidor de diagnóstico comparte recursos reales; ejecuciones paralelas deben usar grupos coordinados para no repartirse eventos inesperadamente.
- El secreto temporal compartido debe revocarse al terminar el trabajo. Un despliegue de backend deberá usar identidad administrada.
- El namespace produce costo mientras exista.

