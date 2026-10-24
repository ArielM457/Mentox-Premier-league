# Resumen del trabajo realizado · Persona 1

El flujo completo también está representado en el [diagrama de datos, Azure y modelos locales](diagrama-flujo.md).

## 1. Definimos el contrato de eventos

- Creamos `MatchEvent 1.0` como formato común.
- Definimos identificadores de partido y evento.
- Incluimos reloj del partido y tiempo del vídeo.
- Añadimos equipos, jugadores, posiciones, resultados y procedencia.
- Separamos eventos sintéticos de inferencias provenientes de vídeo.

## 2. Creamos un partido sintético reproducible

- Generamos siempre el mismo partido a partir de una semilla.
- Incluimos dos equipos y una plantilla de jugadores.
- Incluimos pases, tiros, entradas, presión, recuperaciones y cambios de posesión.
- Construimos una secuencia de control, una transición y un gol.
- Evitamos incorporar datos reales de partidos de la Premier League.

**Historia:** DV-US-01.

## 3. Implementamos la reproducción del partido

- Los eventos pueden emitirse progresivamente.
- Se puede iniciar, pausar y reanudar la reproducción.
- Se puede reiniciar desde el comienzo.
- Se puede cambiar la velocidad.
- La velocidad no modifica el contenido ni el orden de los eventos.
- El modo local funciona sin Azure.

**Historia:** DV-US-02.

## 4. Implementamos la validación de eventos

- Los eventos válidos conservan sus identificadores y tiempos.
- Los eventos incompletos o incorrectos se rechazan con errores estructurados.
- Un evento inválido no detiene los eventos posteriores.
- El backend puede procesar lotes con aceptados y rechazados.

**Historia:** DV-US-03.

## 5. Evitamos el doble conteo

- Detectamos duplicados usando `match_id` y `event_id`.
- Un reintento no se contabiliza como un evento nuevo.
- Los duplicados quedan registrados para diagnóstico.
- La lógica funciona con el transporte local.
- La prueba contra Event Hubs real aprobó el 13 de octubre de 2026 mediante DV-US-15.

**Historia:** DV-US-04.

## 6. Detectamos eventos tardíos

- Identificamos eventos cuyo reloj es anterior al último procesado.
- Los eventos tardíos no se eliminan silenciosamente.
- Registramos su llegada y la diferencia temporal.
- La política final de reconstrucción debe acordarse con Persona 2.

**Historia:** DV-US-05.

## 7. Preparamos la infraestructura Azure

- Creamos una plantilla Bicep parametrizada.
- Definimos un namespace de Event Hubs.
- Definimos el event hub `match-events`.
- Definimos grupos de consumidores para backend y diagnóstico.
- Definimos una cuenta StorageV2.
- Definimos los contenedores privados `matches`, `authorized-videos` y `observations`.
- Deshabilitamos autenticación mediante claves compartidas.
- Preparamos autenticación con identidad Azure y RBAC.
- Documentamos `validate`, `what-if`, despliegue y eliminación.
- La plantilla compila localmente.
- El despliegue real y RBAC aprobaron el 13 de octubre de 2026 mediante DV-US-14.

**Historia:** DV-US-06.

## 8. Implementamos Azure Event Hubs

- Creamos un productor asíncrono.
- Creamos un consumidor asíncrono.
- Definimos un sobre de transporte sin modificar `MatchEvent`.
- Conservamos la carga deportiva completa.
- Registramos tiempos de producción, publicación y recepción.
- Hacemos visibles los errores de publicación y consumo.
- Aplicamos deduplicación después de recibir mensajes.
- Creamos una prueba manual de ida y vuelta.
- La ejecución contra Azure real aprobó mediante DV-US-15.

**Historia:** DV-US-07.

## 9. Permitimos cambiar entre memoria y Azure

- Añadimos el modo `memory` para desarrollo local.
- Añadimos el modo `azure_event_hubs` para integración.
- La selección se realiza mediante variables de entorno.
- El generador no depende del SDK de Azure.
- Los consumidores entregan objetos deportivos equivalentes.
- No existe una caída silenciosa de Azure hacia memoria.

**Historia:** DV-US-08.

## 10. Implementamos almacenamiento de artefactos

- Clasificamos partidos sintéticos, vídeos autorizados y observaciones.
- Asignamos un contenedor específico a cada tipo.
- Relacionamos cada archivo con su partido y origen.
- Conservamos tipo MIME y metadatos de procedencia.
- Calculamos SHA-256 antes de almacenar.
- Verificamos el hash después de recuperar.
- Evitamos sobrescrituras accidentales.
- Creamos una prueba manual para Blob Storage.
- `matches`, `observations`, integridad y rechazo de sobrescritura aprobaron en Azure mediante DV-US-16.

**Historia:** DV-US-09.

## 11. Implementamos la sincronización con vídeo

