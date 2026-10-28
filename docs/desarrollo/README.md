# Desarrollo con Spec Driven Design

Este directorio organiza el desarrollo existente por especificaciones. Es una reconstrucción del código y los requisitos disponibles; no afirma que todo el trabajo histórico se hiciera siguiendo este método.

## Flujo de trabajo

1. **Especificación:** definir problema, entradas, resultados y criterios de aceptación.
2. **Diseño:** elegir contratos, componentes, dependencias y manejo de fallos.
3. **Tareas:** identificar el código ya implementado y el trabajo pendiente.
4. **Validación:** ejecutar pruebas y registrar comandos, resultados y límites.

Cada documento de módulo incluye esas cuatro partes. Para cambios futuros, actualizar la especificación antes de implementar una conducta nueva y adjuntar evidencia después de verificarla.

## Documentos comunes

| Documento | Uso |
|---|---|
| [Requisitos](requisitos.md) | Catálogo RF/RNF heredado, con prioridades y aceptación; conserva sus identificadores |
| [Decisiones](decisiones.md) | Tecnologías y reglas de implementación vigentes |
| [Contratos](contratos.md) | Formatos intercambiados y fuentes de verdad en código |
| [Validación](validacion.md) | Resultados de esta reorganización, fallos previos y pendientes |
| [Evidencias](evidencias/README.md) | Cómo registrar futuras comprobaciones reproducibles |

## Especificaciones por módulo

| Orden | Especificación | Dependencias principales |
|---|---|---|
| 01 | [Datos y visión](01-datos-y-vision.md) | Metadatos, eventos y permisos del material |
| 02 | [Estado y analítica](02-estado-y-analitica.md) | Datos validados y seguimiento disponible |
| 03 | [Agentes y narrativa](03-agentes-y-narrativa.md) | Candidatos y métricas trazables |
| 04 | [API y experiencia](04-api-y-experiencia.md) | Puertos analíticos/narrativos y contratos HTTP |
| 05 | [Editorial y comunidad](05-editorial-y-comunidad.md) | Borradores, sesiones, moderación y persistencia opcional |
| 06 | [Integración y despliegue](06-integracion-y-despliegue.md) | Configuración, contenedores, servicios y credenciales |

Las listas de tareas distinguen código existente de validación pendiente. Una casilla marcada indica una pieza localizada en el repositorio; el resultado de pruebas y la disponibilidad de servicios se consultan por separado.
