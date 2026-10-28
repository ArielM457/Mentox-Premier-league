# Validación y pendientes

## Alcance de esta revisión

Fecha: **28 de octubre de 2026**. Rama de trabajo: `Re-design-frontend`. Base antes de la reorganización: `e6bd85a`. La revisión comprende lectura del código y Git, archivo de documentos, migración de recursos técnicos, actualización de referencias y comprobaciones locales.

No se desplegaron servicios ni se consultó su estado actual en Azure o Supabase. Las comprobaciones históricas de esos entornos permanecen en el archivo anterior y no se presentan como una nueva validación.

## Resultados observados

| Comprobación | Antes | Después |
|---|---|---|
| Suite completa del backend | 485 aprobadas, 12 fallos, 7 omitidas; 44,57 s | 485 aprobadas, los mismos 12 fallos, 7 omitidas; 59,82 s |
| Compilación del frontend | Había compilado tras los cambios de preferencias | Correcta tras reorganizar documentos |
| Lint del frontend | Dos advertencias conocidas tras retirar un import sin uso | Correcto con las mismas dos advertencias de efectos React |
| Comprobación de idiomas | Catálogo existente | 726 claves iguales entre español e inglés |
| Archivo anterior | 158 archivos en `docs/` | 158 archivos en `docs-anteirores/`, SHA-256 conservado para cada uno |
| Recursos técnicos migrados | Dentro de los documentos anteriores | 17 archivos: 12 ejemplos JSON, 2 HTML y 3 resultados de visión; 15 copiados byte a byte y 2 predicciones restauradas a LF para coincidir con sus hashes |
| Requisitos | Catálogo RF/RNF heredado | 110 identificadores únicos conservados |

Las duraciones son observaciones de este equipo, no metas de rendimiento. La verificación de claves de idiomas no es una revisión lingüística completa de las siete traducciones.

## Comandos de referencia

Desde la raíz, con el entorno instalado:

```powershell
uv run --project apps/backend --no-sync pytest apps/backend/tests -q --tb=short
npm run build:frontend
npm run lint:frontend
git diff --check
git check-ignore docs-anteirores/README.md
```

La ejecución de pytest en esta máquina utilizó directamente `apps/backend/.venv/Scripts/python.exe -m pytest`, para no depender del PATH de uv. Los resultados de suite completa se compararon antes y después con los mismos archivos de prueba.

Los ejemplos movidos siguen siendo leídos por `test_analytics_contract_examples.py` y `test_match_experience_api.py`; los HTML, por `test_analytics_demo.py`. Esas pruebas no aparecen entre los fallos de ninguna ejecución.

## Fallos previos que permanecen

| Grupo | Número | Causa observada |
|---|---|---|
| Integración de visión/aceptación/Postman | 10 | Faltan resultados en las rutas predeterminadas `experiments/*/output-real`; hay respuestas 503 y un estado de reproducción incompleto como consecuencia |
| Parsing del adaptador CrewAI | 1 | La importación del paquete real intenta crear almacenamiento bajo `AppData/Local/CrewAI` y falla en el entorno restringido |
| Configuración sin credenciales | 1 | La prueba rechaza cualquier texto `PASSWORD`, aunque `.env.example` solo declara el nombre de variable `SUPABASE_DB_PASSWORD` con un marcador de ejemplo |

Los archivos afectados son `test_integrated_acceptance.py`, `test_integrated_pipeline_api.py`, `test_postman_collection.py`, `test_narrative.py` y `test_transport_configuration.py`. No se han relajado sus assertions para ocultar los errores.

Los tres resultados incluidos ahora en `apps/backend/data/vision/` se verificaron con `IntegratedPipeline`: coinciden en el hash del medio y en los hashes de las entradas de fusión. Esto demuestra coherencia del lote guardado, no una nueva inferencia GPU. La [guía de datos](../funcionamiento/datos-y-vision.md) explica cómo seleccionar ese lote mediante variables, sin cambiar los valores predeterminados de la aplicación.

Después de restaurar LF en las predicciones, una comprobación adicional con `TestClient` y las tres variables `MENTOX_*_ARTIFACT` apuntando al directorio nuevo obtuvo HTTP 200 en `/api/v1/health`, `/api/v1/integration/status` y `/api/v1/integration/timeline?start_ms=0&end_ms=10000`. La consulta de timeline necesita ambos límites; sin ellos responde 422 conforme al contrato. Esta prueba valida la lectura configurada del lote, no la disponibilidad del vídeo ni una inferencia remota. No cambia el resultado registrado de la suite completa con rutas predeterminadas.

## Comprobaciones de la reorganización

- Comparación SHA-256 de cada archivo antes y después del traslado al archivo local.
- Comparación exacta de bytes en ejemplos, HTML e informe de fusión, y comparación del contenido de las dos predicciones al restaurar sus finales de línea LF. Los originales del archivo permanecen intactos.
- Comparación del conjunto de identificadores RF/RNF con el catálogo anterior.
- Revisión de destinos de enlaces Markdown de la nueva documentación y los índices externos actualizados.
- Revisión de rutas de exportadores, pruebas, Docker, preflight e instrucciones de agentes para que no necesiten `docs-anteirores/`.
- Confirmación de que Git ignora el archivo local y de que los artefactos técnicos nuevos se pueden versionar.

No se construyeron imágenes Docker ni se ejecutaron los experimentos de modelos durante esta revisión. Los cambios de contexto de construcción necesitan esa comprobación en el entorno de entrega.

## Criterios de evaluación conservados

La documentación anterior registra cinco criterios del reto, cada uno con peso del 20 %. Son criterios de evaluación, no una puntuación obtenida:

| Criterio | Evidencia que debe presentarse |
|---|---|
| Implementación tecnológica | Contratos, separación de capas, cálculos reproducibles, pruebas y ejecución documentada |
| Agentes e innovación | Tarea concreta de cada etapa, evidencia usada, fallos controlados y valor de IA frente a plantillas |
| Impacto y aplicación | Usuario, caso de uso, latencia medida y pasos necesarios para transmisión real |
| Experiencia y presentación | Reproducción, preferencias, explicación de un momento y resumen desde el mismo flujo |
| Ajuste a la categoría | Las cinco etapas del pipeline y trazabilidad hasta una salida personalizada |

## Pendientes por prioridad

1. **Estabilizar pruebas de integración:** preparar artefactos por configuración reproducible, aislar almacenamiento de CrewAI y ajustar la comprobación de credenciales para analizar valores sin confundir nombres de variables con secretos.
2. **Verificar operación remota:** construcción de imágenes, migraciones, permisos, redes, modelos realmente seleccionados, SSE, workers y almacenamiento.
3. **Completar agentes:** conectar ejecutores tras el despacho, evaluar gateway semántico y resolver investigación/aprobación de fuentes previas y resúmenes editoriales avanzados.
4. **Cerrar datos y visión:** inferencia por modelo y medio autorizado, conversión validada a eventos, identificación fiable y métricas que requieren seguimiento real.
5. **Preparar producción:** idempotencia durable, autorización de usuarios, varias réplicas, moderación distribuida, recuperación y objetivos medidos de latencia/coste.
6. **Revisar experiencia:** todos los idiomas, teclado/lectores de pantalla, dispositivos y proveedores remotos.

Cada cierre debe registrarse en [evidencias](evidencias/README.md) y actualizar la especificación del módulo. Los porcentajes estimados de documentos antiguos no se usan como medida actual de avance.
