# **Diagnóstico del proyecto frente a los requerimientos del hackathon**

Fecha de revisión: 27 de octubre de 2026  
Proyecto: The Prime Moment  
Rama revisada: `persona-2/estado-analitica`  
Commit base: `e278cac39e9ca9a9434700830e4957661c2b2338`

## **1. Alcance y método**

Hicimos una auditoría de lectura y ejecución local. No creamos contenedores, no desplegamos recursos y no modificamos servicios de Azure.

La revisión incluyó:

- lectura del backend, frontend, pruebas, Dockerfiles, Compose, Bicep, scripts y documentación;
- ejecución de la suite de pruebas del backend;
- ejecución separada de las pruebas del núcleo;
- lint y compilación del frontend;
- arranque local del backend con `ANALYTICS_ENGINE=persona2`, `NARRATIVE_PROVIDER=provisional` y `MATCH_SOURCE=synthetic`;
- arranque local del frontend con Vite;
- comprobaciones de solo lectura en Azure CLI;
- búsqueda de mocks, fixtures, fallbacks, plantillas, datos fijos, aleatoriedad y posibles secretos.

El árbol no estaba limpio al iniciar. Ya existían cambios en:

- `apps/frontend/src/screens/Editorial.jsx`;
- `apps/frontend/src/screens/MatchCenter.jsx`;
- `apps/frontend/src/styles/ux.css`;
- `docs/persona-4-api-y-frontend/README.md`;
- `tmp-match-player-mobile.png`;
- `tmp-match-player.png`.

No modificamos esos archivos.

## **2. Resumen ejecutivo**

El proyecto tiene un núcleo funcional y bien probado para eventos sintéticos, analítica determinista, selección de momentos, personalización y salidas para pantalla. Sin embargo, la experiencia que funciona sin credenciales depende de narración por plantillas, seguimiento simulado y escenarios sintéticos. La ruta real de CrewAI y Azure OpenAI existe en código, pero no encontramos un despliegue de modelo activo en la suscripción accesible. La visión tiene servicios de inferencia reales en código y un servicio SoccerNet desplegado, pero está detenido y sus resultados no completan todavía el flujo automático hasta `MatchEvent`.

Estimación de avance:

- avance funcional local total: aproximadamente 62 %;
- parte respaldada por cálculos deterministas y flujos reales locales: aproximadamente 39 puntos porcentuales;
- parte que funciona mediante plantillas, fixtures, mocks o datos sintéticos: aproximadamente 23 puntos porcentuales;
- parte ausente, desconectada o no verificable: aproximadamente 38 %.

Esta estimación pondera por igual las cinco etapas del pipeline y las ocho funcionalidades pedidas. No representa porcentaje de líneas de código.

### **Cinco hallazgos principales**

**1.** La analítica real sí existe y funciona localmente. Con `ANALYTICS_ENGINE=persona2`, la API produjo 255 métricas y patrones como control, impulso, caos, presión sostenida y progresión rápida. Las fórmulas están separadas del LLM. Evidencia: `apps/backend/src/match_intelligence/domain/analytics/statistics.py:146-149`, `apps/backend/src/match_intelligence/domain/analytics/indicators.py:32-51` y `apps/backend/src/match_intelligence/application/analytics/pipeline.py:257-289`.

**2.** La narración predeterminada no usa IA. `NARRATIVE_PROVIDER` usa `provisional` por defecto y `ProvisionalNarrative` declara que trabaja con plantillas. Incluso en la ruta Azure, el LLM selecciona evidencia, pero el texto final en vivo se reemplaza por el texto de la plantilla local. El resumen y la verificación también siguen siendo provisionales. Evidencia: `apps/backend/src/match_intelligence/adapters/http/registry.py:152-168`, `apps/backend/src/match_intelligence/adapters/provisional/narrative.py:1-5` y `apps/backend/src/match_intelligence/adapters/agents/narrative_port.py:155-170,234-251`.

**3.** La visión automática es parcial. Los servicios GPU cargan modelos reales y ejecutan inferencia, pero la integración local falla porque faltan tres artefactos. La fusión se presenta como candidatos experimentales y no como eventos publicados. En Azure encontramos SoccerNet TeamSpotting desplegado, pero con estado `Stopped`. Evidencia: `deploy/azure-soccernet-teamspotting/app.py:52-60,144-154,187-205`, `deploy/azure-roboflow-suite/app.py:84-116,136-149` y la salida de Azure CLI registrada en la sección 9.

