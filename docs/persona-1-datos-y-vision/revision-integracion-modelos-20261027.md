# Revisión de modelos e integración · 27 de octubre de 2026

La integración de The Prime Moment permite preparar TeamSpotting y GameState
sobre un MP4 y capturar fotogramas con los tres detectores de Roboflow durante
Play. La revisión encontró fallos que se corrigieron y límites que impiden
afirmar que todos los eventos y métricas pedidos ya están completos.

Esta revisión es de código y pruebas locales. No encendió recursos Azure,
no construyó la imagen GPU y no midió precisión ni latencia de los modelos.

Actualización posterior: la
[primera validación real de GameState en T4](evidencias/gamestate-validacion-20261027-JoY84d/README.md)
falló en calibración con `KeyError: 0`. Después se construyó y desplegó el
parche, se corrigieron el render y el guardado sin detecciones y se repitió
el MP4 de 180 segundos.

La [prueba final](evidencias/gamestate-parche-validacion-20261027-7uTJjl/README.md)
terminó sin errores en unos 27 minutos, pero produjo solo 4 detecciones en
3 cuadros de 2700, ninguna posición calibrada y ninguna métrica disponible.
El despliegue y la ejecución quedan comprobados; la calidad analítica sobre
ese vídeo MESSI es insuficiente. Se aprobaron 18 regresiones dentro de la imagen
corregida, sin red ni GPU, y 24 pruebas locales con 5 omitidas cubiertas en la
imagen. GameState quedó con mínimo cero y ninguna réplica activa.

## Fallos corregidos

| Problema encontrado | Cambio y comprobación |
|---|---|
| Cerrar una petición podía cancelar la preparación que compartían el arranque y Play | La tarea se protege de la cancelación del cliente. Una solicitud de otro partido recibe 409 mientras haya una preparación activa. |
| Un fallo parcial permitía iniciar un nuevo intento mientras otros modelos seguían ejecutándose | La preparación conserva y espera las operaciones independientes, con resultado o error por servicio. |
| La preparación automática exigía que estuvieran configurados los tres servicios | Ahora prepara los servicios configurados; un endpoint incompleto produce un error explícito. |
| Solo se veía “preparando” sin saber qué ocurría | Cada cliente informa su fase, errores y resultados. Un resultado vacío puede estar listo y no se confunde con un análisis pendiente. |
| Un reintento de GameState subía otra vez el MP4 después de agotar el sondeo | Conserva el `analysis_id` y reanuda la consulta. Solo un fallo terminal o un análisis desaparecido permite crear uno nuevo. Esta recuperación se conserva mientras viva el backend. |
| Un error HTML o texto del proxy terminaba como fallo de JSON | Se conserva el estado HTTP y un fragmento legible del cuerpo para diagnóstico. |
| Los artefactos locales antiguos eran necesarios para consultar el estado actual | El estado del runtime sigue disponible aunque falten. Se identifican los artefactos como históricos y no se reproducen sobre el MP4 de Blob. |
| GameState renderizaba un MP4 anotado adicional que el backend no usa | El render está desactivado por defecto y puede habilitarse para diagnóstico. |
| Un análisis podía seguir ejecutándose sin límite o dejar procesos GPU vivos | La API limita su duración, termina el grupo de procesos y conserva un estado de fallo. Rechaza otra carga pendiente con 429. |
| Se asumía que el lado o cluster del modelo identificaba al equipo local | Ahora se exige un mapeo explícito. Los nombres solo se habilitan con una plantilla verificada para ese MP4. |
| Filas repetidas podían contar como varios votos de identidad o duplicar posiciones | Los votos cuentan cuadros distintos. Se eliminan pistas repetidas de un mismo cuadro y se rechazan identidades simultáneas incompatibles. |
| Pistas `0`, `14.0` o sin identificador se trataban de forma diferente entre tracking y observaciones | Comparten normalización; una detección sin pista mantiene `track_id=null`. |
| Las ventanas de velocidad podían atravesar una pérdida de seguimiento | Se cortan en los saltos o huecos; una posición aislada produce métricas no disponibles. |
| Retroceder el vídeo podía bloquear capturas hasta alcanzar el tiempo anterior | Seek y pausa reinician el intervalo. Se descartan respuestas de inferencia de una posición de reproducción anterior. |
| La pantalla podía mostrar cuadros futuros y atribuir una acción a un dorsal cercano en el tiempo | Se filtran por el tiempo actual y se retiró esa atribución sin evidencia espacial. |
| Event Hubs podía saltarse observaciones publicadas durante la conexión del consumidor | El punto inicial es la hora de creación del consumidor, en vez de `@latest` al conectar cada partición. Su terminación se expone como error. |
| El conjunto de deduplicación crecía aunque el historial fuera limitado | Se limita a los identificadores conservados en el historial. |
| Una respuesta parcial de Roboflow podía aceptarse como suite completa | Se exige presencia de `player`, `ball` y `pitch`, aunque un modelo entregue cero detecciones. |

