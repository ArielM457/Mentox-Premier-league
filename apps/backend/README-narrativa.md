# **Módulo de agentes y narrativa**

El módulo recibe `MatchSnapshot v1`, `InsightCandidate v1` y preferencias. Entrega `NarrativeOutcome` con un `NarrativeDraft v1` cuando hay evidencia suficiente y un registro de la decisión. La persona 4 puede llamar a `NarrativeService` desde su API y guardar ese registro. El módulo no modifica el estado del partido ni publica mensajes.

Antes de la narrativa, el módulo de enrutamiento recibe una ventana de `MatchEvent 1.0`. El servicio filtro calcula cambios de métricas, descarta duplicados conocidos y separa eventos de solo métricas, momentos candidatos, peligro inmediato, tiempos muertos y resúmenes. Solo las rutas relevantes producen `AgentRequest v1` y `AgentDispatch v1`.

## **Preparación**

Desde la raíz del repositorio, instala el backend y las herramientas de prueba:

```powershell
python -m pip install -e '.\apps\backend[dev]'
```

Para usar CrewAI con Azure OpenAI, instala también la dependencia opcional:

```powershell
python -m pip install -e '.\apps\backend[agents]'
```

Configura `AZURE_OPENAI_ENDPOINT` con la dirección HTTPS base del recurso, sin la ruta del despliegue, `AZURE_OPENAI_DEPLOYMENT` con el nombre exacto del despliegue y `AZURE_OPENAI_API_KEY` en el entorno. `AZURE_OPENAI_API_VERSION` es opcional y usa `2024-06-01` si no se establece. No guardes la clave en el repositorio. El adaptador entrega esas variables a la integración nativa de CrewAI con Azure.

## **Prueba local**

Ejecuta el partido sintético sin conexión a Azure:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
python -m match_intelligence.application.narrative.demo apps/backend/tests/fixtures/narrative_match.json --language es --mode casual
python -m match_intelligence.application.narrative.demo apps/backend/tests/fixtures/narrative_match.json --language en --mode analyst --level advanced
python -m pytest apps/backend/tests/test_narrative.py -q
```

Para probar el mismo partido con CrewAI, añade `--provider azure` al primer comando. Cada llamada del modelo tiene un límite de 20 segundos sin reintentos. El registro indica el tiempo total y, cuando CrewAI completa las tareas, el tiempo del observador, analista, narrador y verificador. Si un agente falla o propone un hecho desconocido, el servicio devuelve la decisión y no entrega un borrador publicable. Esta ejecución consume el despliegue de Azure y requiere credenciales válidas.

## **Contrato para integrar**

`NarrativeService.create_live` recibe un `NarrativeRequest`. `answer` recibe una pregunta con estado y candidatos. `summarize` requiere confirmar que terminó el partido y devuelve un borrador final con `editorial_status` igual a `pending`. `resolve_report` recibe el borrador original, su candidato y el motivo del reporte; devuelve confirmación, evidencia insuficiente o una corrección vinculada al original.

La API expone estas funciones en `/api/v1/narratives/live`, `/questions`, `/summaries` y `/reports/resolve`. Las tres primeras rutas admiten `?provider=fixture` para probarlas sin Azure. Sin ese parámetro, usan Azure OpenAI. La [colección de Postman](../../postman/README.md) incluye peticiones y comprobaciones para todas las rutas HTTP actuales.

La API también expone `/api/v1/agent-routing/evaluate`. Esta operación es reproducible y no usa Azure. Recibe eventos, una señal de control opcional, identificadores ya procesados y preferencias. Devuelve la decisión del filtro, cambios de métricas, contexto de jugada y un despacho solo cuando corresponde.

Cada afirmación numérica del borrador procede de `facts` o `metrics` y conserva los identificadores de los eventos. CrewAI selecciona hechos y enfoque. El texto público se construye a partir de esos hechos, por lo que una interpretación libre del modelo no aparece sin respaldo. El modo de jugador comunica que no hay novedades cuando los eventos del momento no mencionan al jugador elegido.

La carpeta `tests/fixtures` contiene un partido válido, un candidato con datos opcionales ausentes, uno inválido y tres ejemplos de `NarrativeDraft v1`. El partido válido contiene presión, recuperación, tiro y gol como hechos derivados de eventos sintéticos. Son ejemplos de contrato, no un motor de cálculo de métricas ni una reproducción de vídeo.

`agent-routing-scenarios.json` añade seis casos para el filtro. La implementación actual procesa cada petición sin guardar estado local. El cliente debe enviar `existing_event_ids` para evitar reprocesar eventos conocidos. El almacenamiento durable, el canal de eventos y GPT-4.1 mini en el orquestador todavía están pendientes.

La asignación propuesta para cada tarea está en [política de modelos de IA](../../docs/12-politica-modelos-ia.md). La configuración actual usa un solo despliegue de Azure OpenAI y deberá separarse al implementar el orquestador y los trabajadores especializados.

La aprobación editorial y la publicación pertenecen al módulo de la persona 4. `NarrativeDraft.publishable` devuelve falso para un resumen final pendiente. El módulo tampoco conoce aún el endpoint ni el nombre del despliegue reales, así que la ejecución con Azure y su tiempo de respuesta deben comprobarse con esa configuración.