**4.** No existe el índice de dificultad del pase. Sí se calculan precisión y distancia de pase, pero la búsqueda en `apps/backend/src`, `apps/frontend/src` y las pruebas no encontró `pass_difficulty`, `difficulty_index` ni una fórmula equivalente. Evidencia positiva de lo existente: `apps/backend/src/match_intelligence/domain/analytics/statistics.py:146-149,178-225`.

**5.** La suite completa no pasa. El resultado fue `471 passed, 11 failed, 7 skipped`. Diez fallos dependen de artefactos de visión ausentes o de rutas integradas que los necesitan. El fallo restante proviene de una prueba que rechaza la palabra `PASSWORD`, aunque `.env.example` contiene el nombre de variable `SUPABASE_DB_PASSWORD` con un valor de ejemplo. Al excluir solo los cuatro archivos de integración afectados, el núcleo terminó con `405 passed, 7 skipped`.

## **3. Mapa del proyecto**

### **Estructura y stack**

| Área | Tecnología | Responsabilidad | Evidencia |
|---|---|---|---|
| `apps/backend` | Python 3.12, FastAPI, Uvicorn, Pydantic | API, reproducción, analítica, narrativa, persistencia y transporte | `apps/backend/pyproject.toml:1-27`, `apps/backend/src/match_intelligence/main.py:24-40` |
| `apps/frontend` | React 19, Vite 8, JavaScript | Experiencia del partido, preferencias, overlays, seguimiento y revisión | `apps/frontend/package.json:1-21` |
| `apps/backend/src/.../domain/analytics` | Python puro | Estado, estadísticas, patrones, indicadores y seguimiento | `apps/backend/src/match_intelligence/domain/analytics/__init__.py:1-4` |
| `apps/backend/src/.../application/narrative` | Python y contratos Pydantic | Selección de evidencia, preguntas, resúmenes y revisión | `apps/backend/src/match_intelligence/application/narrative/service.py:149-214,230-346` |
| `apps/backend/src/.../adapters/agents` | CrewAI opcional | Cuatro agentes sobre Azure OpenAI | `apps/backend/src/match_intelligence/adapters/agents/crewai_gateway.py:45-78,101-190` |
| `apps/backend/src/.../adapters/messaging` | Azure Event Hubs y Service Bus | Transporte de eventos, métricas y eventos importantes | `apps/backend/src/match_intelligence/application/routing/pipeline.py:13-78` |
| `deploy` | FastAPI, PyTorch, Ultralytics y modelos externos | Servicios de inferencia GPU y generador MESSI | `deploy/azure-roboflow-suite/app.py:17-27`, `deploy/azure-soccernet-teamspotting/app.py:21-34` |
| `infra/azure` | Bicep y scripts Azure CLI | Event Hubs, Service Bus, Storage, Container Apps, ACR e identidades | `infra/azure/main.bicep:37-228`, `infra/azure/analytics-platform.bicep:101-487` |
| `supabase` e `infra/supabase` | SQL | Persistencia de partidos, eventos, momentos y analítica | `supabase/migrations`, `infra/supabase/migrations` |
| `experiments` | Python, Dockerfiles y artefactos externos | Diagnósticos y adaptaciones de modelos de visión | `experiments/video_sync_diagnostic`, `experiments/soccernet-gamestate` |

### **Cómo se conectan**

**1.** React usa rutas relativas bajo `/api/v1`. Envía idioma, modo, nivel, club y jugador favorito. Evidencia: `apps/frontend/src/api/client.js:12-29,52-77`.

**2.** FastAPI carga tres partidos sintéticos en memoria cuando no usa Supabase. Evidencia: `apps/backend/src/match_intelligence/adapters/http/registry.py:24-35,152-185`.

**3.** La sesión aplica eventos según el tiempo de vídeo, calcula el estado y selecciona candidatos. La salida se convierte en `OverlayMessage` con tiempo de partido, tiempo de vídeo, duración, prioridad, idioma, modo y eventos de origen. Evidencia: `apps/backend/src/match_intelligence/domain/presentation.py:134-167`.

**4.** El filtro clasifica eventos en `metrics_only`, `moment_candidate`, `danger_immediate`, `dead_ball_context`, `recap` o `rejected`. Evidencia: `apps/backend/src/match_intelligence/application/routing/filter.py:31-68`.

