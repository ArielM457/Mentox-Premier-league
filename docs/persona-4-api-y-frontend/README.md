# **Persona 4: API y experiencia funcional**

Este documento registra lo implementado por Persona 4, cómo se verificó y qué falta. El plan original está en [el plan de Persona 4](../plan-de-desarrollo/persona-4-api-y-frontend.md).

- **Estado:** verificado localmente con datos sintéticos y adaptadores provisionales.
- **Última verificación:** 18 de octubre de 2026.
- **Ramas:** `feat/persona-4-api-frontend` (API) y `feat/persona-4-figma-ui` (interfaz con el diseño de Persona 5).

## **Qué existe ahora**

**Backend.** Rutas nuevas bajo `/api/v1/matches`, documentadas en Swagger (`http://localhost:8000/docs`, grupo «Partido y experiencia»).

| Ruta | Para qué sirve |
|---|---|
| `GET /matches` · `POST /matches` | Listar y cargar un partido sintético. `scenario`: `acceptance` (partido corto de Persona 1) o `analytics` (partido de dos tiempos de Persona 2). `inject_error_in` provoca un error controlado para la demo. |
| `GET /matches/{id}` | Metadatos, duración y fuente de vídeo. |
| `GET /matches/{id}/events?until_video_ms=` | Eventos ya ocurridos; nunca futuros. |
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

Las preferencias se envían como parámetros: `language` (`es`, `en`), `mode` (`casual`, `analyst`, `player`), `level` (`simple`, `normal`, `advanced`), `favorite_team_id` y `favorite_player_id`.

**Frontend.** `apps/frontend` implementa el diseño de Figma de Persona 5 («Inside the Game») en React y JavaScript, como fija la [decisión técnica 3](../07-decisiones-tomadas.md), conectado a la API real.

| Pantalla | Ruta | Qué muestra |
|---|---|---|
| Inicio | `#/` | Presentación del producto, modos y ejemplo con cifras reales del partido de aceptación. |
| Configuración | `#/onboarding` | Idioma, club, jugador y modo, con los equipos y jugadores que entrega la API. |
| Descubrir | `#/discover` | Partidos del club favorito, partidos y acciones del jugador favorito. |
| Partidos | `#/matches` | Búsqueda, filtros en vivo, próximos y resúmenes, y filtro por jugador. |
| Centro del partido | `#/match/{id}` | Reproducción sincronizada, campo con posiciones reales, mensaje en pantalla, línea de tiempo, estadísticas, vista táctica, retraso del canal y asistente de preguntas. |
| Momento | `#/match/{id}/moment/{momento}` | Explicación, cifras y jugadores de la jugada, sus eventos de origen y reporte de errores. |
| Resumen | `#/recap/{id}` | Marcador final, resumen pendiente o aprobado y los tres momentos principales. |
| Mi experiencia | `#/profile` | Idioma, club, jugador, modo y nivel de explicación. |
| Revisión | `#/editorial` | Solo analista. Aprobar o rechazar resúmenes, ver reportes y recargar un partido con un error controlado. |
| Inicio de sesión | `#/login` | Perfil aficionado o analista profesional. |

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

## **Inicio de sesión y consola del analista**

La aplicación tiene dos perfiles. Sin sesión solo se ven la portada y el inicio de sesión.

| Perfil | Usuario | Contraseña | Qué ve |
|---|---|---|---|
| Aficionado | `aficionado` | `aficionado-demo-2026` | Partidos, explicaciones, preguntas y resumen según sus preferencias. |
| Analista profesional | `analista` | `analista-demo-2026` | Todo lo anterior, la **Consola del analista** y la **Revisión** editorial. |

Son cuentas de demostración con datos sintéticos. Las contraseñas no se guardan: `apps/backend/demo-users.json` solo tiene la sal y el hash PBKDF2-SHA256. Para otro entorno, crea tu propio archivo y apunta `MATCH_DEMO_USERS_FILE` a él.

