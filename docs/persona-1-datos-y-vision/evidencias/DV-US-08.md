# Evidencia técnica de DV-US-08

## Identificación

- **Historia:** DV-US-08 · Cambiar entre transporte local y Azure.
- **Estado:** memoria y Azure comprobados mediante DV-US-15.
- **Prioridad:** P0.
- **Última verificación:** 13 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.
- **Requisitos relacionados:** DV-RF-11, DV-RF-12, DV-RF-13 y DV-RNF-02.

## Objetivo comprobado

> **Actualización de integración:** Event Hubs real aprobó el 13 de octubre de 2026 y, después, la configuración en memoria volvió a aprobar sus pruebas. La evidencia conjunta está en [DV-US-15](DV-US-15.md). Las referencias posteriores a Azure pendiente describen el corte local original.

Un desarrollador puede elegir `memory` o `azure_event_hubs` mediante `EVENT_TRANSPORT` sin cambiar el generador, el contrato deportivo ni el reproductor. Las fábricas construyen el adaptador correspondiente y ambos recorridos entregan objetos `MatchEvent` equivalentes para la misma secuencia sintética.

La equivalencia Azure se comprobó con el SDK real y clientes de transporte simulados. La comunicación con un servicio desplegado continúa pendiente.

## Alcance implementado

- Enumeración explícita `memory` y `azure_event_hubs`.
- Configuración inmutable `EventTransportSettings`.
- Lectura desde cualquier mapeo y desde `os.environ` por defecto.
- Modo `memory` predeterminado sin variables ni cuenta Azure.
- Validación temprana de valores desconocidos y variables Azure ausentes.
- Fábrica de publicadores.
- Fábrica de consumidores.
- Inyección opcional de clientes Azure para pruebas sin red.
- Creación normal mediante `DefaultAzureCredential` cuando no se inyecta cliente.
- Vista común `events` en consumidores local y Azure.
- Archivo `.env.example` sin credenciales.
- Prueba completa de la misma secuencia en ambos modos.

## Fuera del alcance

- No se cargan automáticamente archivos `.env`; el proceso o la herramienta de ejecución debe suministrar las variables.
- No se probó el cambio contra un Event Hub real.
- No se implementó conmutación durante una reproducción activa.
- No se oculta un fallo Azure cambiando silenciosamente a memoria.
- No se implementó almacenamiento Blob; corresponde a DV-US-09.
- No se añadió configuración HTTP ni interfaz gráfica.

## Entradas y resultados

| Variable | Modo | Descripción |
|---|---|---|
| `EVENT_TRANSPORT` | Ambos | `memory` por defecto o `azure_event_hubs` |
| `EVENT_PRODUCER` | Ambos | Nombre observable del productor; predeterminado `synthetic-generator` |
| `EVENT_HUB_FULLY_QUALIFIED_NAMESPACE` | Azure | `<namespace>.servicebus.windows.net` |
| `EVENT_HUB_NAME` | Azure | Nombre del event hub |
| `EVENT_HUB_CONSUMER_GROUP` | Azure | Grupo utilizado por el consumidor |

No se aceptan ni documentan variables de cadenas de conexión, claves, contraseñas o tokens.

## Cambios técnicos

| Archivo | Cambio | Motivo |
|---|---|---|
| `apps/backend/src/match_intelligence/adapters/messaging/configuration.py` | Configuración, validación y fábricas | Seleccionar adaptadores en el borde de infraestructura |
| `apps/backend/src/match_intelligence/adapters/messaging/azure_event_hubs.py` | Propiedad `events` | Entregar los mismos objetos deportivos que memoria |
| `apps/backend/.env.example` | Variables admitidas sin secretos | Hacer visible la configuración mínima |
| `apps/backend/tests/test_transport_configuration.py` | Siete pruebas automatizadas | Verificar selección, errores, independencia y equivalencia |
| `docs/persona-1-datos-y-vision/historias-de-usuario.md` | Estado y evidencia | Mantener trazabilidad del backlog |
| `docs/persona-1-datos-y-vision/evidencias/README.md` | Registro de DV-US-08 | Mostrar el estado real |

## Diseño

```text
                 EVENT_TRANSPORT
                       │
              ┌────────┴─────────┐
              ▼                  ▼
           memory        azure_event_hubs
              │                  │
    InMemoryPublisher     AzureEventHubPublisher
    InMemoryConsumer      AzureEventHubConsumer
              │                  │
              └────────┬─────────┘
                       ▼
              tuple[MatchEvent, ...]
```

El generador produce `MatchEvent` y no conoce esta selección. Las fábricas están dentro de `adapters/messaging`, el único lugar que importa ambas implementaciones.

## Decisiones técnicas

### Memoria como modo predeterminado

Si `EVENT_TRANSPORT` no está definido, la configuración usa `memory`. Esto conserva el flujo de desarrollo y pruebas sin cuenta, red, SDK configurado o credenciales Azure.

### Fallo temprano de configuración