**5.** El transporte local usa memoria. La configuración puede cambiar a Event Hubs y Service Bus mediante variables de entorno. Evidencia: `apps/backend/src/match_intelligence/adapters/messaging/configuration.py:20-93` y `apps/backend/src/match_intelligence/adapters/messaging/routing_transport.py:47-109`.

**6.** La captura de visión envía fotogramas por HTTP al servicio Roboflow Suite, recibe inferencias y publica observaciones. Sin endpoint o clave falla de forma explícita. Evidencia: `apps/backend/src/match_intelligence/application/live_vision_capture.py:45-104,133-143,224-259`.

### **Infraestructura y automatización**

- Los cinco archivos Bicep principales compilaron correctamente con `az bicep build --stdout`.
- No existe una carpeta `.github`; no encontramos pipeline CI/CD versionado.
- `compose.integration.yml` define solo el diagnóstico integrado `mentox-integration`, con puerto `8018`, healthcheck y volúmenes de solo lectura.
- No ejecutamos Compose ni Docker por instrucción expresa de esta auditoría.
- La persistencia usa Supabase de forma opcional. Si la base no responde, la API registra el problema y carga partidos sintéticos. Evidencia: `apps/backend/src/match_intelligence/adapters/http/registry.py:122-149`.

## **4. Resultado de las ejecuciones**

### **Backend**

Comando de pruebas completas:

```powershell
uv run --project apps/backend --extra dev pytest apps/backend/tests -q
```

Resultado:

```text
471 passed, 11 failed, 7 skipped, 14 warnings in 66.20s
```

Fallos:

- faltan `experiments/roboflow-sports/output-real/roboflow-sports-predictions.json`;
- falta `experiments/soccernet-teamspotting/output-real/soccernet-predictions.json`;
- falta `experiments/fusion-calibration/output/dv-us-21-report.json`;
- las rutas Postman de integración esperan `200`, pero reciben `503` por esos archivos ausentes;
- una prueba de reproducción intenta leer `position_ms` después de una respuesta de error;
- `test_example_configuration_contains_no_credentials` falla porque prohíbe cualquier aparición de `PASSWORD`, incluido el nombre de variable de ejemplo.

Pruebas del núcleo, excluyendo solamente los cuatro archivos afectados:

```text
405 passed, 7 skipped, 14 warnings in 28.20s
```

Las advertencias vienen principalmente de APIs obsoletas de CrewAI y de callbacks que no pueden serializarse para checkpointing.

### **Arranque local del backend**

Configuración usada:

```text
NARRATIVE_PROVIDER=provisional
ANALYTICS_ENGINE=persona2
MATCH_SOURCE=synthetic
```

Resultados:

- `GET /api/v1/health`: `200`, estado `ok`;
- `GET /api/v1/matches`: `200`, tres partidos sintéticos;
- `GET /api/v1/matches/synthetic-analytics-001/state`: `200`, 255 métricas;
- overlays en español, modo analista avanzado: `200`, 33 mensajes;
- overlays en inglés, modo casual simple: `200`, 14 mensajes;
- `GET /api/v1/integration/status`: `503` por el artefacto de fusión ausente.

El cambio de 33 a 14 mensajes prueba que el perfil cambia la selección, no solo el tono. También cambian titulares, explicaciones y duración.

### **Frontend**

Lint:

```text
Sin errores. Dos advertencias react(set-state-in-effect).
i18n: 695 claves iguales en español e inglés.
```

Build:

```text
67 módulos transformados.
dist/index.html: 0.92 kB
dist/assets/index-ChZIbDCZ.css: 177.62 kB
dist/assets/index-JJ0JjNP8.js: 418.48 kB
Build completado en 5.43 s.
```

Arranque:

- Vite quedó listo en 284 ms;
- `GET http://127.0.0.1:8766/` respondió `200`;
- el HTML contiene `id="root"` y la marca The Prime Moment.

Esto prueba que el servidor y los recursos responden. No prueba por sí solo toda la interacción visual en un navegador.

## **5. Auditoría de las cinco etapas del pipeline**