| Ruta | Para qué sirve |
|---|---|
| `POST /api/v1/auth/login` | Devuelve un token firmado (HMAC-SHA256, 8 horas), su vencimiento y el usuario con su rol. |
| `POST /api/v1/auth/logout` | Revoca el token actual en el servidor. |
| `GET /api/v1/auth/me` | Usuario de la sesión actual. |
| `GET /api/v1/matches/{id}/analyst/feed?until_video_ms=` | **Solo analista.** Eventos, estado, cada momento candidato con sus hechos y límites, la narración casual y analista de cada uno, en qué modos se mostró y el comentario en vivo completo (incluidos los mensajes en cola o reemplazados). Nunca devuelve lo que todavía no pasó en el vídeo. |
| `POST /api/v1/matches/{id}/editorial/{draft_id}/review` | Ahora **solo analista**: 401 sin sesión, 403 para aficionados. |

Medidas de seguridad de la demo:

- **Bloqueo temporal:** 5 intentos fallidos en 15 minutos bloquean esa cuenta 5 minutos. El login responde 401 con `attempts_left` y, al bloquear, 429 con `retry_after_s` y la cabecera `Retry-After`. Un login correcto reinicia el contador.
- **Cierre de sesión real:** `POST /api/v1/auth/logout` revoca el token en el servidor; deja de servir aunque no haya vencido.
- **Tokens con identificador** (`jti`), fecha de emisión y vencimiento (`expires_at` en la respuesta del login).
- Revocaciones e intentos se guardan en memoria: se pierden al reiniciar el backend.

En la interfaz: panel de marca y formulario, selector de perfil, mostrar u ocultar la contraseña, aviso de Bloq Mayús, «Mantener la sesión en este dispositivo» (`localStorage`; si no, `sessionStorage`), botón «Usar cuenta de demostración», intentos restantes y cuenta regresiva del bloqueo. La sesión se cierra sola al vencer y se valida con el servidor al abrir la aplicación; si fue revocada, el login lo explica. **Cada cuenta guarda sus propias preferencias**: el aficionado ve la configuración inicial solo la primera vez.

El token se envía como `Authorization: Bearer <token>`. El secreto se lee de `MATCH_AUTH_SECRET`; sin él se genera uno al arrancar y las sesiones duran mientras el backend siga encendido. 

**Consola del analista** (pestaña del centro del partido): se actualiza cada vez que el vídeo cruza un evento o se adelanta. Tiene tres secciones: comentarios en vivo con prioridad y ventana de pantalla, momentos detectados con hechos, límites de la evidencia y la narración de cada modo lado a lado, y la tabla de eventos del partido.

Pruebas: `tests/test_auth.py` (contraseñas, token alterado o vencido, cuentas documentadas) y `tests/test_analyst_console.py` (permisos, contenido y que no adelanta el futuro). La colección de Postman tiene el grupo «Sesión»: «POST Login analista» guarda `{{token}}` para las peticiones protegidas.

## **Decisiones de Persona 4**

**1. El vídeo manda.** El tiempo del reproductor decide qué se ve. Cada mensaje lleva `video_time_ms` tomado de sus eventos de origen (`video_time_basis = source_event_timestamp`); no se presenta como detección automática.

**2. Transporte: Server-Sent Events.** Es unidireccional, funciona sobre HTTP y el navegador reconecta solo. Al pausar se cierra el canal; al reanudar o adelantar se abre otro desde la nueva posición y el historial se reconstruye con `GET /overlays`. **Esta decisión debe confirmarla el equipo**; cambiar a WebSocket solo afecta a `match_router.py` y `useLiveChannel.js`.

**3. Una sola zona de pantalla (RNF-05).** `schedule_overlays` decide el reemplazo de forma determinista: un mensaje de prioridad igual o mayor reemplaza al visible; uno menor queda en el historial como `suppressed`. Como depende solo de los mensajes, adelantar o retroceder muestra siempre lo mismo.

**4. Campos añadidos a `OverlayMessage v1`.** Además de los campos del contrato de trabajo: `candidate_id`, `period`, `clock_ms`, `kind`, `mode`, `level`, `explanation`, `display_until_ms`, `replaces_message_id`, `suppressed` y `corrected`. Son compatibles hacia atrás; **propongo incorporarlos al contrato compartido** ([ejemplos](ejemplos/)).

