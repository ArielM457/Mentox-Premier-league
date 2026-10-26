# Resumen para el daily · Persona 2 (estado y analítica)

Actualizado el 25 de octubre de 2026. Rama `persona-2/estado-analitica`.

## En un minuto

- **Hecho:** la analítica ya funciona en Azure con datos guardados.
  - La API de The Prime Moment usa el motor real de Persona 2, no la analítica provisional.
  - Lee los partidos y el seguimiento desde una base en Supabase.
  - La pestaña Resumen explica cada momento con cifras medidas.
  - La pestaña «Visión IA» también funciona en Azure: la imagen de la API ya trae los resultados de los modelos de Persona 1.
  - Pasan 413 pruebas. Las 10 que fallan ya fallaban en `main` y son de Persona 1 (ver más abajo).
- **Desde el último daily:**
  - Base de datos con partidos ficticios en Supabase.
  - Script que despliega todo en Azure.
  - La API usa la analítica real.
  - Unión con `main`, con `develop` y con `integration/modelos-frontend-20261025` (Persona 1).
  - Dos reglas nuevas: situaciones del partido y lecturas «¿qué habría pasado si…?».
  - Pestaña Resumen con datos.
  - Guía para que cualquiera del equipo cree el entorno.
- **Demo en Azure:**
  - Interfaz: <https://ca-mentoxp2-web.politegrass-7d829700.eastus2.azurecontainerapps.io>
  - API: <https://ca-mentoxp2-api.politegrass-7d829700.eastus2.azurecontainerapps.io/docs>
  - El tablero local sigue en [`demo/tablero.html`](demo/tablero.html).
- **Flujo continuo probado en Azure:** 178 eventos por Event Hubs, todos aplicados a tiempo, con 51 ms de transporte medio y 27 ms de procesamiento. El registro quedó en Blob y en Supabase.
- **Siguiente:**
  - Acordar los contratos con Persona 3.
  - Subir la rama y abrir el PR cuando el equipo lo decida.
- **Bloqueos y avisos:**
  - Los contratos de Persona 3 todavía rechazan las salidas del motor.
  - La tabla de eventos de Supabase que llegó con `main` mezcla eventos de partidos distintos.

## Novedades desde el último daily

### Base de datos en Supabase

| Qué | Detalle |
|---|---|
| Esquema | `match_analytics`, separado del resto y sin exponer en la API pública de Supabase; RLS activo |
| Datos ficticios | 3 partidos (aceptación, analítica de 22 jugadores y partido en vivo de Persona 4), sus eventos, 92 982 posiciones simuladas con el formato de Persona 1 y el análisis de cada partido |
| Carga | `supabase_seed.py --schema`: crea las tablas, aplica las migraciones y reemplaza los partidos. Se puede repetir |
| Consulta | Vistas listas para SQL: decisiones de atención, métricas finales, propuestas de momentos y avisos de seguimiento |

La base de datos es una decisión de Persona 2, todavía por confirmar con el equipo. No reemplaza a Event Hubs ni a Blob Storage. Es PostgreSQL estándar, así que también funcionaría en Azure Database for PostgreSQL.

### Despliegue en Azure

`./infra/azure/deploy-analytics.ps1` crea todo en un grupo de recursos y en dos fases, con la construcción de las imágenes entre ambas.

| Recurso | Para qué |
|---|---|
| Event Hubs (`match-events`, `match-insights`) y Storage | Transporte de eventos y salidas; registros de cada análisis |
| Container Registry e identidad administrada | Imágenes y permisos sin claves |
| Container Apps en modo `WorkloadProfiles` | API, interfaz, procesador continuo y trabajo que repite partidos de Supabase |
| Log Analytics | Registros, con tope de 0,1 GB al día |

- **Costo real hasta hoy:** 6,51 USD de los 100 de Azure for Students. La previsión para octubre es 12,49 USD. Casi todo es Event Hubs, alrededor de 1 USD al día.
- **Al terminar la demo** hay que borrar el grupo con `remove-analytics.ps1`.

Llegar hasta aquí costó tres intentos. Quedaron resueltos en el script y documentados:

