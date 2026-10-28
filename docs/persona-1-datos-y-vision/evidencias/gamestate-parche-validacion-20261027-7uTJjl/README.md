# Despliegue del parche y nueva validación GPU

Fecha: 27 de octubre de 2026. Producto: The Prime Moment.

## Conclusión

**El servicio corregido completa el análisis en T4. La calidad obtenida con
este vídeo MESSI no permite usarlo para seguimiento ni métricas de jugadores.**
La réplica quedó retirada, con escala mínima cero y ninguna GPU activa para
esta aplicación. No se modificaron los otros modelos ni las colas.

## Alcance autorizado

Construir y desplegar GameState corregido en su suscripción separada, probar
un recorte corto y, si termina, repetir el MP4 MESSI de 180 segundos. Mantener
una sola réplica durante el análisis y restaurar mínimo cero al terminar,
también si falla. No modificar Roboflow, TeamSpotting, colas ni worker.

- Suscripción: `7d45d958-156a-4278-9935-755ba5a395ca`.
- Grupo: `rg-prime-moment-dev`.
- Aplicación: `ca-mentox-gamestate-dev`.
- Región/perfil: North Central US / `NC8as-T4`.
- Secreto existente conservado en memoria; ninguna clave forma parte de la evidencia.
- Corrección: selección posicional `.iloc[0]` en calibración de keypoints.