| Etapa | Estado | Evidencia | Qué falta para llegar a completo | Esfuerzo |
|---|---|---|---|---|
| Ingerir eventos sintéticos a medida que ocurren | ✅ Completo y funcional localmente | Contrato en `domain/contracts.py`; SSE incremental en `match_router.py:254-325`; Event Hubs en `azure_event_hubs.py`; tres escenarios con 220 eventos | Probar el mismo flujo con Event Hubs activo y medir latencia | Medio |
| Interpretar en estadísticas, patrones y contexto | ✅ Completo y funcional localmente | Fórmulas en `statistics.py:146-225`; indicadores en `indicators.py:32-51,63-126,193-241`; pipeline en `pipeline.py:257-289` | Activar `persona2` por defecto y completar datos de seguimiento reales | Bajo |
| Explicar por qué importa | 🟡 Parcial | Patrones con evidencia y plantillas explicativas en `provisional/narrative.py:50-140`; CrewAI en `crewai_gateway.py:101-190` | Evitar que la ruta Azure reemplace el texto final por una plantilla; verificar explicaciones reales con modelo desplegado | Medio |
| Traducir a salida para pantalla | ✅ Completo y funcional localmente | `OverlayMessage` en `presentation.py:134-167`; ejecución produjo JSON con timestamp, duración, prioridad y fuentes | Validar contra el contrato real del sistema de transmisión cuando exista | Bajo |
| Personalizar | 🟡 Parcial avanzado | Preferencias en `presentation.py:15-41`; puntuación por perfil en `attention.py:55-71,249-283`; 33 overlays analista frente a 14 casual | Probar de extremo a extremo club y jugador favorito con UI y proveedor Azure; ampliar personalización del resumen real | Medio |

## **6. Auditoría de las ocho funcionalidades**

| Requisito | Estado | Evidencia | Qué falta para llegar a ✅ | Esfuerzo |
|---|---|---|---|---|
| 1. Identificación de jugador y etiquetas con velocidad o distancia por umbral | 🟠 Solo mock o simulado | La cancha muestra etiquetas desde jugadores conocidos en `apps/frontend/src/components/match/Pitch.jsx:39-96`. Los umbrales existen en `tracking.py:40-45,534-595`. El seguimiento sintético se declara mock en `tracking_mock.py:1-24` | Conectar identidad fiable desde vídeo, publicar `TrackingAlert` en la experiencia y mostrar u ocultar los indicadores según los umbrales. Hoy el frontend no consume `top_speed_kmh` ni `distance_covered_m` | Alto |
| 2. Calidad del pase: distancia, precisión y dificultad | 🟡 Parcial | Precisión en `statistics.py:178-196`; distancia en `statistics.py:146-149,199-225` | Diseñar y documentar una fórmula de dificultad con variables, versión y pruebas. No existe una implementación encontrada | Medio |
| 3. Velocidad del balón y del tiro | 🟠 Solo mock o simulado en el flujo disponible | Cálculo real sobre tracking en `tracking.py:383-421`; sin tracking se marca no disponible en `statistics.py:312-317`. La ejecución local devolvió ambas métricas como no disponibles | Alimentar el cálculo con seguimiento real del balón, conectar esos datos a la sesión y mostrarlos en UI | Alto |
| 4. Generación automática desde vídeo | 🟡 Parcial | Roboflow Suite y SoccerNet ejecutan modelos reales en `deploy/.../app.py`; `live_vision_capture.py` llama al endpoint real | Restaurar artefactos locales, encender o desplegar modelos necesarios, fusionar observaciones y producir `MatchEvent` validado. Hoy la fusión publica cero eventos | Alto |
| 5. Narrativas, rendimiento, hitos y resúmenes | 🟠 Solo mock o simulado en la demo predeterminada | Hitos y momentos vienen de analítica real; el texto viene de `ProvisionalNarrative`. El resumen siempre usa fallback en `narrative_port.py:234-243` | Usar el proveedor real para texto final y resúmenes, probar credenciales, latencia, errores y revisión editorial | Alto |
| 6. Explicabilidad de control, caos, presión y ritmo | 🟡 Parcial avanzado | Control y caos tienen fórmulas versionadas en `indicators.py:26-51,63-126,193-241`; el motor detecta presión, control y caos; la salida local mostró esos mensajes | Mejorar la explicación causal, mostrar componentes y límites de evidencia en la UI y validar ritmo como concepto explícito | Medio |
| 7. Dataset sintético realista o ampliado | ✅ Completo para la demo local, con limitaciones | Tres partidos, 220 eventos y once tipos en total. Los escenarios usan semillas y secuencias. Contrato en `docs/08-formato-de-eventos.md` | Validar distribuciones contra una referencia autorizada y ampliar cantidad y variedad. La coherencia actual está probada por reglas, no por comparación estadística externa | Medio |
| 8. Narración multilingüe | 🟠 Solo mock o simulado | Dos idiomas en `presentation.py:15-17`; plantillas ES/EN en `provisional/narrative.py`; ejecución local correcta en ambos idiomas | Generación lingüística real o traducción verificada con modelo activo; criterios editoriales y pruebas humanas de terminología | Medio |

