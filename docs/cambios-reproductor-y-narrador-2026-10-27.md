# **Cambios del reproductor y el narrador**

Fecha: 27 de octubre de 2026.

## **Resultado**

Hicimos más compacto el reproductor del Centro del Partido de The Prime Moment. La barra ahora está pegada al borde inferior del estadio y no deja un espacio vacío debajo.

Quitamos de la barra el encabezado Momentos destacados y el contador de tiempo. Las jugadas importantes siguen marcadas sobre la línea mediante puntos pequeños.

El comentario de un momento aparece encima de la barra. Muestra el minuto de partido y tiene una X en la esquina superior derecha para cerrarlo.

Encima del momento agregamos un narrador de eventos. La lista conserva todos los eventos ocurridos y permite desplazarse dentro de ella. Los pases nombran al pasador y al receptor. De igual forma, existen frases para remates, goles, recuperaciones, entradas, cambios de posesión, presión, faltas, tarjetas, lesiones y reanudaciones.

## **Comportamiento en directo**

El selector de velocidad se oculta cuando la reproducción está en el punto en directo.

Cuando la persona retrocede, aparece el selector con las velocidades disponibles y una acción En directo. Al volver al borde en vivo, la velocidad regresa automáticamente a 1× y el selector vuelve a ocultarse.

El punto más avanzado también se guarda junto con el minuto de reproducción. Esto permite salir del partido, volver y conservar la diferencia entre el punto actual y el punto en directo.

## **Archivos principales**

- `apps/frontend/src/screens/MatchCenter.jsx`: posición de narrador, momento y controles, además del estado en directo.
- `apps/frontend/src/hooks/useMatchClock.js`: guarda el punto más avanzado de la reproducción.
- `apps/frontend/src/components/match/LiveNarrator.jsx`: lista de narración sincronizada.
- `apps/frontend/src/components/match/OverlayCard.jsx`: minuto y botón para cerrar el momento.
- `apps/frontend/src/lib/commentary.js`: frases de eventos en los siete idiomas disponibles.
- `apps/frontend/src/styles/ux.css`: reproductor compacto y pila de mensajes.
- `apps/frontend/src/styles/experience.css`: cierre del momento y control En directo.

## **Validación ejecutada**

- `npm run lint:frontend`: correcto. Permanecen dos advertencias anteriores en `useCatalog.js` y `MomentDetail.jsx`.
- `npm run build:frontend`: compilación correcta con 72 módulos.
- Prueba directa del narrador: un evento con `player_id=p1` y `receiver_player_id=p2` produjo `Pase de Ana para Bea.`.
- Prueba del minuto: `1 920 000 ms` produjo `32'`.
- Prueba en navegador a 1440 por 1000 píxeles: narrador, momento y barra aparecieron en capas separadas.
- Prueba en navegador a 390 por 844 píxeles: la barra quedó pegada al estadio y el contenido se reorganizó sin cubrir los controles.
- Prueba del cierre: después de pulsar la X quedaron cero tarjetas de momento visibles.

No levantamos contenedores ni regeneramos Postman. Para la comprobación usamos FastAPI, Vite y Chrome local.
