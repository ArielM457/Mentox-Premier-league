# **Decisiones pendientes**

Las decisiones generales ya acordadas están en [decisiones tomadas](07-decisiones-tomadas.md). Aquí quedan los detalles que todavía deben cerrarse.

**1. Fuente sintética.** Elegir los generadores y los conjuntos de referencia concretos. Revisar licencias y evitar incorporar eventos reales de la Premier League al proyecto.

**2. Despliegue de modelos.** La asignación inicial por tarea está definida en [política de modelos de IA](12-politica-modelos-ia.md). Falta confirmar el proveedor, las regiones, las cuotas, los nombres de despliegue, el presupuesto y el comportamiento sin conexión. No guardar claves en el repositorio.

**3. Revisión antes de publicar.** Definir quién revisa los análisis finales, qué interfaz usa y si una narración breve en directo puede publicarse con una revisión automática previa. El análisis final no se publica sin la revisión acordada.

**4. Vídeo de ejemplo.** Elegir clips propios, sintéticos o con permiso de uso. Definir cómo se obtienen o sincronizan eventos durante su reproducción y cómo se mide el retraso.

**5. Fórmulas y umbrales.** Seleccionar métricas iniciales, ventanas de tiempo y reglas para presión, ritmo, calidad de pase y momentos relevantes. La investigación está en `09-investigacion-metricas-y-herramientas.md`.

**6. Rendimiento.** Acordar una meta numérica para el tiempo entre evento, análisis y salida visible. Medirla con el hardware y el vídeo de la demo.

**7. Integración externa.** Confirmar si los organizadores entregan un contrato de superposiciones o una tecnología de renderizado. El contrato local puede adaptarse después.

**8. Funciones opcionales.** Decidir si identificación automática de jugadores, velocidades y extracción desde vídeo alcanzan calidad suficiente para la demo.

**9. Idiomas.** Ya se acordaron inglés y español. Faltan criterios de revisión lingüística y reglas para nombres, unidades y términos futbolísticos.

**10. Canal de eventos.** Comparar un servicio administrado, Redis Streams, RabbitMQ y Kafka con el volumen esperado, el entorno de despliegue y el tiempo disponible. La decisión necesita una prueba de carga y recuperación.

**11. Base previa al partido.** Definir fuentes autorizadas, vigencia, derechos de uso, responsable de aprobación y política para promociones y próximos eventos del canal.

**12. Simulaciones de peligro.** Elegir las primeras acciones que se podrán cambiar, el método de simulación y las reglas para comunicar incertidumbre. No se mostrarán probabilidades hasta validar un modelo y sus datos.

**13. Tiempos muertos.** Decidir si las faltas, pausas y reanudaciones se incorporan como una nueva versión de `MatchEvent` o como señales separadas del reloj y del reproductor.