### **Respuestas a las preguntas específicas**

**Indicadores por umbral.** Existen umbrales de 30 km/h para récord de velocidad, incremento de 1 km/h y hitos cada 1 000 metros. Están en `tracking.py:40-45`. La lógica de cruce está en `tracking.py:534-595`. No encontramos conexión de esas alertas con un indicador visible junto a la etiqueta del jugador.

**Dificultad del pase.** No existe fórmula ni campo implementado. Sí existen precisión, distancia media, pase más largo, avance y pases progresivos.

**Origen de las cifras.** Las cifras principales se calculan en Python antes de la narrativa. CrewAI recibe `snapshot` y `candidate` serializados y tiene instrucciones de no inventar estadísticas. Evidencia: `crewai_gateway.py:101-110`. El LLM selecciona índices de hechos, no calcula las métricas.

**Filtro de momentos.** Sí existe. Usa prioridades, umbrales por perfil, enfriamiento de dos minutos, novedad y preferencias. Evidencia: `attention.py:31-71,163-211,233-283`. También existe un filtro anterior que evita llamar agentes para eventos rutinarios: `routing/filter.py:56-67`.

**Control, caos, presión y ritmo.** Control, caos, presión sostenida, cambio de control y progresión rápida están implementados. El ritmo aparece representado por impulso y progresión, pero no encontramos un indicador público llamado explícitamente ritmo de juego.

**Salida JSON para overlays.** Sí. Incluye `clock_ms`, `video_time_ms`, `show_for_ms`, prioridad, idioma, modo, texto y eventos de origen. Evidencia: `presentation.py:134-167`.

**Personalización real.** Sí cambia la selección. El modo analista tiene umbral 35 y el casual 50. El modo jugador da 20 puntos cuando participa el favorito y resta 30 cuando no participa. Club y jugador favorito también suman prioridad. Evidencia: `attention.py:55-71,249-283`. En la prueba local, analista recibió 33 overlays y casual 14.

**Idiomas.** Soporta español e inglés. En el flujo predeterminado no traduce una salida generada: elige plantillas escritas por separado para cada idioma.

**Realismo del dataset.** Los escenarios son deterministas por semilla y contienen secuencias diseñadas. No son aleatoriedad libre. Aun así, no encontramos una validación estadística que demuestre que las distribuciones representan fútbol real.

**Tiempo real.** La API entrega SSE cada 200 ms con un horizonte de un segundo en `match_router.py:61-62,283-325`. Esto es incremental y funciona durante la reproducción. No se midió latencia completa con modelos y Azure, así que no afirmamos tiempo real de producción.

## **7. Tabla de agentes y componentes inteligentes**

