# Cambios en “Por qué importa” y continuidad del partido

Fecha: 27 de octubre de 2026.

## Resultado

The Prime Moment ahora entrega un llamado diferente según la acción de cada momento. El botón dejó de mostrar solamente “Por qué importa” y presenta una frase breve que invita a abrir el análisis, por ejemplo:

- “¿Cómo nació el gol? Revisa la jugada completa”.
- “¿Un pase que rompió líneas? Mira cuánto avanzó”.
- “Tremenda falta de tarjeta. Revisa los amonestados”.

También se conserva el trabajo realizado dentro de cada partido. Al salir y volver se recuperan el minuto, la velocidad, la pestaña, la jugada, el jugador, el tipo de resumen, el jugador del resumen personalizado, el estado iniciado de la simulación y la posición vertical. La reproducción vuelve pausada para no avanzar fuera de la vista de la persona.

## Frases por jugada

Se agregaron 50 frases en español, divididas entre:

- goles;
- remates;
- pases progresivos;
- faltas;
- tarjetas amarillas;
- tarjetas rojas;
- recuperaciones;
- pérdidas;
- presión;
- momentos generales.

La misma jugada conserva la misma frase. Cuando la preferencia está en otro idioma y todavía no existen variantes de esa frase en la base, se usa una invitación general traducida en lugar de mostrar texto en español.

La migración `202610270002_action_callouts.sql` crea y llena `action_callouts`. El backend intenta leer esta tabla al abrir la sesión del partido. Si Supabase está deshabilitado o no responde, usa el catálogo local equivalente y el partido continúa funcionando.

## Archivos principales

- `apps/backend/src/match_intelligence/application/callouts.py`: catálogo local, equivalencias de acciones y selección estable.
- `apps/backend/src/match_intelligence/application/match_session.py`: agrega la frase al contrato de cada momento.
- `apps/backend/src/match_intelligence/adapters/storage/supabase_match.py`: lectura segura desde Supabase.
- `supabase/migrations/202610270002_action_callouts.sql`: tabla y 50 registros iniciales.
- `apps/frontend/src/components/match/OverlayCard.jsx`: llamado visual dentro del partido.
- `apps/frontend/src/components/match/LiveExperiencePanels.jsx`: frase visible en la lista de jugadas importantes.
- `apps/frontend/src/lib/matchSession.js`: estado local separado por partido.
- `apps/frontend/src/screens/MatchCenter.jsx`: restauración de la experiencia.
- `apps/frontend/src/components/match/LiveSummarySelector.jsx`: restauración del resumen elegido.

## Validación ejecutada

| Comando | Resultado |
|---|---|
| `uv run pytest tests/test_action_callouts.py tests/test_supabase_match_repository.py tests/test_match_experience_api.py -q` | 50 pruebas superadas. |
| `npm run lint:frontend` | Correcto. Conserva dos advertencias anteriores en `useCatalog.js` y `MomentDetail.jsx`. |
| `npm run build:frontend` | Compilación correcta con Vite 8.3.3. |
| Conteo de registros de la migración | 50 frases. |
| Prueba directa de `matchSession.js` con Node | Conservó y combinó pestaña, jugador y tipo de resumen. |
| `git diff --check` | Sin errores de espacios. Solo avisos de conversión LF/CRLF. |

La suite completa del backend terminó con 484 pruebas superadas, 7 omitidas y 11 fallidas. Esos fallos no pertenecen a este cambio: faltan tres artefactos locales de Roboflow, SoccerNet y fusión, varias rutas de integración dependen de esos archivos y una prueba anterior rechaza el nombre `SUPABASE_DB_PASSWORD` que ya existe en `.env.example`.

## Pendiente externo

La migración quedó preparada, pero no se aplicó a la base remota. La configuración actual de Supabase ya había respondido `401` y no existe una contraseña de base válida en el entorno. No se crearon contenedores, no se modificó la base remota y no se regeneró la colección de Postman.
