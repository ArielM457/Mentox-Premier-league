# **Documentación del proyecto**

Este proyecto nace de un reto de hackathon. La solución debe convertir eventos sintéticos de fútbol en información explicable para una transmisión en directo y en experiencias personalizadas para distintos aficionados.

La documentación distingue el alcance del reto, las decisiones del equipo y lo que ya existe en el repositorio. La ingesta sintética, el estado calculado, la analítica y la narrativa tienen módulos propios. La experiencia completa del partido todavía debe conectar esos módulos con la interfaz.

## **Documentos**

- [Objetivos y alcance](01-objetivos-y-alcance.md): qué pide el reto, qué proponemos construir y qué sigue abierto.
- [Responsabilidades del sistema](02-responsabilidades.md): tareas de cada parte del programa y límites entre ellas.
- [Análisis de requisitos](03-requisitos.md): requisitos pequeños y verificables, con prioridad inicial.
- [Casos de uso](06-Casos%20de%20Uso%20%E2%80%94%20Plataforma%20de%20Inteligencia%20de%20Partidos%20con%20IA.md): usuarios y recorridos concretos que complementan los requisitos.
- [Evaluación y evidencias](04-evaluacion.md): cómo demostrar los cinco criterios de la rúbrica.
- [Decisiones tomadas](07-decisiones-tomadas.md): tecnologías, arquitectura, agentes, datos e idiomas acordados.
- [Formato de eventos](08-formato-de-eventos.md): contrato inicial para eventos y sincronización con vídeo.
- [Investigación de métricas y herramientas](09-investigacion-metricas-y-herramientas.md): opciones compatibles con Python y límites de los datos.
- [Equipo de agentes](10-arquitectura-agentes.md): responsabilidades, autonomía, verificación y revisión antes de publicar.
- [Plan de implementación de agentes por eventos](11-plan-implementacion-agentes-eventos.md): filtro, orquestación, simulación, resúmenes, escalado y pruebas de disponibilidad.
- [Política de modelos de IA](12-politica-modelos-ia.md): asignación de modelos por demanda, búsqueda web, embeddings y criterios para cambiar de modelo.
- [Plan de desarrollo](plan-de-desarrollo/README.md): reparto entre cuatro personas de programación y una de UX/UI, con contratos para trabajar en paralelo.
- [Detalle de datos y visión](persona-1-datos-y-vision/README.md): plan, requisitos e historias de usuario de Persona 1, incluida la integración reproducible con Azure.
- [Detalle de estado y analítica](persona-2-estado-y-analitica/README.md): estado del partido, catálogo de métricas, patrones, motor de atención, modelos de valor e integración con Azure de Persona 2.
- [Decisiones pendientes](05-decisiones-pendientes.md): elecciones que aún necesitan datos o acuerdos del equipo.

## **Cómo leer el estado de cada punto**

Un requisito del reto viene del texto compartido por el usuario. Una propuesta inicial es una forma de cumplirlo que aún puede cambiar. Una decisión pendiente no debe aparecer como si ya estuviera resuelta.
