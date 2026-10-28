# **Persona 4: API y experiencia funcional**

Este documento registra lo implementado por Persona 4, cómo se verificó y qué falta. El plan original está en [el plan de Persona 4](../plan-de-desarrollo/persona-4-api-y-frontend.md).

- **Estado:** verificado localmente con datos sintéticos y adaptadores provisionales.
- **Última verificación:** 23 de octubre de 2026.
- **Ramas:** `feat/persona-4-api-frontend` (API) y `feat/persona-4-figma-ui` (interfaz con el diseño de Persona 5).

## **Qué existe ahora**

**Backend.** Rutas nuevas bajo `/api/v1/matches`, documentadas en Swagger (`http://localhost:8000/docs`, grupo «Partido y experiencia»).

| Ruta | Para qué sirve |
|---|---|
| `GET /matches` · `POST /matches` | Listar y cargar un partido sintético. `scenario`: `acceptance` (partido corto de Persona 1) o `analytics` (partido de dos tiempos de Persona 2). `inject_error_in` provoca un error controlado para la demo. |
| `GET /matches/{id}` | Metadatos, duración y fuente de vídeo. |
| `GET /matches/{id}/preview` | Formaciones, tácticas reproducibles e información previa sintética aprobada. |
| `GET /matches/{id}/events?until_video_ms=` | Eventos ya ocurridos; nunca futuros. |
| `GET /matches/{id}/tracking?from_video_ms=&to_video_ms=` | Ventana de posiciones de 22 jugadores y balón para interpolación; máximo 30 segundos. |
| `GET /matches/{id}/state?video_time_ms=` | `MatchSnapshot v1`. |
| `GET /matches/{id}/overlays?until_video_ms=&preferencias` | `OverlayMessage v1` planificados hasta ese tiempo. |
| `GET /matches/{id}/stream?from_video_ms=&speed=&preferencias` | Canal en directo con Server-Sent Events. |
| `GET /matches/{id}/drafts/{draft_id}/sources` | Explicación y eventos de origen de un mensaje. |
| `POST /matches/{id}/questions` | Preguntas sobre el partido hasta el tiempo actual. |
| `GET /matches/{id}/summary?preferencias` | Resumen final; queda pendiente de revisión. |
| `GET /matches/{id}/editorial` · `POST …/editorial/{draft_id}/review` | Cola de revisión, aprobar o rechazar. |
| `GET /matches/{id}/editorial/{draft_id}/published` | Responde `409` mientras falte la aprobación. |
| `POST /matches/{id}/reports` · `GET …/reports` | Reportar un error y consultar la verificación. |
| `GET /matches/{id}/playback` · `POST …/playback` | Reproducir, pausar, adelantar y reiniciar con `VideoSynchronizedReplay` de Persona 1. |
| `POST /matches/{id}/simulation` | Ejecutar localmente las seis rutas del filtro y los agentes configurados. |
| `GET /matches/{id}/highlights` · `POST …/highlights/{clip_id}/review` | Consultar, confirmar o rechazar recortes propuestos. |

Las preferencias se envían como parámetros: `language` (`es`, `en`, `de`, `zh`, `hi`, `fr`, `pt`), `mode` (`casual`, `analyst`, `professional_analyst`, `player`), `level` (`simple`, `normal`, `advanced`), `favorite_team_id` y `favorite_player_id`. `professional_analyst` siempre usa el nivel avanzado.

**Frontend.** `apps/frontend` implementa el diseño de Figma de Persona 5 para The Prime Moment en React y JavaScript, como fija la [decisión técnica 3](../07-decisiones-tomadas.md), conectado a la API real.

