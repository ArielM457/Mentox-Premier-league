# Plan de desarrollo: 1 al 27 de octubre de 2026

## Cómo leer este plan

Este plan reconstruye el trabajo necesario para llegar al proyecto existente al 27 de octubre. Se redactó el 28: **no es un registro diario escrito durante la ejecución**. Las fechas con commits indican evidencia del repositorio; el resto son una distribución retrospectiva del trabajo y no una afirmación sobre lo que hizo cada persona ese día.

Los commits se pueden consultar con `git show <hash>`. No hay commits de la rama revisada que confirmen actividades del 1 al 5 de octubre. El primer bloque documental confirmado es del día 6. Una fecha de commit demuestra un cambio registrado, no su despliegue ni su aceptación por el equipo.

## Plan diario y entregables

| Día | Trabajo organizado | Entregable esperado o existente | Evidencia temporal |
|---|---|---|---|
| 1 | Comprender el reto, usuarios y cinco etapas | Contexto y problema de producto | Distribución retrospectiva, sin commit que confirme el día |
| 2 | Delimitar datos sintéticos, permisos y alcance | Límites de datos e integraciones | Distribución retrospectiva |
| 3 | Descomponer requisitos funcionales y de calidad | Catálogo RF/RNF y prioridades | Distribución retrospectiva |
| 4 | Definir contratos y separación entre módulos | Metadatos, eventos, estado y salidas | Distribución retrospectiva |
| 5 | Repartir responsabilidades y preparar la demo | Plan de áreas y recorrido mínimo | Distribución retrospectiva |
| 6 | Consolidar documentación, casos de uso y estructura inicial | Primera base documental versionada | `fc71627`, `508f399`, `376ae5c` |
| 7 | Preparar generadores, validación y pruebas de entrada | Datos de aceptación repetibles | Etapa reconstruida; entrega registrada el 9 |
| 8 | Integrar contratos, reproducción y puertos | Base de ingesta y conexiones entre áreas | Etapa reconstruida; entrega registrada el 9 |
| 9 | Entregar datos, estado/analítica y primera API/interfaz | Eventos validados, sesión, SSE y UI funcional | `050add0`, `3ce1a86`, `e187deb`, `e631e4c`, `a178272` |
| 10 | Refinar selección, evidencia y flujo narrativo | Solicitudes pequeñas y contratos de narración | Etapa reconstruida; integración registrada el 11 |
| 11 | Consolidar enrutamiento, narrativa y analítica de seguimiento | Filtro, catálogo, despacho y pruebas | `74264b2`, `e084ef2`, `8573c89`, `5afdeea` |
| 12 | Preparar integración entre áreas y revisar simulaciones | Adaptación de observaciones a analítica | Etapa reconstruida; merge registrado el 13 |
| 13 | Integrar analítica y narrativa, separar datos de prueba | Módulos unidos y fixtures fuera de producción | `2643304`, `10ebc1c`, `520ed13`, `320a7f8` |
| 14 | Aplicar diseño a la experiencia React y conectar sus pantallas | Componentes, navegación, preferencias e interfaz visual | `1e01b02`, `7623cee`, `2800894`, `fbf452a` |
| 15 | Revisar recorrido completo y sincronización | Reproducción y momentos con fuentes | Distribución retrospectiva, sin entrega fechada confirmada |
| 16 | Preparar persistencia e integración operativa | Esquema y adaptadores de datos | Etapa reconstruida; integración registrada el 18 |
| 17 | Preparar infraestructura e imágenes | Definiciones de despliegue | Etapa reconstruida; scripts registrados el 18 |
| 18 | Conectar analítica real, Supabase y Container Apps | API con motor seleccionable y despliegue automatizado | `241a1a9`, `ed4afcf`, `7b4fad9` |
| 19 | Corregir provisión y validar simulaciones de frontend | Mayor cobertura del recorrido local | `a0536dd`, `cdbe4f6` |
| 20 | Preparar adaptadores de visión y formatos de observación | Separación entre seguimiento, acciones y fusión | Etapa reconstruida; integración registrada el 23 |
| 21 | Revisar sincronización del vídeo y evidencias de modelos | Observaciones con procedencia y tiempo | Etapa reconstruida |
| 22 | Preparar unión de visión, rutas y experiencia | Contratos de integración revisados | Etapa reconstruida |
| 23 | Consolidar integración de visión y transporte | Pipeline integrado y resultados de experimentos | `e7d1d46`, `b3fdd44`, `da19506` |
| 24 | Preparar lectura de resultados y despliegue de integración | Conexión de modelos con vistas de producto | Etapa reconstruida; cambios registrados el 25 |
| 25 | Integrar resultados de visión, analítica y frontend; ajustar Azure | Vista de visión, explicación del momento y guía de operación | `81f92f3`, `a5bf39a`, `78cf10c`, `5d2b136` |
| 26 | Añadir comunidad y moderación, integrar captura y mejorar UI | Votos/chat, límites de captura, accesibilidad y ajustes del centro | `e260247`, `c1d569f`, `b7d499d`, `bdc42b4`, `f79dffb` |
| 27 | Consolidar rediseño y comentarios; revisar alcance de la demo | Frontend conectado y correcciones finales del intervalo | `672ad72`, `cf5b90b`; existen documentos de revisión fechados el 27 |

## Dependencias del plan

1. Los datos y sus contratos habilitan los cálculos; las métricas habilitan los candidatos con evidencia.
2. Los candidatos y preferencias habilitan la narrativa; las salidas estructuradas habilitan la interfaz.
3. Persistencia y transporte remoto se conectan por adaptadores, manteniendo una demo local sin servicios externos.
4. Los experimentos de visión requieren vídeo permitido y resultados compatibles antes de integrarse al producto.
5. La revisión editorial y la observabilidad se verifican antes de afirmar publicación segura o disponibilidad de producción.

## Estado al cerrar el 27

La base registrada incluye API, experiencia React, escenarios sintéticos, motor de analítica, filtro y despacho, proveedores narrativos, previa táctica, revisión editorial, comunidad e infraestructura. No se considera terminado automáticamente todo el catálogo RF/RNF: faltan validaciones reales de modelos, infraestructura y algunos flujos avanzados.

## Cambios posteriores al intervalo

El commit `6f8f118` y las tarjetas de preferencias del commit `e6bd85a` tienen fecha del **28 de octubre** y no se incluyen como trabajo completado el 27. La reorganización de documentos también es posterior. Su estado está reflejado en las [especificaciones actuales](desarrollo/README.md) y en [validación](desarrollo/validacion.md).
