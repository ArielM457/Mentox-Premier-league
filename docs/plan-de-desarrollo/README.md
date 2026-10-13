# **Plan de desarrollo para cinco personas**

Este plan divide el desarrollo entre cuatro personas de programación y una persona de UX/UI. Se basa en [el plan de integración](../plan_integracion_modelos_futbol.md), [los requisitos](../03-requisitos.md), [los casos de uso](<../06-Casos de Uso — Plataforma de Inteligencia de Partidos con IA.md>), [las decisiones técnicas](../07-decisiones-tomadas.md) y [el formato de eventos](../08-formato-de-eventos.md).

El plan de integración describe una dirección técnica. Roboflow Sports, SoccerNet, xT, VAEP y xG todavía requieren pruebas de compatibilidad, calidad, permisos y tiempo de respuesta. Los eventos sintéticos siguen siendo la fuente principal del producto.

## **Reparto**

**1. [Datos y visión](persona-1-datos-y-vision.md).** Generación sintética, adaptadores de vídeo, Roboflow Sports, SoccerNet y fusión de eventos.

**2. [Estado y analítica](persona-2-estado-y-analitica.md).** Estado del partido, estadísticas, modelos de valor, patrones y selección de momentos.

**3. [Agentes e inteligencia narrativa](persona-3-agentes-y-narrativa.md).** CrewAI, explicaciones, personalización, idiomas, preguntas, verificación y resúmenes.

**4. [API y experiencia funcional](persona-4-api-y-frontend.md).** FastAPI, canal en directo, reproductor, superposiciones, controles, revisión editorial e integración de React.

**5. [Diseño UX/UI](persona-5-diseno-ux-ui.md).** Recorridos, pantallas, sistema visual, estados, accesibilidad y entrega de diseños listos para implementar.

Cada persona de programación puede trabajar con datos de ejemplo desde el primer día. La integración final une sus módulos sin obligar a que una persona termine toda su parte antes de que otra empiece.

## **Contratos compartidos para avanzar en paralelo**

En el arranque acordamos una versión pequeña de estos contratos. Cada responsable entrega ejemplos válidos y ejemplos con datos faltantes. Los demás desarrollan contra esos ejemplos.

Los campos y ejemplos iniciales están en [contratos de trabajo](contratos-de-trabajo.md).

**1. Evento de entrada.** `MatchEvent v1` y metadatos del partido siguen [el formato actual](../08-formato-de-eventos.md). Persona 1 mantiene la evolución del contrato. La API actual solo valida su forma; todavía no ingiere ni guarda eventos.

**2. Estado del partido.** Persona 2 entrega un `MatchSnapshot v1` con partido, período, reloj, marcador, estadísticas, métricas disponibles y referencias a eventos. Los valores sin datos suficientes quedan ausentes o marcados como no disponibles.

**3. Momento candidato.** Persona 2 entrega un `InsightCandidate v1` con tipo de momento, tiempo de partido, prioridad, hechos calculados, eventos de origen y límites de la evidencia.

**4. Narración propuesta.** Persona 3 entrega un `NarrativeDraft v1` con texto en español o inglés, modo de usuario, preferencia aplicada, fuentes, resultado de verificación y estado de revisión.

**5. Salida pública.** Persona 4 transforma una narración aprobada en `OverlayMessage v1` con identificador, tiempo de vídeo, duración sugerida, prioridad y contenido legible por máquina. También define la respuesta de la API para estado, preguntas y resúmenes.

**6. Decisión de ruta.** Persona 2 entrega `RoutingDecision v1` antes de cualquier agente. Los eventos de solo métricas no llegan al orquestador.

**7. Solicitud de agente.** Persona 3 entrega `AgentRequest v1` y `AgentDispatch v1` con contexto reducido, vencimiento, destino y razón.

**8. Contexto previo.** Persona 3 mantiene `PregameFact v1` con fuente, vigencia y aprobación para que el narrador solo use información autorizada.