| Pantalla | Ruta | Qué muestra |
|---|---|---|
| Inicio | `#/` | Presentación del producto, modos y ejemplo con cifras reales del partido de aceptación. |
| Configuración | `#/onboarding` | Idioma, club, jugador y modo, con los equipos y jugadores que entrega la API. |
| Descubrir | `#/discover` | Partido en vivo cuando exista, partido más reciente, próximo partido y acceso a su previa. |
| Previa | `#/match/{id}/preview` | Duelo visual, formaciones, tácticas ofensivas por equipo e informe previo extensible y buscable. |
| Partidos | `#/matches` | Búsqueda, filtros en vivo, próximos y resúmenes, y filtro por jugador. |
| Centro del partido | `#/match/{id}` | Sesión persistente entre Partido, Resumen, Estadísticas y Vista táctica; seguimiento interpolado de once jugadores por equipo y balón, con foco individual; comentarios activables, pantalla completa, agente lateral con flecha; selector y laboratorio de momentos; estadísticas por tiempo; repetición y simulación táctica por equipo. |
| Momento | `#/match/{id}/moment/{momento}` | Autor, situación, equipo y tiempo; explicación breve, cifras, jugadores, eventos de origen y reporte de errores. |
| Resumen | `#/recap/{id}` | Marcador final, resumen pendiente o aprobado y los tres momentos principales. |
| Mi experiencia | `#/profile` | Preferencias, historial local de partidos y resúmenes, contenido del jugador seguido y comentarios para analistas. |
| Comunidad | `#/editorial` | Lista buscable de partidos con resumen, marcador, likes, dislikes y acceso al detalle. |
| Detalle comunitario | `#/editorial/{partido}/{resumen}` | Equipo destacado, resultado, resumen, tácticas, agente de preguntas, votación, sugerencias y comentarios en vivo. |

Estructura del código:

```
apps/frontend/src/
  api/client.js          Llamadas HTTP a /api/v1
  app/                   Preferencias (contexto) y enrutador por hash
  i18n/strings.js        Textos en español e inglés
  data/branding.js       Escudos, colores y fotos del diseño asignados a los equipos de la API
  hooks/                 Catálogo, reloj de reproducción y canal en directo (SSE)
  lib/overlays.js        Qué mensaje se ve en cada instante (sin estado)
  components/ui|layout|match
  screens/               Una pantalla por archivo
  styles/                Un CSS por sección del diseño más experience.css
```

Decisiones de la implementación:

- **Sin TypeScript ni Tailwind.** El diseño exportado de Figma Make venía en TypeScript con Tailwind importado pero sin usar sus utilidades. Se pasó a JavaScript y CSS normal para seguir la decisión del equipo y no sumar dependencias.
- **Datos siempre de la API.** El diseño traía partidos y clubes ficticios fijos en el código (algunos con nombres de clubes reales). Ahora los partidos, equipos, jugadores, marcadores, estadísticas y textos vienen del backend. Del diseño solo quedan escudos, fotos e ilustraciones, asignados a los equipos sintéticos en `data/branding.js`.
- **Sin cifras inventadas.** Donde el diseño mostraba valores de ejemplo (probabilidad de gol, toques, posesión) se usan cifras calculadas o se omiten.
- **Imágenes optimizadas.** Se convirtieron a WebP con el tamaño en que se muestran: de 21 MB a 1,6 MB. Se descartaron las que no se usan.
- **Navegación con la URL.** Cada pantalla tiene su dirección y el botón Atrás del navegador funciona.
- **Pantalla nueva de revisión editorial.** El diseño no la tenía y el reto la pide (RF-38, RF-39).

## **Revisión comunitaria de los resúmenes**

La pantalla ya no separa Revisar resumen y Comunidad. Muestra siempre los partidos como tarjetas grandes con búsqueda y filtros. Cada tarjeta combina los equipos en una composición diagonal, resalta al ganador, presenta el marcador, un resumen breve y los conteos de likes y dislikes.

Al abrir una tarjeta se muestra el resumen completo, las tácticas sintéticas del partido y un agente que responde preguntas con los eventos disponibles. La misma vista permite aprobar con like, marcar que necesita mejoras con dislike, explicar qué debería cambiar y conversar sobre el resumen.

El voto de la comunidad **orienta** al editor, pero no aprueba ni publica el resumen: la publicación sigue exigiendo la revisión editorial (RF-38).

**Tiempo real.** Cada resumen es un tema de un bus de mensajes. La API publica en ese tema cada voto y cada mensaje, y los navegadores suscritos los reciben por Server-Sent Events, con un latido cada 15 s para mantener viva la conexión. El bus por defecto usa una cola en memoria (`asyncio.Queue`) por suscriptor, suficiente porque la API corre en una sola réplica (`maxReplicas: 1` en `infra/azure`). La interfaz `MessageBus` (`application/community.py`) permite reemplazarlo por MQTT o Azure Service Bus si se escalan réplicas.

