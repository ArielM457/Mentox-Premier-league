# Evidencia técnica de DV-US-01

## Identificación

- **Historia:** DV-US-01 · Generar el partido de aceptación.
- **Estado:** verificada localmente.
- **Prioridad:** P0.
- **Última verificación:** 9 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.
- **Requisitos relacionados:** DV-RF-01, DV-RF-02, DV-RF-03, RF-01, RF-02, RF-03, RF-06 y RNF-01.

## Objetivo comprobado

El equipo puede generar un partido sintético corto y repetir exactamente sus metadatos, eventos e identificadores usando la misma configuración y semilla. El partido sirve como entrada estable para desarrollar y probar los módulos posteriores sin esperar a Roboflow, SoccerNet, Azure ni un vídeo.

## Alcance implementado

- Generador `generate_acceptance_match` configurable mediante `seed` y `match_id`.
- Metadatos de dos equipos ficticios, ocho jugadores, dimensiones del campo y direcciones de ataque para dos períodos.
- Diez eventos normalizados mediante `MatchEvent 1.0`.
- Cobertura de pase, tiro, entrada, cambio de posesión, presión y recuperación.
- Fase de control, transición rápida y momento decisivo terminado en gol.
- Coordenadas normalizadas con una variación pseudoaleatoria reproducible.
- Identificadores estables `evt-001` a `evt-010`.
- Relación explícita entre acciones mediante `related_event_ids`.
- Tiempo de partido y tiempo de vídeo diferenciados.
- Procedencia `synthetic` y ausencia de una confianza inventada.

## Fuera del alcance

- La reproducción progresiva pertenece a DV-US-02.
- La validación de entradas arbitrarias y sus errores pertenece a DV-US-03.
- La deduplicación durante la ingesta pertenece a DV-US-04.
- El transporte por Azure Event Hubs pertenece a DV-US-07 y DV-US-08.
- La sincronización operativa con un reproductor pertenece a DV-US-10.
- Roboflow, SoccerNet y la fusión desde vídeo pertenecen a DV-US-11 a DV-US-13.
- El generador no calcula marcador, estadísticas, xG, xT, VAEP ni narraciones.

## Entradas y resultados

| Elemento | Descripción |
|---|---|
| Entrada `seed` | Entero usado por una instancia local de `random.Random`; valor predeterminado `2026` |
| Entrada `match_id` | Identificador estable del partido; valor predeterminado `synthetic-acceptance-001` |
| Resultado | `SyntheticMatch` inmutable con `MatchMetadata` y una tupla de `MatchEvent` |
| Contrato | Esquema `1.0` definido por los modelos del dominio |
| Datos externos | Ninguno |

## Escenario deportivo generado

| Tramo | Eventos | Evidencia representada |
|---|---|---|
| Control | `evt-001` a `evt-005` | Presión de Río Unido, circulación de Aurora FC, entrada y cambio de posesión |
| Transición | `evt-006` a `evt-009` | Recuperación de Aurora FC, progresión mediante pases y presión rival fallida |
| Momento decisivo | `evt-010` | Tiro de Aurora FC con resultado `goal`, relacionado con la recuperación y los pases anteriores |

Los equipos y jugadores son ficticios. El conjunto no reproduce ni redistribuye datos reales de partidos de la Premier League.

## Cambios técnicos

| Archivo | Cambio | Motivo |
|---|---|---|
| `apps/backend/src/match_intelligence/adapters/sources/synthetic.py` | Generador, escenario, metadatos y eventos | Implementar la fuente sintética de aceptación |
| `apps/backend/src/match_intelligence/domain/contracts.py` | Contratos de metadatos y eventos con Pydantic 2 y `StrEnum` | Compartir modelos independientes del adaptador HTTP |
| `apps/backend/src/match_intelligence/adapters/http/schemas.py` | Reexporta los contratos del dominio | Evitar dos definiciones incompatibles del mismo contrato |
| `apps/backend/tests/test_synthetic_match.py` | Nueve pruebas automatizadas | Demostrar criterios y coherencia interna |
| `.python-version` | Fija Python 3.12 | Reproducir el intérprete del proyecto |
| `apps/backend/pyproject.toml` | Declara Python `>=3.12,<3.14` y Pydantic directo | Expresar compatibilidad y dependencias reales |
| `apps/backend/uv.lock` | Bloquea las versiones resueltas | Repetir el entorno del backend |

## Decisiones técnicas

### Generador local de números pseudoaleatorios

Se usa `random.Random(seed)` en lugar del generador global. Esto evita que otra parte del proceso cambie el estado aleatorio del partido. La semilla solo añade una pequeña variación a las posiciones; la historia deportiva y los identificadores permanecen definidos por el escenario.

### Contratos validados al construir

`MatchMetadata`, `MatchEvent` y sus objetos internos son modelos Pydantic. Las coordenadas quedan entre 0 y 100, los tiempos no pueden ser negativos y los valores enumerados se limitan al contrato. La construcción falla si el generador intenta producir una estructura inválida.

### Python 3.12 y `StrEnum`

El proyecto usa Python 3.12. Los tipos `EventType`, `EventOutcome`, `EventSource` y `AttackDirection` heredan de `StrEnum`, por lo que mantienen semántica de enumeración y se serializan como cadenas del contrato.