| Agente o componente | Tipo | Veredicto | Entrada y salida | Evidencia |
|---|---|---|---|---|
| Observador de evidencia | CrewAI con Azure OpenAI | HÍBRIDO, no verificado contra un modelo activo | Recibe snapshot, candidato y preferencias; devuelve índices de hechos observados | `crewai_gateway.py:101-145`; no hay deployments de modelo en la cuenta Azure consultada |
| Analista de evidencia | CrewAI con Azure OpenAI | HÍBRIDO, no verificado contra un modelo activo | Propone ángulo, límite de evidencia y razón | `crewai_gateway.py:115-152` |
| Selector narrativo | CrewAI con Azure OpenAI | HÍBRIDO | Selecciona hechos y ángulo, pero no escribe la prosa final que usa React | `crewai_gateway.py:123-159`, `narrative_port.py:160-167` |
| Verificador narrativo | CrewAI con Azure OpenAI | HÍBRIDO | Aprueba o rechaza selección; fallback local queda aprobado | `crewai_gateway.py:131-190`, `narrative_port.py:168-183` |
| Narrador provisional | Función con reglas y plantillas | MOCK | Recibe hechos calculados y preferencias; devuelve titulares y explicaciones ES/EN | `provisional/narrative.py:1-5,148-260` |
| Resumidor | Plantilla local en la experiencia | MOCK | Recibe estado y candidatos; arma resumen y cola editorial | `narrative_port.py:234-243` |
| Preguntas sobre el partido | CrewAI opcional con fallback de reglas | HÍBRIDO | Recibe métricas y pregunta; si el modelo no está disponible usa respuesta local | `narrative_port.py:188-232` |
| Personalizador | Política determinista | REAL, no es agente LLM | Ajusta prioridad y selección según perfil, club y jugador | `attention.py:249-283` |
| Clasificador y filtro | Reglas deterministas | REAL, no es agente LLM | Clasifica eventos y evita llamadas innecesarias | `routing/filter.py:31-95` |
| Orquestador de routing | Gateway fixture | MOCK | Copia la tarea refinada hacia el agente solicitado | `routing/orchestrator.py:22-49`, `routing/service.py:18-20` |
| Agente de previa táctica | Reglas y datos fijos | MOCK | Genera formaciones y fotogramas sintéticos reproducibles | `prematch_agent.py:1-5,370-390,433-653` |
| Analítica Persona 2 | Motor determinista | REAL | Convierte eventos en estado, métricas, patrones y candidatos | `analytics/pipeline.py:226-307,310-399` |
| Roboflow Suite | Tres modelos YOLO | REAL en código, no desplegado actualmente | Imagen a detecciones de jugador, balón y campo | `deploy/azure-roboflow-suite/app.py:19-27,84-116,136-149` |
| SoccerNet TeamSpotting | T-DEED | REAL en código y desplegado, pero detenido | Vídeo MP4 a acciones temporales con `prediction_origin=actual_model` | `deploy/azure-soccernet-teamspotting/app.py:52-60,118-154,187-205` |
| Seguimiento de la demo | Generador cinemático con semilla | MOCK | Eventos sintéticos a posiciones, velocidades y distancias simuladas | `tracking_mock.py:1-24,150-255` |

## **8. Contenedores y servicios configurados**

No ejecutamos builds ni runtimes de Docker. La columna `¿corre?` indica ejecución local sin contenedor o estado consultado en Azure.

| Servicio | Base y comando | Función | ¿Corre? | ¿Desplegado? | Observaciones |
|---|---|---|---|---|---|
| API principal | `python:3.12-slim`; `uvicorn ... --port 8000` | API, analítica, narrativa y experiencia | Sí, local sin Docker | No encontrado en Azure accesible | `apps/backend/Dockerfile:6-39` |
| Frontend | Build `node:22-alpine`; runtime `nginx:1.27-alpine` | React y proxy `/api` | Sí, local con Vite | No encontrado | `apps/frontend/Dockerfile:3-16` |
| Worker importante | `python:3.12-slim`; `run_important_event_worker.py` | Consume Service Bus | No ejecutado | No encontrado | `apps/backend/Dockerfile.worker:1-22` |
| Diagnóstico integrado | `python:3.12-slim`; Uvicorn en `8018` | Reproduce artefactos de visión y sincronización | No puede quedar listo por artefactos ausentes | No encontrado | `apps/backend/Dockerfile.integration:1-24`, `compose.integration.yml` |
| Roboflow Player | CUDA 12.8.1; Uvicorn | Detector de jugadores | No ejecutado | No encontrado | `deploy/azure-roboflow-player/Dockerfile`, `app.py:90-145` |
| Roboflow Suite | CUDA 12.8.1; Uvicorn | Jugador, balón y campo | No ejecutado | No encontrado | `deploy/azure-roboflow-suite/Dockerfile`, `app.py:103-149` |
| SoccerNet TeamSpotting | CUDA 12.8.1; Uvicorn | Acciones temporales desde vídeo | No ejecutado localmente | Sí, pero `runningStatus=Stopped` | Imagen `mentox/soccernet-teamspotting:74c810f1e3c2`, revisión `0000003` |
| MESSI generator | `python:3.12-slim`; `generate_batch.py` | Genera partidos sintéticos en GPU | No ejecutado | No encontrado | `deploy/azure-messi-generator/Dockerfile` |
| Event Hubs | Azure Standard | Ingreso, observaciones y métricas | Adaptadores locales probados por tests | No encontrado | Declarado en `infra/azure/main.bicep:37-107` |
| Service Bus | Azure Basic | Eventos importantes durables | No ejecutado | No encontrado | Declarado en `infra/azure/main.bicep:109-136` |
| Blob Storage | Azure Standard LRS | Partidos, vídeos y observaciones | Adaptador probado, servicio no consultado con credenciales de datos | No encontrado | `infra/azure/main.bicep:156-211` |
| Supabase | PostgreSQL externo | Persistencia | No verificado con conexión real | No verificado | La API conserva fallback sintético si falla |
| Azure AI Foundry | Recurso de Cognitive Services y proyecto | Posible alojamiento de modelos | Recurso existe | Sí, sin deployments devueltos | Grupo `rg-premier-agents-rhs8l5fb` |