**Moderación** (`application/moderation.py`). Antes de publicar se rechazan groserías e insultos en español e inglés, enlaces y spam (`422` con el motivo). El texto se normaliza para resistir trucos (`put4`, `p.u.t.a`, `puuuta`, tildes) y se comparan palabras completas para no bloquear palabras sanas como «computadora». Los nombres también se moderan. Límite: un mensaje cada 2 segundos por persona (`429` con `Retry-After`).

**Identidad.** No hay inicio de sesión: cada navegador recibe un identificador aleatorio (un voto por persona, que puede cambiarse) y la persona escribe el nombre con el que la verán.

| Ruta | Para qué sirve |
|---|---|
| `GET /matches/{id}/community` | Votos por resumen de la cola editorial. |
| `GET /matches/{id}/community/{draft_id}?client_id=` | Votos, mi voto, sugerencias y chat. |
| `POST /matches/{id}/community/{draft_id}/votes` | Votar `approve` o `reject`. |
| `POST /matches/{id}/community/{draft_id}/messages` | Enviar `suggestion` o `chat`; pasa por la moderación. |
| `GET /matches/{id}/community/{draft_id}/stream` | Canal SSE con `ready`, `vote` y `message`. |

Pruebas: `tests/test_moderation.py`, `tests/test_community.py` y el grupo «Comunidad» de Postman.

Con `SUPABASE_ENABLED=true`, los resúmenes, decisiones, votos y mensajes se guardan mediante la Data API. Con Supabase deshabilitado o temporalmente inaccesible, el flujo continúa en memoria. El identificador anónimo se puede reiniciar borrando los datos del navegador, así que el conteo sigue siendo orientativo; la lista de palabras bloqueadas es fija y puede ampliarse en `BLOCKED_ROOTS`.

## **Decisiones de Persona 4**

**1. El vídeo manda.** El tiempo del reproductor decide qué se ve. Cada mensaje lleva `video_time_ms` tomado de sus eventos de origen (`video_time_basis = source_event_timestamp`); no se presenta como detección automática.

**2. Transporte: Server-Sent Events.** Es unidireccional, funciona sobre HTTP y el navegador reconecta solo. Al pausar se cierra el canal; al reanudar o adelantar se abre otro desde la nueva posición y el historial se reconstruye con `GET /overlays`. **Esta decisión debe confirmarla el equipo**; cambiar a WebSocket solo afecta a `match_router.py` y `useLiveChannel.js`.

**3. Una sola zona de pantalla (RNF-05).** `schedule_overlays` decide el reemplazo de forma determinista: un mensaje de prioridad igual o mayor reemplaza al visible; uno menor queda en el historial como `suppressed`. Como depende solo de los mensajes, adelantar o retroceder muestra siempre lo mismo.

**4. Campos añadidos a `OverlayMessage v1`.** Además de los campos del contrato de trabajo: `candidate_id`, `period`, `clock_ms`, `kind`, `mode`, `level`, `explanation`, `display_until_ms`, `replaces_message_id`, `suppressed` y `corrected`. Son compatibles hacia atrás; **propongo incorporarlos al contrato compartido** ([ejemplos](ejemplos/)).

**5. Selección por modo.** Casual muestra momentos con prioridad ≥ 50; analista muestra todos; el modo jugador muestra los momentos donde interviene el jugador y avisa «Sin novedades» cada 10 s sin intervención. Los goles se muestran siempre, también los del rival (RF-24).

**6. Puertos hacia Persona 2 y Persona 3.** La API solo depende de `AnalyticsPort` y `NarrativePort` (`application/ports.py`). La analítica sigue usando el adaptador provisional. Narrativa puede usar `provisional`, `fixture` o el adaptador de Persona 3 con Azure mediante `NARRATIVE_PROVIDER`. Ningún proveedor añade xG, xT o VAEP por sí mismo.

## **Cómo integrar los módulos reales**

1. Persona 2 implementa `AnalyticsPort` (`snapshot` y `candidates`) devolviendo `MatchSnapshot v1` e `InsightCandidate v1`.
2. Persona 3 ya se conecta mediante `Persona3NarrativeAdapter`. `player_quiet` y la verificación posterior a reportes aún usan el respaldo determinista.
3. `adapters/http/registry.py` selecciona el proveedor por configuración. Las rutas y el frontend no cambian.
4. Las pruebas de `tests/test_match_experience_api.py` deben seguir pasando; las que dependen de textos concretos de las plantillas se ajustan a los textos reales.