- Asociamos eventos mediante `video_time_ms`.
- Conservamos también `clock_ms`.
- Pausar evita que aparezcan eventos futuros.
- Adelantar reconstruye el estado sin mostrar mensajes históricos como nuevos.
- Retroceder reconstruye un prefijo anterior.
- Reiniciar vuelve a la posición cero.
- Indicamos que el tiempo del vídeo es una alineación proporcionada, no una detección automática.
- Falta conectarlo a una interfaz y a un vídeo permitido.

**Historia:** DV-US-10.

## 12. Creamos el evaluador de modelos de visión

- Definimos un contrato para registrar vídeo, permiso, hash y duración.
- Registramos proveedor, modelo, versión, revisión, clases y parámetros.
- Evaluamos detecciones espaciales mediante tiempo e IoU.
- Evaluamos acciones mediante clase y tolerancia temporal.
- Calculamos precisión, recobrado y F1.
- Registramos falsos positivos y observaciones omitidas.
- Separamos calidad y tiempo de procesamiento.
- Los resultados simulados nunca habilitan un modelo para la demo.
- Un resultado insuficiente no bloquea el flujo sintético.
- Falta ejecutar Roboflow Sports y SoccerNet con un vídeo real permitido.

**Historia:** DV-US-11.

## 13. Evitamos inventar identidades de jugadores

- Una detección visual conserva `track_id`.
- Sin evidencia independiente, `player_id` permanece vacío.
- La confianza del detector no confirma una identidad nominal.
- Una asociación confirmada necesita referencia y responsable.
- El jugador debe pertenecer a la plantilla conocida.
- Rechazamos asociaciones de otro partido o seguimiento.
- Falta probar asociaciones sobre observaciones de vídeo reales.

**Historia:** DV-US-12.

## 14. Implementamos la fusión trazable de observaciones

- Comparamos partido, seguimiento, equipo, tiempo y posición.
- Aplicamos tolerancias temporales y espaciales configurables.
- Conservamos las observaciones originales.
- Generamos un identificador determinista para el evento fusionado.
- Usamos una confianza conservadora.
- Una contradicción no genera un hecho deportivo.
- Cuando falta evidencia, no generamos `MatchEvent` y explicamos el motivo.
- Una identidad no confirmada nunca completa `player_id`.
- Falta calibrar las tolerancias con resultados reales.

**Historia:** DV-US-13.

## 15. Creamos scripts de integración

- `event_hubs_smoke.py` prueba publicación, consumo y duplicados.
- `blob_storage_smoke.py` prueba carga, recuperación e integridad.
- `evaluate_vision_predictions.py` compara predicciones con anotaciones manuales.
- `.env.example` documenta las variables sin incluir secretos.

## 16. Creamos pruebas automatizadas

- Probamos el generador sintético.
- Probamos reproducción y controles.
- Probamos validación, deduplicación y eventos tardíos.
- Probamos adaptadores y configuración Azure mediante dobles.
- Probamos almacenamiento, integridad y procedencia.
- Probamos sincronización y saltos del vídeo.
- Probamos métricas de evaluación de visión.
- Probamos protección de identidad.
- Probamos fusión, contradicciones y evidencia insuficiente.

**Resultado actualizado:** 135 pruebas aprobadas con Python 3.12.13 el 13 de octubre de 2026.

## 17. Documentamos cada historia

- Creamos evidencia individual para DV-US-01 a DV-US-13.
- Registramos criterios cubiertos.
- Registramos archivos modificados.
- Registramos decisiones y limitaciones.
- Registramos comandos y versiones.
- Diferenciamos pruebas locales de integraciones reales.
- No presentamos propuestas o fixtures como resultados de modelos reales.

Las evidencias están en [evidencias](evidencias/README.md).

## 18. Preparamos el siguiente ciclo

Creamos DV-US-14 a DV-US-22 para probar lo construido con servicios y medios reales:

1. Desplegar Azure y asignar RBAC.
2. Probar Event Hubs real.
3. Probar Blob Storage real.
4. Preparar un vídeo permitido.
5. Crear una interfaz mínima de sincronización.
6. Ejecutar Roboflow Sports.
7. Ejecutar SoccerNet.
8. Calibrar identidad y fusión.
9. Ejecutar el ensayo final integrado.

El procedimiento está en [plan de pruebas con servicios reales](plan-pruebas-servicios-reales.md).

## 19. Publicamos el trabajo

- El código y la documentación de DV-US-06 a DV-US-13 fueron confirmados en Git.
- El commit publicado es `3ce1a86`.
- La rama `main` quedó sincronizada con `origin/main` después de esa publicación.

El presente resumen y [estado-actual.md](estado-actual.md) son documentos posteriores a ese commit y deben confirmarse cuando se decida subirlos.

## Próximo paso

DV-US-14, DV-US-15 y DV-US-16 están verificadas en integración. El siguiente trabajo es **DV-US-17 · Preparar el paquete de vídeo permitido**.

Necesitamos definir:

- suscripción Azure;
- grupo de recursos;
- región;
- prefijo;
- identidad para RBAC;
- responsable o límite del costo.

No necesitamos compartir contraseñas, tokens ni cadenas de conexión.
