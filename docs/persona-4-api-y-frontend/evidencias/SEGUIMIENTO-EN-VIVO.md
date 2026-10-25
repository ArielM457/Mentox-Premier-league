# **Seguimiento 11 contra 11 en el partido en vivo**

## **Resultado**

El centro del partido en vivo usa 22 jugadores identificados, el balón y un árbitro. Las posiciones llegan desde el backend a 5 cuadros por segundo y React interpola entre ellas con el reloj del partido. La fuente visible es `synthetic_mock`; no se presenta como medición de un vídeo real.

## **Referencia estudiada**

Se revisó MatchPulse en el commit `7abb3619200a01a96d2723271230f0c0ea1f88b7` del 24 de octubre de 2026. Se tomaron como referencia sus ideas de simulación 11 contra 11, zonas por función, presión, marcas, límites cinemáticos e interpolación visual. No se copió su código: el repositorio no declara una licencia y nuestra solución conserva los contratos y la arquitectura hexagonal de este proyecto.

## **Qué se adaptó**

- El escenario analítico pasó de siete a once jugadores por equipo.
- Cada equipo parte de una estructura 4-3-3: portero, cuatro defensores, tres mediocampistas y tres atacantes.
- El jugador de la acción se aproxima al lugar del evento. Los demás acompañan el balón desde su zona y mantienen la forma colectiva.
- Sin posesión, el jugador de campo más próximo presiona. Los defensores y mediocampistas restantes protegen su portería y ajustan una marca por carril sin abandonar por completo su zona.
- La velocidad máxima es 8,5 m/s para el actor, 5,5 m/s para los demás jugadores y 5 m/s para porteros y árbitro. La aceleración máxima es 3,5 m/s².
- El backend genera el seguimiento una sola vez por sesión y expone ventanas de hasta 30 segundos. Incluye los cuadros limítrofes necesarios para evitar saltos al cambiar de ventana.
- La cancha usa `requestAnimationFrame` para interpolar los cuadros conforme a reproducción, pausa, velocidad y búsqueda. Las canchas pequeñas de análisis conservan su componente anterior.

## **Archivos principales**

- `apps/backend/src/match_intelligence/adapters/sources/analytics_scenarios.py`
- `apps/backend/src/match_intelligence/adapters/sources/tracking_mock.py`
- `apps/backend/src/match_intelligence/application/match_session.py`
- `apps/backend/src/match_intelligence/adapters/http/match_router.py`
- `apps/frontend/src/hooks/useTrackingFrames.js`
- `apps/frontend/src/components/match/LiveTrackingPitch.jsx`
- `apps/frontend/src/screens/MatchCenter.jsx`
- `apps/backend/tests/test_live_tracking_api.py`

## **Criterios cubiertos**

- Once jugadores por equipo en el partido en vivo.
- Los 22 jugadores aparecen identificados en cada cuadro.
- Todos se desplazan durante una ventana continua.
- No hay saltos superiores a 8,6 m/s en la salida redondeada.
- El balón aparece como máximo una vez por cuadro y puede quedar ausente cuando la trayectoria requerida no es físicamente razonable.
- La API rechaza rangos invertidos o superiores a 30 segundos.
- La interfaz no descarga el partido completo: solicita una ventana de 28 segundos al cambiar de bloque temporal.

## **Verificación del 24 de octubre de 2026**

```powershell
uv run --project apps/backend pytest apps/backend/tests/test_live_tracking_api.py apps/backend/tests/test_analytics_tracking.py -q
npm run lint
npm run build
```

Resultados: 16 pruebas específicas y 340 pruebas de la suite completa superadas; lint sin errores nuevos; compilación de producción correcta con Vite 8.3.3. Como la unidad `C:` no tenía espacio libre, la suite completa se ejecutó con `CREWAI_STORAGE_DIR=F:\WinTemp\premier-league-crewai-test` para que CrewAI pudiera crear su SQLite temporal.

Se abrió `#/match/synthetic-live-001` con el backend local y Vite, y se capturó la vista de escritorio a 1440 px. La cancha mostró los 22 marcadores, el balón, los números de camiseta y la etiqueta de fuente sintética sin solapamientos críticos. La captura móvil de Chrome sin automatización de métricas de dispositivo no es evidencia suficiente; esa comprobación manual sigue pendiente.

## **Reorganización del Centro del Partido**

La navegación visible quedó ordenada como Partido, Resumen, Estadísticas y Vista táctica. Resumen combina el laboratorio del momento seleccionado con las explicaciones importantes. Los comentarios dejaron de ser una pestaña y ahora se muestran debajo del campo mediante una palanca dentro de Partido.

El agente se monta únicamente en Partido como panel lateral derecho. Una flecha sin texto lo abre y cierra; su nombre continúa disponible para lectores de pantalla. La columna del partido incorpora una acción de pantalla completa y conserva allí el campo, los comentarios activados y la reproducción.

Archivos modificados para esta reorganización:

- `apps/frontend/src/screens/MatchCenter.jsx`
- `apps/frontend/src/components/match/LiveExperiencePanels.jsx`
- `apps/frontend/src/components/ui/Icon.jsx`
- `apps/frontend/src/i18n/strings.js`
- `apps/frontend/src/styles/match.css`
- `apps/frontend/src/styles/responsive.css`

Validación reproducible:

```powershell
npm run lint --workspace apps/frontend
npm run build --workspace apps/frontend
```

Resultado: lint sin errores y con tres advertencias anteriores fuera de los archivos modificados; compilación de producción correcta con Vite 8.3.3. Queda pendiente la comprobación manual de la entrada y salida de pantalla completa en un navegador interactivo.

## **Límites pendientes**

- Las posiciones son sintéticas y derivadas de eventos; todavía no son detecciones de un vídeo.
- El contrato de jugador no incluye una función explícita. En este escenario la función se obtiene de la plaza fija en la formación y del número de camiseta. Conviene añadir `position` o una alineación versionada antes de admitir planteles arbitrarios.
- Falta una revisión visual manual en navegador de escritorio y móvil para comprobar tamaño, solapamiento y selección de los 22 marcadores.
- Un proveedor de vídeo debe resolver homografía, identidad y pérdida temporal de pistas y producir el mismo `TrackingFrame v1` con `source=video_model`.