Recurso: [grupo de GameState en Azure Portal](https://portal.azure.com/#resource/subscriptions/7d45d958-156a-4278-9935-755ba5a395ca/resourceGroups/rg-prime-moment-dev/overview).
Endpoint probado:
`https://ca-mentox-gamestate-dev.yellowdune-bc941df0.northcentralus.azurecontainerapps.io`.
No se dejaron consultas HTTP de salud en ejecución después del apagado.

## Despliegue comprobado

- Imagen: `mentox138f2e77.azurecr.io/mentox/soccernet-gamestate:7a2a65c02395`.
- Digest publicado: `sha256:11ecdcb57ff868035dd816b0ee90856a60fa458d5a4f997611700d27ae45998d`.
- Revisión de despliegue: `ca-mentox-gamestate-dev--0000007`, modo `Single`,
  escala `0-1` antes de encender para la prueba.
- Build con dependencias y siete pesos recuperados de caché; parche aplicado
  en 0,2 segundos. Esto mide el paso del parche, no la inferencia.
- Importación local de API y manifiesto completo verificados antes del push.
- Expresión corregida comprobada dentro de la imagen nueva.
- 13 regresiones aprobadas dentro de la imagen nueva, sin red ni GPU.
- Pruebas locales del paquete: 19 aprobadas y 3 omitidas por no tener pandas
  y checkout del modelo en el entorno del backend; las tres se cubren dentro
  de las 13 pruebas de la imagen.

La prueba local en sandbox quedó bloqueada al ejecutar la API con hilos; se
interrumpió y se repitió fuera del sandbox, sin red, con resultado aprobado.

## Entradas

- MP4 sintético original: 180 segundos, 2700 cuadros, 15 FPS, 1920 × 1080.
- SHA-256 original:
  `188498f09109fbae2f4cb95e6c60b541358d29777c12ea3e261b0c2693807fd7`.
- Prueba corta: primeros 2 segundos, recodificados con FFmpeg a H.264.
- Se envían solo vídeos. Tracking y eventos del simulador no alimentan el modelo.
- No se configura una plantilla nominal ni un mapeo verificado de equipos.

## Primer intento corto: fallo de visualización

Análisis `990b074412a54de597e792a9a26b1443`, 30 cuadros / 2 segundos. El proceso
remoto duró 22,855 segundos (124,649 segundos del cliente, incluido arranque).
Falló con `KeyError: 'image_id'` en el callback de visualización de TrackLab.
El tramo no produjo detecciones y el pipeline intentó agrupar una tabla vacía
para dibujar. No se envió el MP4 de 180 segundos en ese intento.

El ajuste anterior usaba `visualization.cfg.save_videos=false`, pero TrackLab
1.3.24 lee el argumento `visualization.save_videos` directamente en el
constructor de `VisualizationEngine`. Se inspeccionó el código instalado en
la imagen y se corrigió el ejecutor. Context7 no ofreció documentación de
TrackLab; se utilizó como referencia el código de esa versión instalada.

`test_runner.py` ejecuta el script Bash con comandos dobles y comprueba los
argumentos reales tanto con render desactivado como activado. Resultado tras
el segundo ajuste: 21 pruebas locales aprobadas y 3 omitidas (pandas/checkout,
ya cubiertas por las pruebas dentro de la imagen). Esta prueba corta sin
detecciones no valida por sí sola la calibración ni la calidad del detector.

El segundo despliegue y su repetición se conservan por separado en
`deploy-attempt-2.log`, `deployment-attempt-2.json` y `smoke-attempt-2/`.

## Segundo intento corto: fallo al conservar el esquema vacío

Imagen `df2a4a8f4990`, digest
`sha256:672ccc9c9de51dddbee1c971a6b93a4737ab8c14c28a51dfac057bfb9601ffe4`,
revisión de despliegue `0000010`. Análisis
`89b6fdc2effe4375a4ca40712ee0c6fd`: el render ya no se ejecutó, pero el guardado
falló con `KeyError: 'video_id'` en `TrackerState.update`. El proceso remoto
duró 23,515 segundos (124,525 segundos del cliente, incluido arranque).

`TrackerState.load` inicializaba `video_detections = pd.DataFrame()` sin las
columnas requeridas. Se añadió al parche de build la inicialización vacía con
`video_id` e `image_id`. Solo cambia el esquema vacío: no crea observaciones
ni convierte fallos desconocidos en un resultado exitoso. El parche mantiene
la comprobación estricta de coincidencias y sintaxis.

Las regresiones evalúan el método `update` real instalado, con dos actualizaciones
vacías y una actualización posterior con una detección. Resultado: 18 pruebas
aprobadas dentro de la imagen; 24 aprobadas y 5 omitidas en el entorno local
del backend. Las cinco omitidas requieren pandas o el checkout y están cubiertas
en la prueba de la imagen. El tercer intento se registra en sus archivos
`deploy-attempt-3.log`, `deployment-attempt-3.json` y `smoke-attempt-3/`.

## Ejecución y evidencia

Se usa `infra/azure/gamestate-operator.sh deploy` con
`MENTOX_IMAGE_BUILD_MODE=local`, sin un tag heredado. Las llamadas de Azure
fijan la suscripción. La construcción conserva la capa de pesos en caché.

`apps/backend/scripts/validate_gamestate_remote.py` utiliza el cliente real de
backend con lectura local del MP4 y transporte en memoria. Cada prueba guarda
resumen, estado remoto, log y, si termina, observaciones, tracking y métricas.
Esto no valida el flujo de colas ni la interfaz.

- `deploy.log`: construcción, precarga validada, push y despliegue.
- `deployment.json`: imagen y configuración aplicadas.
- `smoke/`: análisis corto y resultados.
- `full/`: análisis de 180 segundos, solo si pasa el corto.
- `shutdown.json`: comprobación final de escala y réplicas, cuando termine.

El estado final y el resultado completo se describen a continuación. Una API
saludable no equivale a precisión útil sobre el vídeo.

## Tercer despliegue y prueba corta correcta

- Imagen: `mentox138f2e77.azurecr.io/mentox/soccernet-gamestate:60da675eaafb`.
- Digest: `sha256:7228f2cd754641eb44b9772fab1583ee1860da613dfcd85b4af93141e18d4ae8`.
- Revisión del despliegue: `0000013`; revisión encendida para validar:
  `0000014`, réplica `ca-mentox-gamestate-dev--0000014-79fdcc7df7-z54rl`.
- Se comprobó `.iloc[0]` directamente en el archivo de la réplica.
- 18 regresiones aprobadas en la imagen exacta: `container-tests.log`.

El análisis corto `77755ee192bf4e3badd3475d464ed37a` terminó con `succeeded`.
Inicio remoto `2026-10-27T21:35:10.693035+00:00`, fin
`2026-10-27T21:35:34.164750+00:00`: 23,472 segundos de proceso. El cliente tardó
124,745 segundos incluyendo el arranque desde cero. La salida contiene cero
observaciones y cero frames de tracking; las 11 métricas consultadas quedan
no disponibles. Esto verifica el manejo del resultado vacío, no precisión
de detección ni calibración.

A continuación se envió el MP4 completo sin recodificar: análisis
`bed13a88ebaf4110a00e74fce99d881f`, 2700 cuadros y SHA-256 coincidente con el
original. Su resultado final se registra en `full/`.

## Resultado completo y calidad

El estado remoto fue `succeeded`, sin `KeyError`. Inicio del proceso
`2026-10-27T21:35:45.718222+00:00`, fin
`2026-10-27T22:02:39.277154+00:00`.

| Comprobación | Resultado |
|---|---|
| Duración del vídeo | 180 segundos / 2700 cuadros |
| Tiempo del pipeline remoto | 1613,559 segundos: 26 minutos y 53,559 segundos |
| Tiempo total del cliente | 1622,142 segundos: 27 minutos y 2,142 segundos |
| Relación proceso / duración del vídeo | 8,964 veces; no es tiempo real |
| Observaciones espaciales | 4 |
| Cuadros con alguna detección | 3 de 2700: 0,111 % de cobertura de cuadros |
| Pistas observadas | 3; solo una aparece en dos cuadros consecutivos |
| Coordenadas de campo | 0; todos los `bbox_pitch` son nulos |
| Tracking convertido con posición calibrada | 0 frames |
| Lecturas de dorsal | Una lectura `10`, sin confianza OCR disponible |
| Identidades confirmadas | 0; no se configuró plantilla ni mapeo verificados |
| Métricas disponibles | 0 de 11 consultadas |

Las detecciones ocurren en los cuadros 1890, 2643 y 2644, equivalentes a
126000, 176200 y 176267 ms. Esta cobertura **no** es recall ni precisión: no
se hizo una evaluación exhaustiva con cajas etiquetadas. Se inspeccionaron
visualmente dos fotogramas originales de esos tiempos; el vídeo muestra
jugadores estilizados numerados, no personas de una transmisión real. La
diferencia visual es una explicación plausible de la baja cobertura, no una
causa aislada demostrada mediante una comparación controlada.

Las cuatro filas originales se conservan sin corregir como si fueran verdad.
Incluyen una etiqueta de equipo `nan` y puntajes de rol mayores a uno: no deben
interpretarse como equipos confirmados ni probabilidades calibradas. El dorsal
aislado tampoco confirma una identidad. No hay posiciones con las que calcular
velocidad o distancia, ni una trayectoria de balón para métricas del tiro.

El backend conserva `available=false`, valores nulos y razones de ausencia,
sin rellenarlos con tracking MESSI. Con cero frames, el contrato analítico
actual muestra el valor predeterminado `synthetic_mock` en la evidencia vacía;
es una limitación de etiquetado de ausencia, no una fuente sintética utilizada
en esta prueba. No se considera evidencia de métricas desde vídeo.

`quality-summary.json` reproduce los conteos y tiempos desde los artefactos.
Los logs muestran cargas de pesos locales/caché y no nuevas transferencias
ni instalaciones. Las líneas de MMOCR con URL identifican la fuente del
checkpoint, no demuestran una descarga. `gpu-samples.json` registra una muestra
breve de 95–100 % de utilización y 3857 MiB; no un perfil completo del proceso.

## Estado final y decisión

Se restauró mínimo cero al terminar y se cerró la consola de diagnóstico.
Azure CLI confirmó la revisión `0000015` con escala `0-1`, lista de réplicas
`[]` y ninguna otra revisión con réplica activa: `shutdown.json`.

La corrección de ejecución queda probada sobre el MP4 completo. La capacidad
analítica desde estos renders **no queda verificada**. No basta con desplegar
el baseline para obtener jugadores, dorsales, posiciones y velocidades fiables.
Hace falta evaluar material visual autorizado más cercano al entrenamiento o
entrenar/adaptar percepción y calibración al render; son trabajos posteriores,
no cambios implementados durante esta prueba. No se iniciaron nuevos análisis.
