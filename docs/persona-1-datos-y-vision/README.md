# Datos, visión e ingesta de eventos

Esta carpeta contiene el plan detallado de Persona 1. Su objetivo es entregar un flujo confiable y reproducible de eventos de fútbol sintéticos, con una vía experimental para obtener observaciones desde vídeo y una integración desplegable en Azure.

## Documentos

- [Plan general](plan-general.md): alcance, arquitectura, fases, entregables y estrategia de Azure.
- [Requisitos funcionales](requisitos-funcionales.md): capacidades verificables del módulo.
- [Historias de usuario](historias-de-usuario.md): necesidades de los consumidores del módulo y criterios de aceptación.
- [Plan de pruebas con servicios reales](plan-pruebas-servicios-reales.md): orden de despliegue, integración Azure, vídeo, modelos e interfaz mínima de comprobación.
- [Evidencias técnicas](evidencias/README.md): implementación, criterios cubiertos, pruebas y limitaciones de cada historia.

## Fuentes de autoridad

Este plan amplía, pero no reemplaza, los siguientes documentos:

- [Asignación de Persona 1](../plan-de-desarrollo/persona-1-datos-y-vision.md).
- [Formato estándar de eventos](../08-formato-de-eventos.md).
- [Requisitos generales](../03-requisitos.md).
- [Casos de uso](<../06-Casos de Uso — Plataforma de Inteligencia de Partidos con IA.md>).
- [Decisiones tomadas](../07-decisiones-tomadas.md).

Si existe una contradicción, se debe resolver en el documento general correspondiente antes de cambiar el contrato compartido.

## Estado

DV-US-01 a DV-US-13 tienen implementación y evidencia local en distintos niveles. Los recursos Azure, el vídeo permitido y las ejecuciones reales de Roboflow Sports y SoccerNet todavía no están verificados. DV-US-14 a DV-US-22 separan ese trabajo de integración de las capacidades comprobadas con dobles y datos sintéticos.