1. **Modo Express.** Azure crea ahora los entornos en ese modo, que no admite trabajos. La plantilla pide `WorkloadProfiles` y el script recrea el entorno si hace falta.
2. **Suspensión.** Azure suspendió un entorno recreado con el mismo nombre (`ManagedClusterSuspended`). El entorno nuevo usa otro nombre, y el script comprueba 90 s después de desplegar que siga activo.
3. **Cadena solo IPv6.** Con la conexión directa de Supabase, Azure no alcanzaba la base. Ahora el script rechaza esa cadena antes de desplegar, y la API arranca con los partidos sintéticos si no alcanza la base.

### La API usa la analítica real

- `PresentationAnalytics` pone `MatchAnalytics` detrás del `AnalyticsPort` de Persona 4. Entrega sus mismos contratos.
- Dos variables eligen el modo:
  - `ANALYTICS_ENGINE=persona2` usa el motor real; sin ella, se mantiene el provisional para no romper las pruebas de Persona 4.
  - `MATCH_SOURCE=supabase` lee los partidos de la base.
- En Azure, la API comprobada lee los 3 partidos y el seguimiento de Supabase: el estado trae las velocidades de los 22 jugadores.

### Unión con `main`, `develop` y la integración de Persona 1

- **`main` trajo la integración de Persona 1:** visión, enrutamiento de eventos y su propia persistencia en Supabase (esquema `public`). No choca con la nuestra.
- **`develop` trajo la experiencia en vivo de Persona 4:**
  - partidos de 11 contra 11;
  - un partido en vivo con faltas, tarjetas, una lesión y reanudaciones;
  - la cancha con seguimiento;
  - la previa táctica.

  También cambió el contrato de eventos de Persona 1 (cinco tipos y tres campos nuevos) y partes de nuestra analítica.

Lo que adapté:

| Tema | Qué se hizo |
|---|---|
| Cancha en vivo | `develop` la construyó sobre el formato viejo de seguimiento. Ahora usa nuestro modelo y entrega el mismo JSON (`TrackingFrame v1`), sin cambios en la interfaz. La simulación de posiciones volvió a `src/` porque la API la usa al ejecutarse |
| Faltas, tarjetas y lesiones | Regla nueva `situation@1`. Ahora el motor real también las propone como momentos: la roja siempre, amarillas y lesión en todos los modos, faltas solo para el analista |
| Campos nuevos de los eventos | Migración nueva en Supabase para guardar receptor, situación y duración de la detención |
| Pestañas de la interfaz | Se conserva la estructura nueva de `develop`, y la visión de Persona 1 tiene su propia pestaña, «Visión IA» (ver la unión con su rama más abajo) |
| Imagen de Docker | Conserva la estructura del repositorio para que la previa táctica encuentre sus datos en Azure |

### Pestaña Resumen con analítica

Antes, el «resultado estimado» era el mismo texto para cualquier momento y la cancha usaba una formación fija. Ahora la ruta `/moments/{id}/analysis` entrega lo que sabe el motor y la pestaña lo muestra:

- **Por qué es un momento:** prioridad, umbral del perfil y cada motivo con sus puntos.
- **Datos medidos:** avance, duración, pases, distancia del remate… con unidades.
- **Cancha real:** las posiciones de ese instante, con los jugadores de la alternativa marcados.
- **¿Qué habría pasado si…? (`what_if@1`):** cada opción compara el instante real con una alternativa medida:
  - el pase un segundo antes: espacio del pasador y del receptor;
  - el remate un segundo antes: distancia, ángulo y espacio del rematador;
  - el apoyo hacia el compañero más libre: su espacio frente al del compañero más cercano;
  - el arquero 3 m más adelante: distancia al balón y a su línea de gol.

Si una opción no aplica, la pestaña lo dice («el momento no incluye un remate»). Las posiciones son simuladas y la pestaña lo avisa: compara espacios, no predice el resultado. Funciona con el motor real y con el provisional, y ya responde desde Azure.

### Unión con `integration/modelos-frontend-20261025`

Esta rama de Persona 1 une `develop` con su visión. También prepara el despliegue de sus modelos con GPU en Azure: Roboflow y SoccerNet, con las historias DV-US-30 y DV-US-31. No toca la analítica.