## **9. Estado verificado en Azure**

La Azure CLI estaba autenticada en una sola suscripción accesible. Usamos únicamente consultas de lectura.

Recursos relacionados encontrados en `rg-premier-agents-rhs8l5fb`:

- Container App `ca-mentox-teamspotting-dev`, aprovisionamiento correcto, estado detenido;
- Container Apps Environment `cae-mentox-vision-dev`;
- Azure AI Foundry `ai-premier-rhs8l5fb`;
- proyecto `football-intelligence`;
- Azure Container Registry `mentoxcdcb5a0d`;
- identidad administrada `id-mentox-teamspotting-dev`.

Detalles del Container App:

```text
provisioningState: Succeeded
runningStatus: Stopped
minReplicas: 1
maxReplicas: 1
targetPort: 8000
latestReadyRevision: ca-mentox-teamspotting-dev--0000003
```

La consulta de deployments del recurso de Azure AI no devolvió modelos. No encontramos en la suscripción accesible los recursos `ca-mentoxp2-api`, frontend, worker, replay, Event Hubs, Service Bus o Storage que describe `docs/14-despliegue-en-azure.md`. Puede tratarse de otra suscripción no disponible en esta sesión o de recursos eliminados. El estado actual es no verificado fuera de la suscripción accesible.

## **10. Calidad y riesgos para la demo**

### **Riesgos críticos**

**1. Artefactos de visión ausentes.** La integración devuelve `503` y provoca diez fallos. Una demo que abra la pestaña de visión o ejecute la colección Postman puede fallar de inmediato.

**2. Narración real no comprobada.** El recurso Azure consultado no tiene deployments visibles. `NARRATIVE_PROVIDER=azure` exige endpoint, deployment y clave, y falla al construir el gateway si faltan. Evidencia: `crewai_gateway.py:47-63`.

**3. La ruta Azure no genera la prosa final en vivo.** Aunque CrewAI responda, `narrative_port.py:162-166` reemplaza titular y explicación por la plantilla local. Esto puede hacer que una demo aparente usar LLM cuando el texto visible no proviene del modelo.

**4. SoccerNet está detenido.** El servicio desplegado no está listo para una demo hasta que se arranque y pase `/health/ready`. No lo arrancamos.

**5. Configuración predeterminada provisional.** `.env.example` propone `NARRATIVE_PROVIDER=provisional` y `ANALYTICS_ENGINE=provisional`. Si el presentador olvida cambiarlos, no se verá el motor real de Persona 2 ni Azure.

### **Riesgos altos**

- no existe índice de dificultad del pase;
- velocidad y distancia no llegan a una etiqueta visible de jugador;
- la identificación nominal desde vídeo no está resuelta;
- la visión produce observaciones y candidatos, pero no un flujo completo de eventos automáticos;
- no existe CI/CD versionado;
- hay advertencias de APIs obsoletas de CrewAI;
- el frontend tiene dos advertencias de actualizaciones de estado dentro de efectos;
- la colección Postman espera éxito donde la API responde correctamente con `503` por dependencia ausente;
- no medimos latencia completa con Azure, GPU y UI.

### **Código muerto y pendientes**

La búsqueda de `TODO`, `FIXME`, `XXX`, `HACK` y `NotImplementedError` no devolvió coincidencias relevantes. El mayor riesgo no está marcado con TODO: son adaptadores provisionales que están integrados como comportamiento predeterminado.

### **Secretos**

