# Evidencia técnica de DV-US-02

## Identificación

- **Historia:** DV-US-02 · Reproducir el flujo.
- **Estado:** verificada localmente.
- **Prioridad:** P0.
- **Última verificación:** 9 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.
- **Requisitos relacionados:** DV-RF-09, DV-RF-11, RF-18 y RNF-01.

## Objetivo comprobado

Un consumidor de analítica puede recibir progresivamente los eventos normalizados de DV-US-01 sin esperar a un detector de vídeo ni conectarse a Azure. La reproducción permite iniciar, pausar, reanudar, reiniciar y cambiar la velocidad sin modificar los eventos ni su orden lógico.

## Alcance implementado

- Reproductor asíncrono `MatchReplay`.
- Estados explícitos `idle`, `running`, `paused` y `completed`.
- Inicio de una reproducción desde el primer evento.
- Pausa sin publicar el evento cuya espera todavía está en curso.
- Reanudación desde la misma posición.
- Reinicio seguro de una ejecución activa o terminada.
- Factor de velocidad inicial y cambio posterior mediante `set_speed`.
- Publicación local mediante `InMemoryEventPublisher`.
- Puerto `EventPublisher` independiente de cualquier proveedor.
- Función de espera inyectable para pruebas rápidas y deterministas.
- Validación del orden por período y reloj.
- Validación de velocidades positivas y finitas.
- Seguimiento de posición, total de eventos y estado actual.

## Fuera del alcance

- No se expuso todavía el control mediante endpoints HTTP o interfaz gráfica.
- No se implementó adelanto a un tiempo arbitrario; forma parte de la sincronización con vídeo de DV-US-10.
- No se implementó persistencia del cursor después de reiniciar el proceso.
- No se implementó publicación por Azure Event Hubs; corresponde a DV-US-07.
- No se implementó deduplicación en el consumidor; corresponde a DV-US-04.
- No se calculan estado, estadísticas ni narraciones.

## Entradas y resultados

| Elemento | Descripción |
|---|---|
| Eventos | Secuencia de objetos `MatchEvent` ordenada por período y `clock_ms` |
| Publicador | Implementación del puerto asíncrono `EventPublisher` |
| Velocidad | Número finito mayor que cero; valor predeterminado `1.0` |
| Espera | Función asíncrona compatible con `asyncio.sleep`; puede reemplazarse en pruebas |
| Resultado | Eventos publicados progresivamente sin cambiar contenido ni orden |
| Estado observable | Estado, posición, velocidad y cantidad total de eventos |

## Cambios técnicos

| Archivo | Cambio | Motivo |
|---|---|---|
| `apps/backend/src/match_intelligence/application/replay.py` | Reproductor, puerto, estados, controles y validaciones | Implementar el caso de uso sin depender de infraestructura |
| `apps/backend/src/match_intelligence/adapters/messaging/memory.py` | Publicador en memoria | Permitir desarrollo y pruebas sin Azure |
| `apps/backend/src/match_intelligence/adapters/messaging/__init__.py` | Paquete del adaptador | Separar transporte local de la aplicación |
| `apps/backend/tests/test_match_replay.py` | Pruebas de controles, tiempos, orden, estados y transporte local | Demostrar los criterios de aceptación |

## Arquitectura

```text
SyntheticMatch.events
        │
        ▼
   MatchReplay ────────────────┐
        │                      │
        │ EventPublisher       │ Sleep inyectable
        ▼                      ▼
InMemoryEventPublisher     asyncio.sleep
        │
        ▼
consumidor de analítica
```

`MatchReplay` pertenece a la capa de aplicación. Solo conoce el contrato `MatchEvent` y el puerto `EventPublisher`. El almacenamiento en memoria es un adaptador reemplazable; el futuro adaptador de Event Hubs implementará el mismo comportamiento de publicación sin entrar en la lógica del reloj.

## Máquina de estados

```text
                   pause
idle ── start ──> running ─────────> paused
 ^                  ^                  │
 │                  └──── resume ──────┘
 │
 ├──────────── restart ────────────────┐
 │                                    │
 └──────── completed <── último evento┘
```

- `start` solo comienza desde `idle`.
- `pause` solo es válida desde `running`.
- `resume` solo es válida desde `paused`.
- Al publicar el último evento se alcanza `completed`.
- Para iniciar nuevamente una reproducción terminada se debe ejecutar `restart`.
- `restart` incrementa una generación interna, vuelve el cursor a cero e invalida de forma segura cualquier tarea anterior.

## Cálculo del ritmo

Para el primer evento de un período, la espera parte desde el inicio de ese período:

```text
espera_ms = clock_ms
```

Para eventos consecutivos del mismo período:

```text
espera_ms = clock_ms_actual - clock_ms_anterior
```

La velocidad modifica la espera, no el contenido:

```text
espera_segundos = espera_ms / 1000 / velocidad
```

Al comenzar otro período, `clock_ms` vuelve a considerarse desde cero. Una velocidad `4.0` reduce cada espera a una cuarta parte. Cambiar la velocidad afecta las esperas que todavía no comenzaron; no recalcula una espera ya iniciada.

## Pausa y reinicio durante una espera

El reproductor comprueba la compuerta de pausa antes y después de cada espera. Por eso, si se solicita una pausa mientras transcurre un intervalo, el siguiente evento no se publica hasta reanudar.

