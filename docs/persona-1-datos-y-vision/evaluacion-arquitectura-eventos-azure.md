# Evaluación de la arquitectura de eventos en Azure

## Conclusión

La separación propuesta es viable, pero no son tres colas equivalentes:

1. API HTTP de ingreso, protegida opcionalmente por Azure API Management.
2. Event Hubs para todos los eventos aceptados y la telemetría reconstruible de alto volumen.
3. Un filtro determinista que valida, deduplica, actualiza el estado y decide la ruta.
4. Azure Service Bus para jugadas importantes y solicitudes a agentes, con deduplicación, reintentos y cola de mensajes no procesables.
5. SSE desde la API al frontend para la experiencia en directo.

API Management no clasifica el partido: protege y limita la API HTTP. El backend publica cada resultado en el canal correspondiente.

## Estado después de la integración

Ya existen el filtro, `RoutingDecision v1`, analítica, agentes, API y frontend oficial. `RoutedEventPipeline` conecta el ingreso con dos salidas: métricas reconstruibles e importantes. Funciona en memoria y tiene adaptadores Azure con identidad.

La plantilla añade `match-metrics` al namespace existente y puede crear una cola `important-events` en Service Bus Basic. Esta última permanece desactivada por defecto para evitar costo accidental. La vista de visión está incorporada en Resumen dentro del centro del partido; no existe una segunda interfaz de producto.

Faltan desplegar y probar los recursos nuevos en Azure, ejecutar un trabajador distribuido permanente y definir la promoción controlada de observaciones visuales a `MatchEvent`. API Management continúa opcional y no es necesario para probar el backend.

## Captura cada segundo

El segundo debe ser una ventana de publicación. El trabajador agrupa por `match_id` y segundo de vídeo, conservando identificadores originales. Envía métricas reconstruibles a Event Hubs, jugadas confirmadas a Service Bus y evidencia auditable a Blob Storage.

Las detecciones actuales siguen siendo observaciones experimentales. Ningún candidato se convierte en `MatchEvent` sin cumplir la política de evidencia.

Se consultó documentación vigente de Microsoft mediante Context7: Event Hubs está orientado a streaming y telemetría; Service Bus, a mensajería durable con funciones empresariales.