Los clientes calculan SHA-256 del MP4 enviado. La preparación rechaza resultados
de TeamSpotting y GameState si ambos informan huellas distintas. El blob debe
permanecer estable durante la prueba; reemplazar el archivo requiere reiniciar
y preparar el backend con la nueva fuente.

## Qué se puede afirmar

| Capacidad | Resultado de la revisión |
|---|---|
| Detecciones de jugadores, árbitro, balón y puntos de cancha | Integración de los tres modelos Roboflow preparada; la calidad depende del vídeo. |
| Acciones como pase, tiro y entrada | TeamSpotting las entrega como candidatos temporales; no identifica al autor ni al receptor. |
| Pistas, roles, equipo visual, dorsal y coordenadas | GameState tiene adaptador y API. La cobertura efectiva y la estabilidad se deben comprobar sobre el MP4. |
| Distancia, velocidad e intensidad del jugador | Cálculo probado por pista cuando existen segmentos calibrados continuos. No necesita un nombre confirmado. |
| Nombre de jugador | Condicional: plantilla correcta, mapeo de equipo y votos suficientes. El resultado se mantiene vacío cuando falta evidencia. |
| Forma por equipo | Condicional a mapeo verificado y suficientes jugadores calibrados por cuadro. |
| Velocidad de balón y tiro | Falta una trayectoria de balón continua, calibrada y con frecuencia suficiente. Una captura por segundo no resuelve este requisito. |
| Pasador, receptor, distancia y precisión desde vídeo | Falta asociar la acción al balón y a los actores, con resultado verificable. Los datos sintéticos ya existentes no prueban esta capacidad desde vídeo. |
| Dificultad del pase | Sigue pendiente una fórmula explícita, sus entradas y validación. |
| Publicación automática de todos los `MatchEvent` desde los modelos | No está completa. El canal `vision-observations` transporta evidencia experimental. La fusión aún exige información que las acciones temporales no proporcionan. |

## Riesgos todavía abiertos

1. La imagen optimizada de GameState necesita una construcción completa y una
   inferencia real en T4. El manifiesto verifica los siete archivos esperados,
   pero las pruebas locales no demuestran su compatibilidad en CUDA ni descartan
   una descarga adicional durante esa inferencia.
2. GameState ejecuta TrackLab en un proceso nuevo por análisis. Precargar pesos
   evita trabajo de red previsto, pero no elimina la carga de módulos, pesos y
   CUDA para cada vídeo. `/health/ready` comprueba prerrequisitos, no un análisis
   terminado ni toda la memoria GPU ya preparada.
3. Los resultados del servicio y la caché del backend son efímeros. La siguiente
   mejora operativa es guardar resultados por huella del vídeo y versión del
   modelo en Blob Storage. No hay recuperación durable entre réplicas.
4. La ejecución asíncrona exige mantener una réplica mínima durante el análisis
   y descargar resultados antes de apagarla. Los operadores existentes permiten
   hacerlo; `min-replicas=0` no garantiza mantener un trabajo en segundo plano.
5. El contenedor fija GameState, TrackLab y varias dependencias, pero los repos
   de `prtreid` y `torchreid` todavía no están fijados a commits y faltan hashes
   de referencia externos para varios pesos. La construcción no es totalmente
   reproducible hasta resolverlo.
6. El render MESSI difiere de una transmisión real. Tener detecciones o una API
   saludable no demuestra precisión sobre esos jugadores dibujados.
