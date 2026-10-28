# Documentación de The Prime Moment

Documentación consolidada el **28 de octubre de 2026** sobre la rama `Re-design-frontend`. Describe el código disponible y distingue las funciones locales, las integraciones configurables y el trabajo pendiente.

## Por dónde empezar

| Necesidad | Documento |
|---|---|
| Entender el producto, su alcance y su estado | [Contexto del proyecto](contexto-del-proyecto.md) |
| Consultar el desarrollo del 1 al 27 de octubre | [Plan y reconstrucción de octubre](plan-octubre.md) |
| Revisar especificaciones, diseño, tareas y pruebas por módulo | [Desarrollo con Spec Driven Design](desarrollo/README.md) |
| Entender y operar el programa | [Documentación de funcionamiento](funcionamiento/README.md) |
| Instalar y ejecutar backend y frontend | [Ejecución local](funcionamiento/ejecucion-local.md) |
| Saber qué se ha comprobado y qué falta | [Validación y pendientes](desarrollo/validacion.md) |

## Organización

```text
docs/
  README.md
  contexto-del-proyecto.md
  plan-octubre.md
  desarrollo/
    README.md
    requisitos.md
    decisiones.md
    contratos.md
    01-datos-y-vision.md
    02-estado-y-analitica.md
    03-agentes-y-narrativa.md
    04-api-y-experiencia.md
    05-editorial-y-comunidad.md
    06-integracion-y-despliegue.md
    validacion.md
    evidencias/README.md
  funcionamiento/
    README.md
    arquitectura.md
    flujo-del-programa.md
    agentes.md
    datos-y-vision.md
    ejecucion-local.md
    despliegue.md
```

## Archivo anterior

Los 158 archivos que estaban en `docs` se conservaron en `docs-anteirores/`, en la raíz del repositorio. Se respeta ese nombre solicitado. La carpeta está ignorada por Git y es un archivo local; los siguientes clones no la recibirán. Las versiones anteriores también siguen disponibles en el historial de Git.

La documentación vigente no depende de ese archivo. Los JSON que consumen las pruebas están ahora en `apps/backend/tests/fixtures/contracts/`, la demo HTML en `experiments/analytics-demo/` y los tres resultados de visión que copia Docker en `apps/backend/data/vision/`. Son recursos técnicos versionados, separados de los documentos archivados.

## Cómo mantener estos documentos

Para cada cambio, actualizar la especificación del módulo y registrar su validación. «Implementado» significa que existe código; «verificado» requiere un comando y su resultado; «configurable» requiere infraestructura o credenciales que no vienen con el repositorio. Una propuesta de la documentación histórica no se considera una función entregada.