Elegir `azure_event_hubs` sin namespace, hub o consumidor produce `TransportConfigurationError` antes de abrir una conexión. El mensaje enumera las variables ausentes y no solicita secretos.

### Sin caída silenciosa a memoria

Una selección Azure inválida o una falla del servicio debe ser visible. Cambiar automáticamente a memoria podría hacer creer que la integración distribuida funciona cuando no es así.

### Equivalencia deportiva

El consumidor Azure expone `events` extrayendo el `MatchEvent` validado de cada `ReceivedMatchEvent`. Los metadatos de transporte continúan disponibles en `accepted`, pero Persona 2 puede consumir la misma tupla deportiva que recibe en memoria.

### Límite del SDK

`synthetic.py`, los contratos y el reproductor no importan Azure. La fábrica sí importa adaptadores concretos porque su responsabilidad es elegir infraestructura.

## Context7

DV-US-08 no añadió llamadas nuevas a bibliotecas externas. Reutiliza las factorías y firmas de `azure-eventhub` y `azure-identity` consultadas y verificadas con Context7 durante DV-US-07. Por ello no fue necesaria otra consulta. La lógica nueva usa `dataclass`, `StrEnum`, `Mapping` y `os.environ` de Python 3.12.

## Cobertura de criterios de aceptación

| Criterio | Implementación | Evidencia | Estado |
|---|---|---|---|
| Publicar la misma secuencia en memoria o Event Hubs | Fábrica de publicadores y adaptadores con el mismo método `publish` | `test_same_sequence_is_equivalent_in_memory_and_azure_modes` | Cumplido localmente; Azure real pendiente |
| El generador no importa directamente el SDK | Selección aislada en `adapters/messaging/configuration.py` | `test_synthetic_generator_does_not_import_azure_sdk` | Cumplido |
| Consumidores reciben objetos equivalentes | Ambos consumidores exponen `tuple[MatchEvent, ...]` | `test_same_sequence_is_equivalent_in_memory_and_azure_modes` | Cumplido localmente; Azure real pendiente |

## Pruebas automatizadas

| Prueba | Comportamiento comprobado |
|---|---|
| `test_memory_is_the_default_without_azure_configuration` | Desarrollo local sin cuenta ni variables Azure |
| `test_invalid_transport_is_rejected_with_allowed_values` | Error claro para un selector desconocido |
| `test_azure_transport_requires_names_but_not_secrets` | Variables necesarias y ausencia de cadenas de conexión |
| `test_factories_select_injected_azure_adapters` | Selección de tipos Azure mediante configuración |
| `test_same_sequence_is_equivalent_in_memory_and_azure_modes` | Publicación y consumo equivalente de los diez eventos |
| `test_synthetic_generator_does_not_import_azure_sdk` | Independencia directa del generador |
| `test_example_configuration_contains_no_credentials` | Ejemplo seguro y modo local visible |

## Reproducción

Modo local:

```bash
export EVENT_TRANSPORT=memory
uv run --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_transport_configuration.py -q
```

Configuración Azure:

```bash
export EVENT_TRANSPORT=azure_event_hubs
export EVENT_HUB_FULLY_QUALIFIED_NAMESPACE="<namespace>.servicebus.windows.net"
export EVENT_HUB_NAME="match-events"
export EVENT_HUB_CONSUMER_GROUP="backend"
export EVENT_PRODUCER="synthetic-generator"
```

La prueba real se ejecuta mediante `apps/backend/scripts/event_hubs_smoke.py`, documentada en `infra/azure/README.md`.

## Entorno verificado

| Componente | Versión |
|---|---|
| Python | 3.12.13 |
| uv | 0.11.32 |
| pytest | 9.1.1 |
| azure-eventhub | 5.15.1 |
| azure-identity | 1.26.0 |
| aiohttp | 3.14.4 |
| Azure real | No utilizado |

## Resultado

Pruebas específicas:

```text
.......                                                                  [100%]
7 passed in 0.23s
```

Suite completa:

```text
....................................................................     [100%]
68 passed in 0.51s
```

## Limitaciones y riesgos

- La equivalencia se verificó con serialización real de `EventData`, pero sin red Azure.
- Los tipos concretos de consumidores tienen controles operativos diferentes: memoria recibe un lote; Azure mantiene un ciclo asíncrono.
- Los diagnósticos y checkpoints continúan en memoria.
- `os.environ` se evalúa al llamar `from_mapping`; cambiar variables después no altera una instancia existente.
- La fábrica construye credenciales Azure únicamente cuando el modo seleccionado lo requiere.
- No existe caída automática a memoria ante errores Azure.

## Dependencias y siguientes pasos

- Desplegar DV-US-06, asignar RBAC y ejecutar la prueba de DV-US-07.
- Repetir la misma secuencia con `EVENT_TRANSPORT=memory` y `azure_event_hubs` en integración.
- Persona 2 debe consumir la propiedad `events` y no depender del adaptador concreto.
- DV-US-09 añadirá selección equivalente para almacenamiento local o Blob.