## **Cobertura de requisitos**

| Requisito | Cómo se cumple | Prueba |
|---|---|---|
| RF-19 | `OverlayMessage v1` con todos los campos legibles por máquina | `test_overlay_is_machine_readable`, `test_overlay_contract_examples` |
| RF-20, RF-37 | Mensajes por tiempo de vídeo; adelantar no muestra mensajes de otro momento | `test_seek_rebuilds_same_screen_without_future_messages`, `test_events_and_state_never_reveal_future`, prueba manual en navegador |
| RF-22, RF-27 | Mismo momento en español e inglés con los mismos hechos | `test_language_changes_text_not_facts` |
| RF-23 | Casual y analista con distinto contenido | `test_casual_and_analyst_differ_but_share_sources` |
| RF-24 | Club favorito sube prioridad sin ocultar el gol rival | `test_favorite_team_never_hides_rival_goal` |
| RF-25 | Jugador favorito solo cambia lo que le afecta | `test_favorite_player_raises_priority_only_when_involved` |
| RF-26 | Modo jugador con avisos sin novedades | `test_player_mode_reports_quiet_stretches` |
| RF-28 | «Ver por qué importa» con eventos de origen | `test_sources_explain_a_message` |
| RF-34 | Preguntas por equipo, jugador y tramo; reconoce lo que no sabe | `test_questions_use_available_events`, `test_question_without_data_is_acknowledged` |
| RF-35 | Resumen con enfoque sin cambiar cifras | `test_summary_focus_keeps_facts` |
| RF-36 | Niveles simple, normal y avanzado | `test_levels_change_detail_not_facts` |
| RF-38 | El resumen no se publica sin aprobación | `test_final_summary_is_held_until_approved`, `test_rejected_summary_is_not_published` |
| RF-39 | Reporte válido corrige; reporte inválido se confirma | `test_valid_report_withdraws_and_corrects`, `test_invalid_report_is_confirmed` |
| RNF-05 | Nunca dos mensajes a la vez | `test_only_one_message_competes_for_screen`, `test_scheduler_replaces_lower_priority_and_keeps_higher` |
| Retraso | `emitted_at_ms` y `pipeline_ms` en cada mensaje; panel de retraso | `test_live_stream_sends_new_messages_with_timing` |

## **Comandos y resultados**

Desde la raíz del repositorio:

```bash
uv run --project apps/backend pytest apps/backend/tests
npm run lint:frontend
npm run build:frontend
```

Resultado del 18 de octubre de 2026 en el árbol de trabajo: 323 pruebas superadas, compilación correcta y tres advertencias previas del linter por cargar datos dentro de efectos. La simulación integrada con el proveedor fixture devolvió seis rutas, siete mensajes y un recorte pendiente. La revisión visual en navegador de las pantallas nuevas sigue pendiente.

**Seguimiento 11 contra 11, 24 de octubre de 2026.** El partido en vivo ahora consume ventanas de `TrackingFrame v1` a 5 cuadros por segundo y mueve 22 jugadores y el balón mediante interpolación sincronizada con el reloj. La forma base es 4-3-3; al defender se asigna un presionante y los jugadores de líneas retrasadas ajustan coberturas o marcas por carril. La API limita cada ventana a 30 segundos y declara `synthetic_mock`. Se superaron 16 pruebas específicas y las 340 pruebas del backend, además del lint y la compilación de producción del frontend. La vista de escritorio a 1440 px se comprobó en Chrome local; queda pendiente la revisión manual móvil y durante una reproducción prolongada.

**Situaciones coordinadas, 24 de octubre de 2026.** `synthetic-live-001` usa un escenario distinto del partido analítico. Los pases declaran receptor y propósito; el seguimiento prepara la recepción y mantiene unido al balón con la jugada. Se añadieron recuperación y contraataque, cambios largos, pases al espacio, falta, tarjeta amarilla, paro por lesión y reanudación. La cancha muestra la situación actual y las pausas también producen una narración con sus eventos de origen. Esta versión es un guion reproducible con validaciones tácticas; todavía no selecciona el pase en cada cuadro entre todas las opciones disponibles.