Cada ejecución captura un número de generación. `restart` incrementa ese número. Una tarea antigua que finaliza su espera detecta que su generación ya no es vigente y termina sin publicar un evento fuera de la nueva reproducción.

## Cobertura de criterios de aceptación

| Criterio | Implementación | Evidencia | Estado |
|---|---|---|---|
| Se puede iniciar la reproducción | `MatchReplay.start` recorre y publica la secuencia | `test_start_publishes_the_complete_match_in_order` | Cumplido |
| Se puede pausar y reanudar | Compuerta `asyncio.Event`, estados y controles `pause`/`resume` | `test_pause_blocks_publication_until_resume` | Cumplido |
| Se puede reiniciar | Generación interna, cursor a cero y estado `idle` | `test_restart_invalidates_an_active_run_and_starts_from_the_beginning` | Cumplido |
| Se puede acelerar | Factor `speed` y control `set_speed` | `test_acceleration_changes_delays_but_not_events`, `test_speed_can_be_changed_before_starting` | Cumplido |
| Cambiar velocidad no cambia contenido ni orden | Solo se divide la duración de espera; los mismos objetos llegan al publicador | `test_acceleration_changes_delays_but_not_events` | Cumplido |
| La reproducción local no necesita Azure | Adaptador en memoria sin SDK, credenciales ni variables obligatorias | `test_local_replay_has_no_azure_configuration_dependency` | Cumplido |

## Pruebas automatizadas

| Prueba | Comportamiento comprobado |
|---|---|
| `test_start_publishes_the_complete_match_in_order` | Publicación completa, cursor final y estado `completed` |
| `test_pause_blocks_publication_until_resume` | Ningún evento se publica mientras la pausa está activa |
| `test_restart_invalidates_an_active_run_and_starts_from_the_beginning` | Una ejecución antigua no publica después del reinicio y la nueva comienza en cero |
| `test_acceleration_changes_delays_but_not_events` | Velocidad cuatro reduce esperas a un cuarto sin alterar eventos |
| `test_speed_can_be_changed_before_starting` | El control público modifica la velocidad utilizada |
| `test_local_replay_has_no_azure_configuration_dependency` | El flujo completo funciona sin variables de Azure |
| `test_speed_must_be_finite_and_positive` | Rechazo de cero, valores negativos, `NaN` e infinito; cuatro casos parametrizados |
| `test_invalid_state_transitions_are_rejected` | Pausa y reanudación fuera de estado producen errores explícitos |
| `test_events_must_be_ordered_within_the_period` | Rechazo de una secuencia cuyo reloj retrocede |

El archivo contiene nueve funciones de prueba y doce casos ejecutados debido a la parametrización de velocidades inválidas.

## Reproducción

Desde la raíz del repositorio:

```bash
uv python install 3.12
uv sync --project apps/backend --extra dev
uv run --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_match_replay.py -q
```

Para ejecutar toda la suite del backend:

```bash
uv run --project apps/backend --python 3.12 \
  pytest apps/backend/tests -q
```

## Entorno verificado

| Componente | Versión |
|---|---|
| Python | 3.12.13 |
| pytest | 9.1.1 |
| uv | 0.11.32 |
| Contrato de eventos | MatchEvent 1.0 |
| Transporte probado | Memoria local |

## Resultado

Verificación específica de DV-US-02 ejecutada el 9 de octubre de 2026:

```text
............                                                             [100%]
12 passed in 0.07s
```

Verificación completa del backend:

```text
.....................                                                    [100%]
21 passed in 0.08s
OpenAPI: ok
```

## Trazabilidad adicional

- El publicador recibe los mismos objetos `MatchEvent` que produjo DV-US-01.
- La reproducción no reescribe `event_id`, `match_id`, relojes, coordenadas ni relaciones.
- El orden publicado coincide con el orden de entrada.
- La posición indica cuántos eventos se publicaron en la ejecución vigente.
- Las pruebas sustituyen la espera real por dobles controlados; comprueban los intervalos calculados sin hacer más lenta la suite.

## Limitaciones y riesgos

- No se midió todavía precisión temporal contra un reloj de pared; las pruebas verifican el cálculo de intervalos.
- `asyncio.sleep` puede despertar después del instante solicitado según la carga del sistema operativo. La meta de latencia todavía está pendiente en el proyecto.
- La velocidad cambia las esperas futuras, no interrumpe ni recalcula una espera ya iniciada.
- El publicador en memoria no persiste eventos y se pierde al terminar el proceso.
- No se acepta una secuencia desordenada. La política para eventos tardíos se implementará por separado en DV-US-05.
- El control todavía no está conectado a FastAPI ni React.
- La igualdad de contenido se comprobó localmente; Event Hubs necesitará pruebas de serialización y consumo propias.

## Dependencias y siguientes pasos

- DV-US-03 validará entradas arbitrarias antes de que lleguen al reproductor.
- DV-US-04 agregará idempotencia al proceso de ingesta.
- DV-US-07 implementará el adaptador de Event Hubs sobre el puerto de publicación.
- DV-US-10 conectará el control de reproducción con el tiempo del vídeo.
- Persona 2 ya puede consumir el `InMemoryEventPublisher` o implementar otro consumidor del puerto para construir el estado del partido.