**5. Selección por modo.** Casual muestra momentos con prioridad ≥ 50; analista muestra todos; el modo jugador muestra los momentos donde interviene el jugador y avisa «Sin novedades» cada 10 s sin intervención. Los goles se muestran siempre, también los del rival (RF-24).

**6. Puertos hacia Persona 2 y Persona 3.** La API solo depende de `AnalyticsPort` y `NarrativePort` (`application/ports.py`). Hoy los implementan `adapters/provisional/analytics.py` y `adapters/provisional/narrative.py`: conteos simples y plantillas, **sin xG, xT, VAEP ni modelos de lenguaje**. Están marcados como provisionales y no deben presentarse como el trabajo final de Persona 2 o 3.

## **Cómo integrar los módulos reales**

1. Persona 2 implementa `AnalyticsPort` (`snapshot` y `candidates`) devolviendo `MatchSnapshot v1` e `InsightCandidate v1`.
2. Persona 3 implementa `NarrativePort` (`live`, `player_quiet`, `answer`, `summary` y `verify`) devolviendo `NarrativeDraft v1`.
3. En `adapters/http/registry.py`, `_default_registry()` cambia las fábricas provisionales por las reales. Las rutas y el frontend no cambian.
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

Resultado del 14 de octubre de 2026 sobre `main` actualizado: 316 pruebas superadas (incluye Personas 1, 2 y 3 y la colección de Postman), compilación del frontend correcta y tres advertencias del linter por cargar datos dentro de efectos, que es el patrón esperado.

**Prueba en navegador de la interfaz con el diseño** (14 de octubre, escritorio y 375 px): configuración inicial con club y jugador de la API; centro del partido de dos tiempos a 8× con mensajes, marcador por período y canal en directo; pregunta «¿Cuántos tiros tiene M. Luz?» respondida con `sc-009` y `sc-036`; estadísticas y momentos; detalle de un momento; resumen pendiente y aprobado desde Revisión; error controlado reportado, retirado y corregido; interfaz en inglés; las nueve pantallas sin desbordamiento horizontal a 375 px.

**Prueba en navegador de la primera interfaz** (9 de octubre, Chrome, escritorio y 375 px): reproducción a 2×, mensajes de robo, recuperación y gol en su momento; marcador 0-0 antes del gol y 1-0 después; saltos a 5, 20, 24, 33,5 y 35 s sin mensajes de otro momento; cambio a inglés y analista; pregunta «How many shots did M. Luz take?» con fuente `evt-010`; resumen bloqueado con 409 y publicado tras aprobar; error controlado «A. Vega» reportado, retirado y corregido a «M. Luz». El retraso medido en local fue de unos 9 ms de transporte, menos de 1 ms de cálculo y unos 850 ms de margen antes de mostrar.

## **Limitaciones y pendientes**

- **Sin vídeo real.** Se usa la línea de tiempo sintética. El reproductor ya acepta una URL de vídeo; falta decidir el vídeo permitido (decisión pendiente 4).
- **Analítica y narración provisionales.** Ver la decisión 6.
- **Partidos de la demo.** Hay dos: el corto de aceptación (42 s) y el de dos tiempos de Persona 2 (11:30). Los dos enfrentan a Aurora FC y Río Unido.
- **Estado en memoria.** Revisiones y reportes se pierden al reiniciar el backend. Para la demo alcanza; para producción haría falta guardarlos.
- **Diseño.** Implementado desde el Figma de Persona 5. Los escudos de Aurora FC y Río Unido son los de «Aurora Athletic» y «Riverside United» del diseño; si Persona 5 prepara escudos propios, solo cambia `data/branding.js`.
- **Sin vídeo real.** La interfaz nueva usa el campo sintético; el reproductor de la primera versión aceptaba una URL de vídeo y puede recuperarse cuando el equipo elija el vídeo.
- **Voz.** No implementada; depende de que el equipo la incluya en el alcance.
- **Mensajes de verificación** salen en español aunque la interfaz esté en inglés.
- **Meta de latencia.** Se mide, pero el equipo aún no acordó un valor objetivo (decisión pendiente 6).