- **Ya está unida** a nuestra rama (commit `5d2b136`).
- **Conflictos:** hubo 2, en la interfaz, y se resolvieron con su solución. El panel de visión pasa a una pestaña propia, «Visión IA», en lugar de ir dentro de la pestaña Partido. Así deja de pedir datos de visión en la pestaña principal.
- **Resumen:** conserva el `matchId` con el que carga el análisis del momento.
- **Comprobación:** las pruebas dan el mismo resultado (413 pasan; las 10 que fallan son las de `main`). La interfaz compila y en local muestra las cinco pestañas sin errores.

Ahora nuestra rama contiene `main`, `develop` y esta integración; las demás ramas no tienen nada que falte en la nuestra.

### Pestaña «Visión IA» en local y en Azure

Decía «Visión no disponible» por tres motivos:

1. **Ruta de los archivos.** La API busca los resultados de los modelos en `experiments/…/output-real`, que solo existe en el equipo de Persona 1. Las copias están en `docs/mentox-modelos-20261023T045413Z/resultados`. En local basta con apuntar tres variables a esa carpeta.
2. **Finales de línea.** En Windows, Git cambiaba esos archivos y su huella SHA-256 dejaba de coincidir. Un `.gitattributes` lo evita.
3. **Imagen.** En Azure no estaban los archivos. Ahora la imagen de la API se construye desde la raíz del repositorio y trae los tres resultados (8,5 MB) con sus variables. El `.dockerignore` de la raíz solo deja pasar lo que usan las imágenes.

En Azure se actualizaron la API, la interfaz, el procesador y el trabajo `replay` a la imagen `78cf10c`. Solo cambió la imagen; la cadena de Supabase siguió como secreto. La API responde `ready`, con 16 324 detecciones de Roboflow, 127 acciones de SoccerNet y 12 candidatos de fusión, y sigue leyendo los 3 partidos de Supabase. La imagen no incluye el vídeo, que la pestaña no necesita.

### Guía para el equipo

[`docs/14-despliegue-en-azure.md`](../14-despliegue-en-azure.md) explica, paso a paso:

- si conviene un despliegue compartido o uno por persona (se recomienda uno compartido);
- qué instalar;
- cómo crear la base y desplegar;
- cómo mostrar el flujo en directo;
- cómo cuidar los créditos;
- cómo manejar secretos;
- una tabla con todos los errores que aparecieron y su solución.

## Qué hace el motor con cada evento

```text
MatchEvent 1.0
  → estado: marcador, reloj, período y posesión por tramos
  → estadísticas: tiros, pases, precisión, recuperaciones, presión, pases progresivos…
  → jugadas: agrupa recuperación, pases y tiro en una sola secuencia
  → reglas: progresión rápida, recuperación y tiro, presión sostenida, hitos de jugador,
            cambio de control, fase de caos y situaciones (faltas, tarjetas, lesiones)
  → atención: decide qué momento merece salir en pantalla y por qué
  → salida: MatchSnapshot v1 + InsightCandidate v1 (+ registro de decisiones)

Observaciones de visión de Persona 1 (VisualTrackObservation + identidad resuelta)
  → seguimiento: distancia, velocidad, sprints, velocidad del balón y del tiro,
                 presión por cercanía, forma del equipo y avisos por umbral
  → cancha: cuadros para dibujar el partido en vivo
  → resumen: posiciones del momento y lecturas «¿qué habría pasado si…?»
```

Cuatro ideas para explicarlo:

1. **Toda cifra se puede comprobar.** Cada número lleva fórmula, unidad, versión y los eventos o pistas de donde sale. Si faltan datos, aparece como «no disponible», nunca como cero.
2. **La IA no calcula cifras.** El motor calcula; los agentes de Persona 3 explican. Así un agente no puede inventar un dato.
3. **La prioridad se explica.** Es una suma visible de motivos, y ahora se ve en la pestaña Resumen.
4. **Personalización sin cambiar los hechos.** Los perfiles cambian qué momentos salen, pero no las cifras. Los goles y las rojas del rival salen siempre.

Con el partido de prueba de 178 eventos, el perfil casual recibe 14 momentos, el analista 33 y el modo jugador de L. Sol 9. En el partido en vivo, el casual recibe 7 y el analista 12.

## Qué está acoplado hoy