**Actualización del centro del partido, 19 de octubre de 2026.** Se conectó el inicio de la simulación al reloj local y se mantuvo la sesión al cambiar de pestaña. Se añadieron controles globales de pausa, continuación y reinicio; cambio inmediato entre Aficionado y Analista; todos los jugadores en el campo con foco individual; selector de un momento; laboratorio contrafactual local; estadísticas con balance visual; tácticas por equipo; explicaciones con vista previa; comentarios sincronizados y locutor contextual. `npm run lint:frontend` terminó sin errores y conservó las tres advertencias anteriores. `npm run build:frontend` terminó correctamente con Vite 8.3.3. La revisión visual manual en navegador queda pendiente.

El laboratorio contrafactual actual es una estimación determinista de interfaz y está marcado como tal. No se considera implementación de RF-44 mediante IA: falta definir y conectar el contrato del agente que reciba posiciones de jugadores, balón y arquero y devuelva supuesto, método, evidencia y límites.

**Corrección del flujo en vivo y persistencia, 19 de octubre de 2026.** Encontramos que el proveedor Azure devolvía `401` y el adaptador retenía todas las narraciones. Esto dejaba vacías las vistas Momentos y Explicaciones. El adaptador ahora usa una narración local verificada cuando el proveedor no está disponible y abre un circuito para no repetir llamadas fallidas durante la misma sesión. El asistente recibe métricas y fuentes del tiempo consultado, reconoce nombres de equipos y jugadores y responde preguntas abiertas con la última acción registrada.

El campo interpola cada pase y remate en un máximo de 900 ms. La secuencia final del partido corto conecta el pase de N. Alba con el remate y gol de M. Luz. El balón se representa en blanco y ya no usa un movimiento decorativo separado de los eventos.

La persistencia opcional usa Supabase desde el backend. La migración `supabase/migrations/202610190001_match_intelligence.sql` crea `matches`, `match_events`, `moments` y `assistant_messages` con RLS activo. `SUPABASE_ENABLED=false` mantiene la demo en memoria. El `.env` ignorado contiene la URL y las claves. Para aplicar la migración remota falta autenticar la CLI, corregir las claves que actualmente responden `401` y completar `SUPABASE_DB_PASSWORD`; el identificador del proyecto se obtiene automáticamente de `SUPABASE_URL`.

La verificación final ejecutó 330 pruebas del backend correctamente, además de `npm run lint:frontend` sin errores y `npm run build:frontend` correctamente. La API local devolvió siete momentos para el partido corto, incluido `Gol de M. Luz`, y el asistente respondió una pregunta abierta con las fuentes `evt-006`, `evt-007`, `evt-009` y `evt-010`. La conexión remota de Supabase respondió `401`; la migración no se aplicó porque la CLI no tiene sesión y la clave actual no autentica contra el proyecto indicado.

**Prueba en navegador de la interfaz con el diseño** (14 de octubre, escritorio y 375 px): configuración inicial con club y jugador de la API; centro del partido de dos tiempos a 8× con mensajes, marcador por período y canal en directo; pregunta «¿Cuántos tiros tiene M. Luz?» respondida con `sc-009` y `sc-036`; estadísticas y momentos; detalle de un momento; resumen pendiente y aprobado desde Revisión; error controlado reportado, retirado y corregido; interfaz en inglés; las nueve pantallas sin desbordamiento horizontal a 375 px.

**Prueba en navegador de la primera interfaz** (9 de octubre, Chrome, escritorio y 375 px): reproducción a 2×, mensajes de robo, recuperación y gol en su momento; marcador 0-0 antes del gol y 1-0 después; saltos a 5, 20, 24, 33,5 y 35 s sin mensajes de otro momento; cambio a inglés y analista; pregunta «How many shots did M. Luz take?» con fuente `evt-010`; resumen bloqueado con 409 y publicado tras aprobar; error controlado «A. Vega» reportado, retirado y corregido a «M. Luz». El retraso medido en local fue de unos 9 ms de transporte, menos de 1 ms de cálculo y unos 850 ms de margen antes de mostrar.

