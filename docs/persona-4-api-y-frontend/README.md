# **Persona 4: API y experiencia funcional**

Este documento registra lo implementado por Persona 4, cómo se verificó y qué falta. El plan original está en [el plan de Persona 4](../plan-de-desarrollo/persona-4-api-y-frontend.md).

- **Estado:** verificado localmente con datos sintéticos y adaptadores provisionales.
- **Última verificación:** 9 de octubre de 2026.
- **Rama:** `persona-4/api-frontend`.

## **Qué existe ahora**

**Backend.** Rutas nuevas bajo `/api/v1/matches`, documentadas en Swagger (`http://localhost:8000/docs`, grupo «Partido y experiencia»).

| Ruta | Para qué sirve |
|---|---|
| `GET /matches` · `POST /matches` | Listar y cargar un partido sintético (generador de Persona 1). `inject_error_in` provoca un error controlado para la demo. |
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

**Frontend.** `apps/frontend` reemplaza el formulario inicial por la experiencia completa:

- Reproductor con «vídeo sintético» (el campo dibuja los eventos ya ocurridos) o un vídeo real si se pega su URL. Controles de reproducir, pausar, ±5 s, reiniciar, barra de tiempo y velocidad. Teclado: espacio o `k` para pausar y flechas para moverse.
- Marcador, reloj y una sola zona de mensajes sobre el vídeo, con barra de duración.
- «Ver por qué importa»: explicación, eventos de origen, preferencias aplicadas y formulario de reporte.
- Preferencias de idioma, modo, nivel, club y jugador. La interfaz también cambia de idioma.
- Historial de momentos, estado del partido, preguntas, resumen final, revisión editorial, reportes y retraso medido.
- Herramientas de demo: recargar el partido con un error controlado en el gol.

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

Resultado del 9 de octubre de 2026: 166 pruebas superadas (134 previas y 32 nuevas), compilación del frontend correcta y una advertencia del linter sobre la carga inicial de datos en `App.jsx`, que es el patrón esperado.

**Prueba en navegador** (Chrome, escritorio y 375 px de ancho): reproducción a 2×, mensajes de robo, recuperación y gol en su momento; marcador 0-0 antes del gol y 1-0 después; saltos a 5, 20, 24, 33,5 y 35 s sin mensajes de otro momento; cambio a inglés y analista; pregunta «How many shots did M. Luz take?» con fuente `evt-010`; resumen bloqueado con 409 y publicado tras aprobar; error controlado «A. Vega» reportado, retirado y corregido a «M. Luz». El retraso medido en local fue de unos 9 ms de transporte, menos de 1 ms de cálculo y unos 850 ms de margen antes de mostrar.

## **Limitaciones y pendientes**

- **Sin vídeo real.** Se usa la línea de tiempo sintética. El reproductor ya acepta una URL de vídeo; falta decidir el vídeo permitido (decisión pendiente 4).
- **Analítica y narración provisionales.** Ver la decisión 6.
- **Partido corto.** El partido de aceptación dura 42 s; sirve para probar, pero la demo se verá mejor con un partido más largo de Persona 1.
- **Estado en memoria.** Revisiones y reportes se pierden al reiniciar el backend. Para la demo alcanza; para producción haría falta guardarlos.
- **Diseño.** La interfaz usa un estilo propio a la espera de los diseños de Persona 5.
- **Voz.** No implementada; depende de que el equipo la incluya en el alcance.
- **Mensajes de verificación** salen en español aunque la interfaz esté en inglés.
- **Meta de latencia.** Se mide, pero el equipo aún no acordó un valor objetivo (decisión pendiente 6).