| Con quién | Qué se conectó | Estado |
|---|---|---|
| Persona 1 (datos) | Contrato `MatchEvent 1.0` (con los campos nuevos), validación, deduplicación y eventos tardíos | Probado en local |
| Persona 1 (vídeo y visión) | `MatchStateRebuilder` y las observaciones `VisualTrackObservation` con identidad resuelta | Probado con observaciones simuladas |
| Persona 1 (Azure) | Event Hubs y Storage de su plantilla, reutilizados sin cambios | Desplegado |
| Persona 4 (API e interfaz) | `AnalyticsPort` con el motor real, cancha en vivo, análisis de momentos en Resumen | Integrado y desplegado en Azure |
| Persona 3 (agentes) | Tiene los contratos y ejemplos de Persona 2 | Bloqueado: sus contratos rechazan las salidas del motor |

## Qué usa datos simulados (mocks)

| Parte | Qué se simula | Qué lo reemplaza |
|---|---|---|
| Partidos | 3 partidos sintéticos (el reto lo exige) | Partidos más largos de Persona 1 |
| Posiciones de jugadores y balón | `adapters/sources/tracking_mock.py`, con el formato de Persona 1 y origen `simulated_fixture` | Las observaciones reales de vídeo de Persona 1, sin cambiar la analítica |
| Distancias, velocidades, cancha y lecturas del Resumen | El cálculo es real, sobre posiciones simuladas | Lo mismo con posiciones reales |
| Frases de los momentos | Narración provisional de Persona 4 | Los agentes de Persona 3 |

**No es simulado:**
- el estado, las estadísticas, los patrones, los indicadores, los momentos, las prioridades y los motivos;
- el despliegue en Azure y la base en Supabase.

**xT, xG y VAEP** siguen **desactivados** hasta tener datos con licencia para entrenarlos.

## Qué recibe Persona 3 (agentes)

**`InsightCandidate v1` (momento candidato):** un momento que vale la pena narrar, con todo lo necesario para explicarlo sin inventar nada. Ejemplo real del gol, recortado:

```json
{
  "candidate_id": "moment-evt-010",
  "kind": "goal",
  "priority": 100,
  "team_id": "team-aurora",
  "facts": [
    {"key": "goals", "team_id": "team-aurora", "value": 1, "unit": "count",
     "origin": "event_count", "formula_version": "goals@1", "source_event_ids": ["evt-010"]},
    {"key": "shot_distance_m", "value": 14.2, "unit": "meters", "origin": "derived"},
    {"key": "seconds_since_recovery", "value": 11.0, "unit": "seconds"}
  ],
  "source_event_ids": ["evt-006", "evt-007", "evt-008", "evt-009", "evt-010"],
  "evidence_limits": [
    "Relación temporal entre ganar el balón y el tiro; los eventos no demuestran que una acción causara la otra."
  ],
  "reasons": [{"code": "base_kind", "points": 80}, {"code": "measured_fact", "points": 13},
              {"code": "combined_signals", "points": 5}, {"code": "novelty", "points": 10}]
}
```

| Campo | Para qué le sirve al agente |
|---|---|
| `kind` | Qué pasó. Hay 14 tipos: gol, tiro, recuperación y tiro, progresión rápida, presión sostenida, cambio de control, fase de caos, hito de jugador, recuperación alta, pase progresivo, falta, amarilla, roja y detención por lesión |
| `facts` | Las únicas cifras que puede decir, cada una con unidad y eventos de origen |
| `evidence_limits` | Lo que **no** puede afirmar |
| `reasons` | Por qué se eligió el momento |
| `source_event_ids` | Para que el verificador contraste cada afirmación |

**`MatchSnapshot v1` (estado):** el partido en un instante, con unas 250 cifras (unas 340 con seguimiento). Sirve para responder preguntas y para los resúmenes.

**Nuevo para Persona 3:** el análisis de un momento (`/moments/{id}/analysis`) trae lecturas «¿qué habría pasado si…?» medidas. Su agente contrafactual puede partir de ellas en vez de inventar el escenario.

