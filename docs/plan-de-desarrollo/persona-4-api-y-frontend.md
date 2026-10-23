# **Persona 4: API y experiencia funcional**

## **Objetivo**

Unir los módulos mediante FastAPI y construir la experiencia React que muestra el partido, sus explicaciones y los controles reales del usuario. Esta persona es dueña del transporte y de la interfaz implementada. No reescribe cálculos ni lógica de agentes.

## **Módulos a cargo**

**1. API de partido.** Partir del backend existente, que hoy solo valida eventos y metadatos. Añadir rutas para cargar un partido, iniciar o consultar la reproducción, obtener estado, momentos, fuentes, preguntas y resúmenes. Swagger debe reflejar los contratos reales. La API delega en los casos de uso de las otras personas.

**2. Canal en directo.** Conectar los módulos mediante eventos durables y entregar estado y mensajes nuevos al frontend durante la reproducción. Separar canales lógicos para eventos aceptados, métricas, candidatos, peligro, solicitudes de agentes, narraciones, resúmenes y errores. Medir el tiempo de entrega y conservar tiempo de partido y tiempo de vídeo.

**3. Reproductor y sincronización.** Reproducir un vídeo permitido, pausar, adelantar y reiniciar sin mostrar mensajes del momento equivocado. La experiencia debe funcionar con eventos sintéticos sincronizados aunque la inferencia automática de vídeo esté en prueba.

**4. Superposiciones.** Convertir narraciones verificadas en `OverlayMessage v1`. Mostrar prioridad, duración sugerida y reemplazo de mensajes de forma legible junto al vídeo. Permitir abrir la explicación y las fuentes del momento.

**5. Preferencias y vistas.** Implementar selección de idioma, modo casual o analista, club favorito, jugador favorito y modo centrado en el jugador. Conectar cada control con resultados del backend. Implementar también la vista de preguntas y el resumen personalizado.

**6. Revisión editorial y reportes.** Crear una vista funcional para consultar el análisis final pendiente, revisar sus fuentes, aprobarlo o rechazarlo. Permitir reportar un error y consultar el resultado de la nueva verificación. La publicación se bloquea del lado del backend mientras falte la aprobación.

**7. Integración visual.** Implementar el diseño entregado por Persona 5 con estados de carga, sin datos, error y contenido largo. Revisar comportamiento en escritorio y móvil, legibilidad y uso con teclado.

**8. Voz opcional.** Si el equipo decide incorporarla, conectar la narración aprobada con salida de voz, controles de silencio y el idioma elegido. Medir el retraso adicional antes de usarla durante el partido.

**9. Disponibilidad y operación.** Preparar consumidores idempotentes, vencimiento de mensajes, reintentos limitados, cola de errores y comprobaciones de salud. Permitir varias instancias sin depender de estado local y conservar el orden por partido.

## **Entregables**

**1.** API documentada en Swagger con ejemplos de respuestas y errores.

**2.** Frontend conectado al backend para el recorrido completo de un partido sintético.

**3.** Reproductor con superposiciones sincronizadas y controles que funcionan.

**4.** Vistas de preferencias, consulta, resumen y revisión editorial.

**5.** Medición visible o registro del retraso desde evento hasta superposición.

**6.** Salida de voz integrada y probada si se confirma como parte del alcance.

**7.** Prueba de carga y recuperación con una instancia detenida, sin perder métricas ni duplicar mensajes.

## **Trabajo independiente**

Puede construir React con ejemplos de `MatchSnapshot v1`, `NarrativeDraft v1` y `OverlayMessage v1`. Puede crear adaptadores de prueba para la API y reemplazarlos por los módulos reales al integrarlos. Persona 5 entrega el diseño sin esperar a que el backend funcione.

Sus archivos principales son `apps/frontend`, `match_intelligence/main.py` y el adaptador HTTP del backend. Los módulos de dominio, visión y agentes se conectan mediante sus interfaces públicas.

## **Comprobación de entrega**

La prueba principal recorre en un navegador un partido completo: reproducción, superposición, cambio de idioma y modo, club y jugador favorito, pregunta, resumen y aprobación. Al pausar o adelantar, la información visible debe corresponder al tiempo correcto. Se comprueba que una respuesta de error no deje controles bloqueados.

Requisitos principales: RF-19, RF-20, RF-24 a RF-28, RF-34 a RF-39 y RNF-05 a RNF-11. Integra las salidas de RF-01 a RF-48 sin duplicar su cálculo.