- `apps/backend/.env` existe localmente, contiene variables sensibles y está ignorado por `.gitignore`;
- el único archivo de entorno rastreado es `.env.example`;
- la revisión de nombres y asignaciones no encontró un secreto evidente confirmado en archivos rastreados;
- los servicios GPU rechazan el arranque si falta la clave y comparan la credencial de forma segura;
- esta fue una búsqueda heurística, no una auditoría especializada con historial completo de Git.

## **11. Pendientes priorizados**

### **Imprescindible para el hackathon**

**1.** Restaurar o regenerar los tres artefactos de visión esperados y dejar la suite completa verde. Ajustar Postman para que una dependencia ausente tenga una expectativa coherente si ese modo debe admitirse.

**2.** Definir una configuración de demo explícita y reproducible. Debe activar `ANALYTICS_ENGINE=persona2` y declarar con claridad si la narrativa será Azure o provisional.

**3.** Probar Azure OpenAI de extremo a extremo. Confirmar deployments, ejecutar una narración, registrar latencia y mostrar en la salida qué proveedor produjo cada contenido.

**4.** Corregir la arquitectura de la narración para que el texto visible provenga del modelo cuando el proveedor sea Azure, sin perder la validación de hechos. El fallback debe quedar marcado de forma visible.

**5.** Completar el flujo vídeo a evento. Una inferencia debe convertirse en una observación validada, luego en un candidato y finalmente en un `MatchEvent` cuando alcance los criterios definidos.

**6.** Preparar una prueba de demo única que recorra ingesta, analítica, selección, explicación, overlay y personalización con evidencias guardadas.

**7.** Mostrar en la UI el origen de cada dato: calculado desde eventos, seguimiento simulado, modelo de vídeo o LLM.

### **Deseable**

**1.** Implementar el índice de dificultad del pase con fórmula versionada.

**2.** Conectar alertas de velocidad y distancia con las etiquetas de jugador.

**3.** Validar el realismo de las distribuciones sintéticas contra datos autorizados o literatura pública.

**4.** Añadir CI para backend, frontend, Bicep y colección Postman.

**5.** Resolver advertencias de CrewAI y React.

**6.** Añadir resúmenes de medio tiempo con una ruta real de IA y revisión editorial.

**7.** Medir latencia de extremo a extremo y establecer un límite aceptable para la demo.

## **12. Lo que no pudimos verificar**

- Builds y ejecución de contenedores: no se hicieron por instrucción expresa.
- Comportamiento visual completo en navegador: comprobamos servidor, HTML, lint y build, pero no recorrimos toda la UI con automatización de navegador.
- Azure OpenAI real: no había deployments visibles en el recurso consultado y no usamos claves.
- Inferencia GPU real: el Container App encontrado estaba detenido y no lo arrancamos.
- API, frontend, worker y mensajería del despliegue analítico documentado: no aparecen en la única suscripción accesible.
- Supabase real: no usamos la cadena local ni consultamos datos externos.
- Precisión de modelos de visión: faltan artefactos de resultados en el árbol actual.
- Identidad nominal desde vídeo: el detector identifica pistas o clases, no prueba identidad de un jugador.
- Tiempo real de producción: solo verificamos reproducción incremental local.
- Realismo estadístico del dataset: no existe una comparación reproducible con una fuente autorizada dentro del alcance revisado.
- Historial completo de secretos en Git: revisamos el árbol actual, no todas las revisiones históricas.

## **13. Veredicto final**

The Prime Moment ya es una demo funcional de inteligencia sobre partidos sintéticos cuando se usa la analítica de Persona 2. La parte más sólida es el cálculo determinista: estado, métricas, patrones, filtro de momentos, personalización y overlays estructurados.

La principal diferencia entre la presentación y la realidad técnica está en los agentes y la visión. La demo predeterminada narra con plantillas. El proveedor Azure existe en código, pero no está comprobado con un deployment activo y todavía conserva texto final y resúmenes locales. La visión contiene modelos reales y un despliegue detenido, pero no completa hoy el camino automático desde vídeo hasta eventos del partido.

El proyecto no debe presentarse como un motor completo de IA en producción. Sí puede presentarse con honestidad como una plataforma local funcional, con analítica real y explicable, personalización comprobable, infraestructura preparada y adaptadores de IA y visión que todavía necesitan conexión y validación final.
