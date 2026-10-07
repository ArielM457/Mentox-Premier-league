# **Formato estándar de eventos**

Definimos una versión inicial de contrato interno para todos los eventos, sin depender del origen. Los generadores sintéticos y los futuros adaptadores de vídeo deben producir este formato. La API publica su esquema formal en `/openapi.json` cuando está en ejecución.

## **Sobre el partido**

Cada partido tiene un identificador, dos equipos, jugadores conocidos, dimensiones del campo en metros y la dirección de ataque de cada equipo por período. Las coordenadas de eventos son posiciones fijas del campo, por lo que no cambian de orientación al cambiar de lado.

El contrato de metadatos usa `schema_version`, `match_id`, `home_team`, `away_team`, `pitch_length_m`, `pitch_width_m`, `players` y `attacking_directions`. Cada equipo tiene identificador y nombre. Cada jugador tiene identificador, equipo, nombre y número de camiseta opcional. Cada dirección indica período, equipo y uno de los valores `left_to_right` o `right_to_left`.

## **Sobre cada evento**

**1. Identidad.** `event_id` identifica el evento dentro del partido. `match_id` enlaza con los metadatos. Un identificador repetido no debe contarse dos veces.

**2. Tiempo.** `period` indica la parte del encuentro. `clock_ms` son milisegundos desde el inicio de ese período, incluido el tiempo añadido. `video_time_ms` son milisegundos desde el inicio del archivo o señal de vídeo y pueden faltar si aún no hay sincronización. Se guardan ambos tiempos porque el reloj de partido y el vídeo no son equivalentes.

**3. Autor.** `team_id` identifica al equipo responsable y `player_id` al jugador cuando se conoce. Un evento de cambio de posesión puede carecer de jugador.

**4. Tipo.** La primera versión admite `pass`, `shot`, `tackle`, `possession_change`, `pressure` y `recovery`. Los adaptadores deben traducir sus nombres externos a estos valores.

**5. Posición.** `start` y `end` usan `x` y `y` entre 0 y 100. Son coordenadas normalizadas de un campo fijo. Para calcular distancias reales se necesitan las dimensiones del partido. La posición puede faltar cuando la fuente no la conoce.

**6. Resultado.** `outcome` distingue éxito, fallo, gol, atajada, bloqueo, tiro fuera y resultado desconocido. No todos los resultados aplican a todos los tipos de evento.

**7. Procedencia.** `source` distingue un generador sintético de una inferencia de vídeo. `confidence` se usa solo si la fuente produce una estimación. Un valor desconocido no se inventa.

**8. Relaciones.** `related_event_ids` permite vincular una jugada con sus acciones. Las explicaciones y métricas deben conservar estos identificadores.

## **Ejemplo**

```json
{
  "schema_version": "1.0",
  "event_id": "evt-104",
  "match_id": "demo-001",
  "period": 1,
  "clock_ms": 802000,
  "video_time_ms": 805500,
  "type": "pass",
  "team_id": "team-a",
  "player_id": "player-7",
  "start": {"x": 43.0, "y": 51.0},
  "end": {"x": 62.0, "y": 46.0},
  "outcome": "success",
  "source": "synthetic",
  "confidence": null,
  "related_event_ids": []
}
```

## **Reglas de calidad**

No se calcula velocidad desde un único evento con posición inicial y final si se desconoce el tiempo del movimiento. La presión táctica necesita posiciones, tiempo y una regla definida. El tiempo de vídeo no implica que un evento haya sido detectado automáticamente.

La versión `1.0` es interna y puede evolucionar. Cualquier cambio incompatible debe crear una versión nueva y un adaptador o migración. Quedan pendientes las reglas detalladas por tipo de evento, la coherencia entre identificadores de jugadores y equipos, y el orden de eventos tardíos.
