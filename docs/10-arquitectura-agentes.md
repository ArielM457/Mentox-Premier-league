# **Equipo de agentes y flujo de revisión**

Esta es la distribución inicial de trabajo con CrewAI. Define responsabilidades para diseñar el sistema; todavía no hay agentes funcionando. Usaremos un flujo controlado para ordenar tareas y conservar evidencia, y equipos de agentes para las decisiones que requieren interpretación.

## **Entrada común**

Los agentes reciben eventos con el formato `1.0`, estado calculado, métricas, preferencias del usuario y tiempo del vídeo. Cada resultado debe indicar qué eventos y cálculos lo sustentan. Los agentes no modifican el evento original ni el marcador calculado.

## **Responsabilidades propuestas**

**1. Observador.** Resume qué cambió desde el último tramo: posesión, tiros, presión y participantes. Entrega hechos y sus identificadores, sin redactar una historia final.

**2. Analista táctico.** Propone patrones de presión, progresión, control o transición. Explica qué señales apoyan la lectura y qué datos faltan. Puede concluir que no hay evidencia suficiente.

**3. Selector de momentos.** Decide qué hallazgos merecen aparecer durante el partido. Considera relevancia, repetición, tiempo en pantalla y preferencias del espectador.

**4. Narrador.** Convierte un hallazgo verificado en texto breve para pantalla y en una explicación más amplia cuando se solicita. Produce español o inglés según la configuración.

**5. Personalizador.** Elige enfoque y nivel de detalle para aficionado casual, analista, club favorito o jugador favorito. No cambia hechos ni cifras.

**6. Verificador.** Contrasta cada cifra y afirmación con el estado y los eventos. Devuelve aprobación, corrección solicitada o rechazo, con motivo. Si llega un reporte de error, vuelve a comprobar la conclusión y registra el resultado.

**7. Agente de resumen.** Al terminar el partido, organiza momentos verificados y propone un análisis final. No lo publica por sí solo.

Estas responsabilidades pueden combinarse o dividirse según las pruebas de tiempo de respuesta. Tener más agentes no debe retrasar avisos que necesitan aparecer durante la jugada.

## **Decisiones y revisión**

El equipo de agentes puede elegir momentos, formular hipótesis y adaptar narraciones. El código del dominio calcula marcador, conteos, porcentajes y medidas definidas. El verificador puede bloquear una salida cuando la evidencia no la respalda.

Los mensajes en directo deben pasar por validación de estructura y verificación de hechos antes de mostrarse. Los análisis finales quedan en estado pendiente hasta completar la revisión editorial acordada. El responsable de aprobarlos se definirá más adelante.

Cuando se reporta un error, conservamos la salida original, el reporte, las fuentes consultadas, el resultado de la nueva verificación y la corrección o retirada. No se debe corregir silenciosamente un análisis publicado.

## **Fallas**

Si un agente no responde, el estado del partido y los eventos siguen procesándose. El flujo puede omitir una narración sin inventar una respuesta. Si el verificador rechaza una afirmación, no se muestra hasta corregirla. Los límites de espera y los reintentos se definirán al medir la latencia real.