**Actualización de comunidad y revisión, 26 de octubre de 2026.** Se reemplazaron las pestañas Revisar resumen y Comunidad por una lista única con los tres partidos sintéticos, búsqueda, filtros, tarjetas diagonales, marcador, resumen breve y conteos de likes y dislikes. El detalle reúne equipo destacado, resumen completo, tácticas, agente, votación, sugerencias y conversación. Los controles de tema y sesión volvieron al sidebar, y la línea de tiempo quedó dentro de Partido debajo de los comentarios.

Mi experiencia incluye al final una acción confirmada para borrar la configuración local. Reinicia idioma, tema, modo, nivel, club, jugador, comentarios en vivo, estado del sidebar y apertura del agente, marca el onboarding como pendiente y vuelve a la selección inicial. Conserva el historial de partidos y resúmenes, la identidad de comunidad, los votos y los comentarios.

Las esperas del frontend muestran un indicador de carga visible y accesible. El patrón cubre la carga inicial, catálogo, previa, resúmenes, comunidad, conexión en vivo, agente, reportes, analítica táctica, seguimiento y procesamiento de visión. Los botones asíncronos se bloquean mientras esperan su respuesta y muestran el progreso dentro del mismo control.

Los controles de reproducción y la línea de tiempo de momentos se muestran encima de la cancha sintética como si fuera un video. Permanecen ocultos para no tapar la jugada y aparecen al pasar el cursor o enfocar un control con el teclado. En una pantalla táctil permanecen visibles. En escritorio, los comentarios en vivo ocupan una columna a la derecha y los momentos tienen un espacio propio debajo. En pantallas pequeñas pasan debajo de la cancha. El reloj conserva su estado al cambiar de vista.

La migración `202610260001_summary_community.sql` añade resúmenes, votos y mensajes. Los adaptadores recuperan y guardan esos datos cuando Supabase está activo y mantienen respaldo en memoria cuando falla. Se superaron 53 pruebas específicas de experiencia, comunidad y persistencia; la suite disponible sin los artefactos reales de visión terminó con 412 pruebas superadas y 7 omitidas. El linter y la compilación del frontend terminaron correctamente con las dos advertencias anteriores. La comprobación HTTP local cargó tres resúmenes y tres salas de comunidad. La revisión visual automatizada no pudo completarse porque Chrome y Edge no generaron la captura en este entorno.

La base remota no se migró: `SUPABASE_ENABLED` sigue en `false`, las claves actuales responden `401` y falta `SUPABASE_DB_PASSWORD`. La migración queda lista para aplicarse con `scripts/setup-supabase.ps1`; `SUPABASE_PROJECT_REF` ya no es obligatorio porque el script lo deriva de la URL.

## **Limitaciones y pendientes**

- **Sin vídeo real.** Se usa la línea de tiempo sintética. El reproductor ya acepta una URL de vídeo; falta decidir el vídeo permitido (decisión pendiente 4).
- **Analítica provisional.** Narrativa ya admite Persona 3, pero algunas operaciones conservan respaldo determinista. Ver la decisión 6.
- **Recortes sin archivo físico.** La versión local propone tiempos y permite revisión; todavía no corta ni sube vídeo a Blob Storage.
- **Partidos de la demo.** Hay tres: el corto finalizado de aceptación, el próximo partido analítico de dos tiempos y otro escenario analítico marcado en vivo para revisar el centro del partido con once jugadores por equipo. Los tres enfrentan a Aurora FC y Río Unido.
- **Persistencia opcional.** Con Supabase activo se recuperan resúmenes, decisiones, votos y mensajes. Los reportes de error todavía se conservan solo en memoria. Sin Supabase, toda la participación comunitaria vuelve al respaldo local en memoria.
- **Diseño.** Implementado desde el Figma de Persona 5. Los escudos de Aurora FC y Río Unido son los de «Aurora Athletic» y «Riverside United» del diseño; si Persona 5 prepara escudos propios, solo cambia `data/branding.js`.
- **Sin vídeo real.** La interfaz nueva usa el campo sintético; el reproductor de la primera versión aceptaba una URL de vídeo y puede recuperarse cuando el equipo elija el vídeo.
- **Voz.** No implementada; depende de que el equipo la incluya en el alcance.
- **Mensajes de verificación** salen en español aunque la interfaz esté en inglés.
- **Meta de latencia.** Se mide, pero el equipo aún no acordó un valor objetivo (decisión pendiente 6).