7. Las colas de métricas e importantes tienen pruebas locales de separación,
   reintentos y errores. Eso no demuestra un recorrido nuevo en Azure. Además,
   `run_important_event_worker.py` usa `DispatchRecordingHandler`: confirma el
   despacho, pero todavía no ejecuta los agentes narrativos ni publica sus
   resultados. Esta limitación es independiente de los detectores de vídeo.

## Verificación reproducible

Desde la raíz, sin encender GPU ni conectarse a Azure:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 --with python-multipart==0.0.20 \
  pytest -q \
  apps/backend/tests/test_model_preparation.py \
  apps/backend/tests/test_model_http.py \
  apps/backend/tests/test_soccernet_gamestate_adapter.py \
  apps/backend/tests/test_gamestate_analysis.py \
  apps/backend/tests/test_teamspotting_analysis.py \
  apps/backend/tests/test_live_vision_capture.py \
  apps/backend/tests/test_analytics_tracking.py \
  apps/backend/tests/test_integrated_pipeline_api.py \
  apps/backend/tests/test_vision_observation_transport.py \
  apps/backend/tests/test_routing_transport.py \
  apps/backend/tests/test_important_event_worker.py \
  apps/backend/tests/test_observation_fusion.py \
  apps/backend/tests/test_candidate_fusion.py \
  apps/backend/tests/test_transport_configuration.py \
  deploy/azure-soccernet-gamestate
```

Resultado: 101 pruebas aprobadas. La API se probó con dobles de CUDA, OpenCV y
subproceso; las pruebas incluyen cancelación del cliente, reintento, 429, fallo
del ejecutor y terminación por timeout. Se usó Python 3.12.13; esto no sustituye
una construcción de la imagen Python 3.9. En el entorno restringido hubo que
ejecutar esta comprobación fuera del sandbox por un bloqueo de hilos de AnyIO.

Después se añadió la regresión de desconexión HTTP de Roboflow. La comprobación
final de `test_model_http.py` y `test_live_vision_capture.py` aprobó sus 10 pruebas;
la repetición final de las cuatro pruebas de la API GameState también pasó.

El frontend se compiló con Node 22.17.0 y Vite 8.3.3. El lint terminó sin errores
y conservó tres advertencias existentes en Editorial, useCatalog y MomentDetail.
La sintaxis de los scripts Bash y `git diff --check` se comprobaron por separado.

## Aplicar los cambios

Reinicie el backend con sus variables actuales para usar las correcciones de
integración. Para usar las correcciones dentro del servicio GPU hay que
reconstruir y desplegar GameState desde el código actualizado, conservando la
clave del servicio:

```bash
export MENTOX_IMAGE_BUILD_MODE=local
export MENTOX_ACCEPT_MODEL_LICENSES=1
bash infra/azure/gamestate-operator.sh deploy
```

Compruebe antes la suscripción, el grupo y que `MENTOX_MODEL_API_KEY` corresponda
al servicio. El operador despliega en escala cero. La revisión no ejecutó este
comando ni modificó los recursos existentes.

## Documentación contrastada

- [Configuración fijada de SoccerNet GameState](https://github.com/SoccerNet/sn-gamestate/blob/1c958345067218297d221e45e1a6405f975f83e0/sn_gamestate/configs/soccernet.yaml): pipeline offline, inicialización y render.
- [Configuración ReID](https://github.com/SoccerNet/sn-gamestate/blob/1c958345067218297d221e45e1a6405f975f83e0/sn_gamestate/configs/modules/reid/prtreid.yaml) y [calibración](https://github.com/SoccerNet/sn-gamestate/blob/1c958345067218297d221e45e1a6405f975f83e0/sn_gamestate/configs/modules/pitch/nbjw_calib.yaml): rutas de pesos precargados.
- [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/), consultado mediante Context7: inicialización y ciclo de vida.
- [Azure CLI Container Apps](https://learn.microsoft.com/en-us/cli/azure/containerapp) y [revisiones](https://learn.microsoft.com/en-us/cli/azure/containerapp/revision), consultados mediante Context7: variables y revisión única.
- [SDK Event Hubs](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/eventhub/azure-eventhub/api.md), consultado mediante Context7: consumo desde una fecha de encolado.