### Inmutabilidad del contenedor

`SyntheticMatch` es una dataclass congelada y sus eventos se entregan en una tupla. Esto impide reemplazar accidentalmente el conjunto completo o su secuencia desde el contenedor. Los modelos Pydantic internos todavía no están congelados; si aparece una necesidad de inmutabilidad profunda, deberá tratarse como una decisión de contrato separada.

## Cobertura de criterios de aceptación

| Criterio | Implementación | Evidencia | Estado |
|---|---|---|---|
| Misma configuración y semilla producen los mismos metadatos, eventos e identificadores | `Random(seed)`, escenario ordenado e identificadores derivados del número de evento | `test_same_seed_produces_the_same_match` | Cumplido |
| El partido contiene todos los tipos exigidos por RF-02 | Los diez eventos incluyen los seis valores de `EventType` | `test_acceptance_match_contains_every_required_event_type` | Cumplido |
| Existe una secuencia de control, una transición y un momento decisivo | El escenario divide los eventos en control, recuperación/progresión y tiro con gol | `test_acceptance_match_contains_control_transition_and_decisive_moment` | Cumplido |
| No contiene datos reales de partidos de la Premier League | Equipos, jugadores e identificadores ficticios; procedencia `synthetic` | `test_acceptance_match_is_synthetic_and_uses_fictional_teams` | Cumplido |

## Pruebas automatizadas

| Prueba | Comportamiento comprobado |
|---|---|
| `test_same_seed_produces_the_same_match` | Igualdad completa de metadatos y eventos para la misma semilla |
| `test_custom_match_id_is_preserved_in_metadata_and_events` | Propagación del `match_id` a todos los objetos |
| `test_different_seeds_change_the_generated_positions` | La semilla participa realmente en la generación |
| `test_acceptance_match_contains_every_required_event_type` | Cobertura exacta de los seis tipos de evento |
| `test_acceptance_match_contains_control_transition_and_decisive_moment` | Orden, relaciones y resultado de las tres escenas |
| `test_acceptance_match_is_synthetic_and_uses_fictional_teams` | Procedencia sintética, nombres ficticios y ausencia de confianza inventada |
| `test_metadata_is_complete_and_internally_consistent` | Dimensiones, direcciones, equipos, jugadores y autoría coherentes |
| `test_event_identifiers_and_clocks_are_stable_and_ordered` | Identificadores únicos y reloj creciente |
| `test_every_related_event_reference_exists_and_points_backwards` | Integridad y orden causal de las referencias |

## Reproducción

Desde la raíz del repositorio:

```bash
uv python install 3.12
uv sync --project apps/backend --extra dev
uv run --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_synthetic_match.py -q
```

Para consultar las versiones usadas:

```bash
uv run --project apps/backend --python 3.12 python --version
uv run --project apps/backend --python 3.12 python -c \
  "import fastapi, pydantic; print(fastapi.__version__, pydantic.__version__)"
```

## Entorno verificado

| Componente | Versión |
|---|---|
| Python | 3.12.13 |
| FastAPI | 0.143.0 |
| Pydantic | 2.12.5 |
| pytest | 9.1.1 |
| Gestor | uv 0.11.32 |
| Sistema de contratos | MatchEvent 1.0 |

## Resultado

Verificación ejecutada el 9 de octubre de 2026:

```text
Python 3.12.13
.........                                                                [100%]
9 passed in 0.06s
FastAPI 0.143.0
Pydantic 2.12.5
```

## Trazabilidad adicional

- Los diez eventos usan el mismo `match_id` que los metadatos.
- Los jugadores autores pertenecen a uno de los dos equipos declarados.
- Las coordenadas se normalizan al intervalo de 0 a 100.
- `clock_ms` pertenece al reloj del período.
- `video_time_ms` mantiene un desfase sintético fijo de dos segundos y no afirma que el evento haya sido detectado desde vídeo.
- Las referencias de `related_event_ids` apuntan a eventos anteriores existentes.

## Limitaciones y riesgos

- El escenario solo representa un tramo corto del primer período, no un partido reglamentario completo.
- Ocho jugadores son suficientes para las acciones de la muestra, pero no representan plantillas completas.
- El valor de `video_time_ms` es sintético; la sincronización con vídeo se demostrará en DV-US-10.
- La coherencia semántica por tipo de evento todavía no tiene validadores específicos. Por ejemplo, el contrato general aún permite combinaciones de tipo y resultado que no tendrían sentido deportivo. Esto se tratará en DV-US-03.
- La historia no prueba deduplicación, eventos tardíos, persistencia ni transporte.
- La prueba confirma que los nombres creados son ficticios; no constituye una auditoría automática contra todos los conjuntos deportivos existentes.

## Dependencias y siguientes pasos

- DV-US-03 consumirá estos objetos para implementar validación y errores estructurados.
- DV-US-04 utilizará sus identificadores estables para probar idempotencia.
- DV-US-02 reproducirá esta misma tupla progresivamente.
- Persona 2 puede consumir la muestra desde ahora, pero deberá depender del contrato público y no de los detalles internos del generador.
