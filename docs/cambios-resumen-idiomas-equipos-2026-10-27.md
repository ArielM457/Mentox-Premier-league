# Cambios de resumen, idiomas y equipos

Fecha: 27 de octubre de 2026.

## Resultado

The Prime Moment permite elegir tres tipos de resumen al terminar un partido:

- **Resumen corto:** muestra solo los goles. Está pensado para cerrar un programa.
- **Resumen extendido:** muestra goles, estadísticas y momentos importantes del partido.
- **Resumen personalizado:** muestra únicamente goles y ocasiones de peligro en las que participa el jugador elegido.

Cada variante usa un `draft_id` diferente, conserva sus `source_event_ids` y mantiene su propia revisión editorial.

## Persistencia

La API sigue guardando los resúmenes en `match_summaries`. La migración `202610270001_summary_variants.sql` agrega:

- `summary_type`: `short`, `extended` o `player_danger`.
- `player_id`: jugador elegido para el resumen personalizado.
- Un índice por partido, tipo de resumen y jugador.

La interfaz no crea el contenido por su cuenta. Solicita el resumen y los momentos a FastAPI. Cuando Supabase está habilitado, FastAPI guarda y recupera los resúmenes mediante el repositorio existente.

La conexión remota configurada no quedó activada: las siete consultas de comprobación respondieron `401` y falta `SUPABASE_DB_PASSWORD` para aplicar la migración. No se levantaron contenedores ni se modificó la base remota.

## Idiomas

Se agregaron estas opciones:

- Alemán (`de`).
- Chino (`zh`).
- Hindi (`hi`).
- Francés (`fr`).
- Portugués (`pt`).

El selector, los perfiles de experiencia y los tres tipos de resumen tienen traducción propia. Las secciones avanzadas que todavía no tienen una traducción específica usan el texto inglés para no dejar claves vacías ni romper la interfaz.

## Perfiles de experiencia

Los tres perfiles muestran una descripción corta tanto en la configuración inicial como en Preferencias:

- Aficionado: explicaciones claras y sencillas.
- Analista: más detalle táctico y datos.
- Centrado en jugador: seguimiento del jugador elegido durante el partido.

## Escudos

Se recuperaron de `ejemplo ui` los cuatro escudos que faltaban:

- North City.
- Harborline FC.
- Summit Vale.
- Ember Borough.

Aurora y Río ya tenían escudos en la aplicación. Los seis clubes aparecen ahora en la elección de club. Los archivos de imagen son recursos estáticos; los partidos, jugadores, eventos y resúmenes siguen llegando desde la API.

## API

La ruta de resumen acepta:

```text
GET /api/v1/matches/{match_id}/summary
  ?summary_type=short|extended|player_danger
  &player_id={player_id}
  &language=es|en|de|zh|hi|fr|pt
```

`player_id` es obligatorio para `player_danger` y debe pertenecer al partido.

## Comprobaciones ejecutadas

- Backend dirigido: `45 passed`.
- Colección Postman: `55 passed`, `7 failed` por artefactos de visión ausentes que ya estaban pendientes.
- Frontend: lint correcto, con `705` claves iguales entre español e inglés.
- Frontend: build de Vite correcto.
- Suite completa: `467 passed`, `18 failed`, `7 skipped`. Siete fallos de Postman causados por el cambio de identificador se corrigieron y se volvieron a comprobar; los fallos restantes corresponden a artefactos de visión ausentes y una validación previa de `.env.example`.
- Supabase remoto: conexión rechazada con `401`; migración remota pendiente.

No se crearon contenedores ni recursos de Azure.

## Corrección del flujo de experiencia

Después de probar la selección en portugués encontramos que el adaptador de Persona 3 aceptaba el código `pt`, pero su catálogo interno de etiquetas solo incluía español e inglés. Esto producía un error `KeyError: 'pt'` al pedir los overlays.

Corregimos el catálogo narrativo para alemán, chino, hindi, francés y portugués. También agregamos una prueba que reproduce el caso portugués, modo jugador, nivel avanzado, club Río y jugador `rio-8`.

El último paso de la configuración inicial ahora muestra un resumen corto con:

- Idioma elegido.
- Club elegido.
- Jugador elegido.
- Perfil de experiencia elegido.

La pestaña Resumen del partido en vivo contiene los selectores corto, extendido y personalizado. Usa únicamente eventos que ya ocurrieron para no mostrar jugadas futuras.

El partido pasado conserva el resumen generado por la API. Si la API narrativa no responde, la pantalla muestra un resumen mock con el marcador y una explicación sintética, sin enviarlo a revisión editorial.

North City, Harborline FC, Summit Vale y Ember Borough tienen ahora tres jugadores mock cada uno. Aurora y Río conservan los jugadores que llegan desde los partidos sintéticos del backend.

No regeneramos la colección Postman durante esta corrección porque ya no forma parte del flujo de pruebas solicitado.
