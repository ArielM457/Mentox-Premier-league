# Evaluación de la arquitectura de eventos en Azure

## Conclusión

La separación propuesta es viable, pero no son tres colas equivalentes:

1. API HTTP de ingreso, protegida opcionalmente por Azure API Management.
2. Event Hubs para todos los eventos aceptados y la telemetría reconstruible de alto volumen.
3. Un filtro determinista que valida, deduplica, actualiza el estado y decide la ruta.
4. Azure Service Bus para jugadas importantes y solicitudes a agentes, con deduplicación, reintentos y cola de mensajes no procesables.
5. SSE desde la API al frontend para la experiencia en directo.

API Management no clasifica el partido: protege y limita la API HTTP. El backend publica cada resultado en el canal correspondiente.

## Estado de `origin/main`

Ya existen el filtro, `RoutingDecision v1`, las rutas lógicas locales `metrics`, `important` y `discarded`, analítica, agentes, API, frontend oficial y Event Hubs para `match-events` y `match-insights`. La topología está documentada y simulada, pero no desplegada.

Faltan Service Bus, API Management, el trabajador distribuido y la promoción controlada de observaciones visuales a `MatchEvent`.

## Captura cada segundo

El segundo debe ser una ventana de publicación. El trabajador agrupa por `match_id` y segundo de vídeo, conservando identificadores originales. Envía métricas reconstruibles a Event Hubs, jugadas confirmadas a Service Bus y evidencia auditable a Blob Storage.

Las detecciones actuales siguen siendo observaciones experimentales. Ningún candidato se convierte en `MatchEvent` sin cumplir la política de evidencia.

Se consultó documentación vigente de Microsoft mediante Context7: Event Hubs está orientado a streaming y telemetría; Service Bus, a mensajería durable con funciones empresariales.