El contrato del evento ya tiene versión `1.0`. Los otros nombres son contratos de trabajo propuestos y se cerrarán antes de implementar la conexión entre módulos. Los cambios incompatibles requieren nueva versión y un ejemplo actualizado. No editamos al mismo tiempo el mismo archivo de contrato.

## **Límites de archivos**

Persona 1 trabaja principalmente en adaptadores de fuentes, generadores y muestras sintéticas. Persona 2 trabaja en dominio y casos de uso de analítica. Persona 3 trabaja en orquestación de agentes y narración. Persona 4 trabaja en el adaptador HTTP y `apps/frontend`. Persona 5 entrega diseños y especificaciones en la carpeta de diseño acordada por el equipo.

Los archivos compartidos de configuración, contratos y documentación se cambian mediante una propuesta corta y revisión de las personas afectadas. Cada módulo expone una interfaz pública pequeña y prueba su comportamiento sin importar directamente las partes internas de otro módulo.

## **Orden de integración**

**1. Acordar contratos y ejemplos.** Usamos un partido sintético corto con pases, presión, recuperación, tiro y gol. Definimos reloj, identidad de jugadores, posiciones, estados sin datos y referencias de origen. Persona 5 entrega los primeros recorridos y bocetos.

**2. Completar el procesamiento rápido.** Persona 1 reproduce eventos. Persona 2 calcula estado, filtra rutas y reconoce jugadas. Persona 3 refina solicitudes y prueba el orquestador local. Persona 4 prepara los canales y mensajes simulados. Persona 5 termina los diseños de los recorridos principales.

**3. Unir el flujo sintético por eventos.** Conectamos evento, filtro, estado, catálogo, refinamiento, orquestador, agente, validación y superposición. Después unimos el resumen de medio tiempo, el resumen final, la aprobación y los reportes. Este flujo completo es el primer hito demostrable.

**4. Conectar vídeo y analítica avanzada.** Persona 1 prueba Roboflow Sports y SoccerNet por separado antes de fusionarlos. Persona 2 incorpora solo métricas cuyo cálculo pueda validar. Persona 4 mide sincronización y retraso visibles. Las funciones de vídeo se incorporan al flujo público cuando sus resultados y permisos sean suficientes.

**5. Probar carga y fallos.** Medimos el filtro y los canales con el volumen esperado y un pico mayor. Detenemos una instancia, repetimos mensajes y simulamos un modelo caído sin detener las métricas.

**6. Ensayar la demo.** Repetimos el mismo partido en inglés y español, en modos casual y analista, con club y jugador favoritos. Mostramos una ruta de solo métricas, una situación de peligro, una simulación marcada, contexto previo aprobado, ambos resúmenes y un fallo controlado.

Este orden expresa hitos, no fechas. La duración del hackathon y la disponibilidad de modelos aún no están documentadas.

## **Prioridad y decisiones abiertas**

La primera entrega cubre los requisitos P0 mediante eventos sintéticos y vídeo sincronizado. La extracción de eventos desde vídeo es una línea de trabajo real de Persona 1, con evaluación propia. xT, VAEP, xG, voz, control y caos se incorporan según datos y pruebas; no se mostrarán cifras de modelos sin validar.

Debemos cerrar juntos el proveedor de modelos para CrewAI, el vídeo permitido para la demo, la meta numérica de latencia y quién aprueba el análisis final. Estas decisiones figuran en [decisiones pendientes](../05-decisiones-pendientes.md). Hasta entonces cada módulo usa adaptadores y ejemplos locales.

## **Regla para dar un módulo por terminado**

El módulo entrega código, contrato, datos de prueba, una prueba de su comportamiento y una demostración desde la interfaz o la API que le corresponda. Debe registrar lo que se midió localmente y lo que todavía falta probar con vídeo, modelos externos o una transmisión real. La [rúbrica](../04-evaluacion.md) guía la revisión final.
