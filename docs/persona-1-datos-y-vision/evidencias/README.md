# Evidencias técnicas de las historias de usuario

Esta carpeta conserva la evidencia de implementación de cada historia de Persona 1. Una historia no se marca como terminada únicamente porque exista código: debe demostrar cada criterio de aceptación con una prueba o una comprobación reproducible.

## Evidencias disponibles

| Historia | Estado | Evidencia |
|---|---|---|
| DV-US-01 · Generar el partido de aceptación | Implementada y verificada localmente | [DV-US-01](DV-US-01.md) |
| DV-US-02 · Reproducir el flujo | Implementada y verificada localmente | [DV-US-02](DV-US-02.md) |
| DV-US-03 · Recibir únicamente eventos válidos | Implementada y verificada localmente | [DV-US-03](DV-US-03.md) |
| DV-US-04 · Evitar el doble conteo | Núcleo y memoria verificados localmente; Event Hubs pendiente | [DV-US-04](DV-US-04.md) |
| DV-US-05 · Reconocer un evento tardío | Detección verificada; reconstrucción pendiente de acuerdo con Persona 2 | [DV-US-05](DV-US-05.md) |
| DV-US-06 · Desplegar recursos en una cuenta propia | Bicep verificado localmente; despliegue Azure pendiente | [DV-US-06](DV-US-06.md) |
| DV-US-07 · Publicar eventos en Event Hubs | Adaptadores verificados localmente; integración Azure pendiente | [DV-US-07](DV-US-07.md) |
| DV-US-08 · Cambiar entre transporte local y Azure | Selección y equivalencia verificadas localmente; Azure real pendiente | [DV-US-08](DV-US-08.md) |
| DV-US-09 · Conservar artefactos autorizados | Contrato y adaptador verificados localmente; Azure real pendiente | [DV-US-09](DV-US-09.md) |
| DV-US-10 · Sincronizar eventos con vídeo | Coordinación temporal verificada localmente; vídeo e interfaz pendientes | [DV-US-10](DV-US-10.md) |
| DV-US-11 · Evaluar modelos sin comprometer el MVP | Evaluador verificado; vídeo y ejecuciones reales pendientes | [DV-US-11](DV-US-11.md) |
| DV-US-12 · No inventar identidad de jugadores | Regla y pruebas negativas verificadas localmente; asociación real pendiente | [DV-US-12](DV-US-12.md) |
| DV-US-13 · Fusionar observaciones con trazabilidad | Política y servicio verificados localmente; vídeo real pendiente | [DV-US-13](DV-US-13.md) |

DV-US-14 a DV-US-22 están pendientes y no tienen evidencia de ejecución. Sus criterios y orden se encuentran en [historias de usuario](../historias-de-usuario.md) y en el [plan de pruebas con servicios reales](../plan-pruebas-servicios-reales.md). La evidencia se creará al ejecutar cada historia; no se generarán informes vacíos que puedan confundirse con resultados.

## Contenido obligatorio

Cada evidencia debe registrar:

1. Estado y fecha de la última verificación.
2. Alcance implementado y exclusiones.
3. Entradas y resultados.
4. Archivos creados o modificados.
5. Decisiones técnicas relevantes.
6. Matriz entre criterios de aceptación, implementación y pruebas.
7. Comandos exactos para reproducir la verificación.
8. Versiones del entorno utilizado.
9. Resultado de las pruebas.
10. Limitaciones, riesgos y trabajo pendiente.
11. Dependencias sobre otros módulos o decisiones del equipo.

## Estados permitidos

- **Pendiente:** todavía no comenzó la implementación.
- **En progreso:** existe trabajo parcial, pero falta al menos un criterio.
- **Implementada, pendiente de verificación:** existe código, pero no hay evidencia suficiente.
- **Verificada localmente:** todos los criterios de la historia pasaron en el entorno local documentado.
- **Verificada en integración:** también pasó con sus servicios o consumidores reales.
- **Bloqueada:** no puede continuar por una dependencia explícita.

La evidencia debe distinguir las pruebas locales de las pruebas con Azure, vídeo o modelos externos. Una prueba local no demuestra comportamiento en una transmisión real.

## Plantilla

Copiar [PLANTILLA.md](PLANTILLA.md) al comenzar una historia nueva. El nombre debe conservar el identificador, por ejemplo `DV-US-03.md`.