**Qué hay que acordar con Persona 3:**
- Usar estos contratos en lugar de sus copias, o ajustar las cuatro reglas que hoy rechazan las salidas.
- Quién implementa el filtro y el catálogo de jugadas (`RoutingDecision v1`, `PlayContext v1`) que el plan asigna a Persona 2.
- Mantener Event Hubs como canal (decisión 10).

## Qué recibe cada una de las demás personas

| Persona | Qué recibe | Qué necesito de ella |
|---|---|---|
| **Persona 4 (API e interfaz)** | El motor real detrás de su `AnalyticsPort`, la cancha en vivo con nuestro modelo, el análisis de momentos y el despliegue en Azure | Revisar los cambios en sus archivos (registro de partidos, narración provisional, Resumen y pestañas) y decidir si `persona2` pasa a ser el motor predeterminado |
| **Persona 1 (datos y visión)** | La analítica de seguimiento que consume sus observaciones y la cadena de Azure que reutiliza su plantilla | Avisar cuando cambien los resultados de sus modelos (la imagen copia los de `docs/mentox-modelos-20261023T045413Z`) y corregir la tabla `match_events` de su Supabase. Coordinar los cambios de contrato, indicar en las observaciones qué pista es el balón o un portero y conseguir un vídeo permitido |
| **Persona 5 (UX/UI)** | Los bloques nuevos del Resumen: motivos, datos medidos y la tabla de alternativas | Revisar su diseño en claro y oscuro y en móvil |

Detalle de los avisos para Persona 1:

- **Archivos de experimentos:** su panel de visión los busca en `experiments/…/output-real`, que solo existe en su equipo. Ya funciona apuntando las variables `MENTOX_*_ARTIFACT` a las copias de `docs/mentox-modelos-20261023T045413Z/resultados`, con lo que pasan 8 de las 10 pruebas que fallaban. Las 2 restantes tienen esa ruta fija en la prueba. La imagen de Azure copia esas mismas tres copias; si publica resultados nuevos en otra carpeta, hay que cambiarla en `apps/backend/Dockerfile` y en el `.dockerignore` de la raíz.
- **Panel de visión:** decía «Visión no disponible» aunque la API respondía `ready`, porque leía un campo que la API no envía. Ya está corregido.
- **Tabla `match_events`:** usa `event_id` como clave única, así que dos partidos con `evt-001` se pisan.

## Cómo se integra con Azure

```text
Supabase (match_analytics) ──► API (Container Apps) ──► interfaz (nginx, Container Apps)
        ▲                          motor de Persona 2
        │
Trabajo replay ──► Event Hubs · match-events ──► procesador continuo
                                                   ├─► Event Hubs · match-insights
                                                   │      narrative → Persona 3
                                                   │      experience → Persona 4
                                                   ├─► Blob Storage · analytics (registro con SHA-256)
                                                   └─► Supabase · analytics_runs
```

**Listo y verificado en Azure:**
- Infraestructura completa con identidad administrada, sin claves.
- La API con el motor real, que lee Supabase.
- La interfaz, el análisis de momentos y la previa táctica.

**Flujo continuo verificado el 25 de octubre:** el trabajo `replay` publicó en `match-events` los 178 eventos del partido de analítica a 8× (como `synthetic-analytics-001-live-20261026003858`). El procesador los aplicó todos a tiempo, con un transporte medio de 51 ms (p95 71 ms) y un procesamiento medio de 27 ms (p95 35 ms). Propuso momentos en 19 eventos y, 30 s después del último, guardó el registro `run-c57436ad-…` con 7 archivos en Blob y en Supabase.

**Falta:**
- La prueba de humo `analytics_azure_smoke.py`.
- Cerrar con Persona 3 que el canal sigue siendo Event Hubs.

Medido en local: unos 3 ms de procesamiento por evento y entre 0,1 y 0,15 s por estado con seguimiento.

## Para profundizar

- [Despliegue en Azure paso a paso (para todo el equipo)](../14-despliegue-en-azure.md)
- [Despliegue en Azure y Supabase (detalle técnico)](despliegue-azure-supabase.md)
- [README de Persona 2](README.md)
- [Catálogo de métricas](catalogo-de-metricas.md)
- [Reglas de patrones y atención](reglas-de-patrones-y-atencion.md)
- [Analítica de seguimiento](analitica-de-seguimiento.md)
- [Evidencias](evidencias/README.md)
