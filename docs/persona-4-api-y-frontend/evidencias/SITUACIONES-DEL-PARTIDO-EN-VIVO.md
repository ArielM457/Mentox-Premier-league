# **Situaciones del partido en vivo**

## **Problema observado**

La primera versión movía a los 22 jugadores, pero las posiciones nacían después de un guion de eventos. El receptor no formaba parte del contrato y el movimiento podía parecer desconectado de la decisión del pase.

## **Referencia local revisada**

Revisamos la copia entregada en `F:\Proyectos\premier league ejemplo\matchpulse-main`.

Su parte más útil es la separación entre decisión táctica y movimiento físico:

- `app/tactics.py` puntúa espacio, progresión y riesgo de intercepción.
- `app/physics.py` mantiene poseedor, receptor, balón en vuelo y balón detenido en un solo estado.
- El receptor debe llegar al balón y un defensor puede interceptarlo.
- Los saques esperan a que los jugadores ocupen su estructura.
- Solo un jugador presiona y los demás reciben marcas o tareas de cobertura.

La copia no contiene un archivo de licencia. El usuario indicó que los autores entregaron el ZIP y se unirán al proyecto. Aun así, esta integración no copió sus archivos: adaptamos las ideas a nuestros contratos y escribimos un escenario propio. El README de la referencia también indica que todavía no implementa faltas, tarjetas, lesiones ni sustituciones.

## **Implementación iniciada**

Creamos un escenario exclusivo para `synthetic-live-001` con estas situaciones:

- salida desde el portero;
- pase que rompe una línea;
- cambio largo de orientación;
- apoyo interior y pase al espacio;
- recuperación por intercepción;
- gol después de recuperación;
- falta táctica y tarjeta amarilla;
- paro de trece segundos por lesión;
- reanudación con tiro libre;
- presión alta, entrada, cambio de posesión y contraataque.

Cada pase y reanudación identifica `receiver_player_id` y `situation`. El generador rechaza receptores iguales al pasador, cambios largos demasiado cortos, pases al espacio sin progresión y retrocesos grandes sin una razón táctica permitida.

El seguimiento mueve al receptor hacia el punto de llegada. Durante el paro por lesión el balón permanece fijo, el jugador afectado desacelera hasta quedar casi inmóvil y el resto camina como máximo a 1,2 m/s. El evento de reanudación devuelve el balón al juego.

La cancha muestra una etiqueta temporal para la situación actual. Faltas, tarjetas y lesiones también producen momentos narrados y conservan sus eventos relacionados.

Los comentarios visibles usan lenguaje para espectadores. Ya no incluyen claves internas como `shot=1`, identificadores como `live-032`, unidades como `pitch_percent`, límites de evidencia ni una segunda marca de tiempo dentro de la explicación. Un pase progresivo se explica como una acción que rompe una línea y hace avanzar la jugada. En modo avanzado o analista, solo se añade contexto que pueda expresarse de forma natural, por ejemplo la cantidad de pases de una jugada. Los identificadores, métricas y límites originales siguen disponibles en los campos estructurados y en la ruta de fuentes del borrador para conservar la trazabilidad sin mostrarlos en el comentario.

## **Archivos**

- `apps/backend/src/match_intelligence/adapters/sources/live_scenario.py`
- `apps/backend/src/match_intelligence/adapters/sources/tracking_mock.py`
- `apps/backend/src/match_intelligence/domain/contracts.py`
- `apps/backend/src/match_intelligence/adapters/provisional/analytics.py`
- `apps/backend/src/match_intelligence/adapters/provisional/narrative.py`
- `apps/frontend/src/components/match/LiveTrackingPitch.jsx`
- `apps/backend/tests/test_live_tracking_api.py`
- `apps/backend/tests/test_match_experience_api.py`

## **Verificación del 24 de octubre de 2026**

```powershell
uv run --project apps/backend pytest apps/backend/tests/test_live_tracking_api.py apps/backend/tests/test_match_experience_api.py apps/backend/tests/test_analytics_tracking.py apps/backend/tests/test_event_validation.py -q
npm run lint
npm run build
```

Resultados: 62 pruebas seleccionadas y 342 pruebas de la suite completa superadas. El lint terminó sin errores nuevos, la compilación terminó correctamente con Vite 8.3.3 y `git diff --check` no encontró errores de espacios.

En Chrome se reprodujo el partido a 8×. La captura en `1:44` y la comprobación del DOM confirmaron 22 jugadores posicionados, balón visible y la situación `Partido detenido por lesión`. La pantalla mostró el momento narrado, la tarjeta amarilla anterior y el marcador sincronizado. La reproducción continuó solicitando cuadros hasta cerca del final sin errores HTTP.

## **Siguiente etapa**

El escenario actual ya evita pases arbitrarios mediante reglas y propósitos declarados, pero sigue siendo un guion reproducible. Falta portar el siguiente nivel del enfoque estudiado: evaluar varias opciones reales en cada cuadro, seleccionar el receptor con mejor espacio y menor riesgo, resolver intercepciones según quién llega primero y generar saques de banda, esquina, fuera de juego y saque de meta desde la trayectoria física del balón.

## **Validación de comentarios del 24 de octubre de 2026**

Probamos las dos rutas de narrativa usadas por el servidor: la plantilla provisional y el adaptador de Persona 3. Ambas producen texto público sin claves, unidades, identificadores ni límites internos. El servidor local devolvió `Aurora FC rompe una línea y hace avanzar la jugada.` para `live-003` y `Río Unido genera una ocasión clara.` para `live-032`. La evidencia continúa disponible en los campos estructurados de la respuesta.
