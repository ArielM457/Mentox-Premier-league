# Evaluación de costos para ejecutar los modelos de visión

**Fecha de consulta:** 23 de octubre de 2026.
**Moneda:** USD, precios públicos sin impuestos, descuentos ni ajustes particulares de Azure for Students.

## Conclusión

Para el hackathon conviene mantener el backend, Blob Storage, Event Hubs y Service Bus en Azure, pero ejecutar la primera demostración de los modelos en la RTX 3060 disponible. Si la inferencia también debe mostrarse en Azure, la opción recomendada es **Azure Container Apps Jobs con una GPU T4 serverless, mínimo cero y máximo uno**. Debe encenderse antes de la demo y apagarse al terminar.

No se recomienda todavía un endpoint GPU permanente de Azure Machine Learning. Los endpoints online no escalan a cero y cobran la instancia mientras está aprovisionada. Azure ML Batch o Container Apps Jobs son mejores para procesamiento por lotes; Container Apps es más cercano al flujo en vivo del proyecto.

## Rendimiento medido en Mentox

Las cifras siguientes provienen de las evidencias del repositorio sobre un vídeo autorizado de 30 segundos.

| Modelo | GPU medida | Tiempo | Factor respecto al vídeo |
|---|---|---:|---:|
| Roboflow Sports, tres pesos | RTX 3060 Laptop, 6 GB, FP16 | 51,283 s | 1,71× más lento que el vídeo |
| SoccerNet TeamSpotting | RTX 3060 Laptop, 6 GB, AMP | 5,660 s | 5,30× más rápido que el vídeo |
| SoccerNet GameState | Recomendación mínima de 12 GB | Pendiente | Desconocido |

Roboflow y TeamSpotting ejecutados uno después del otro consumen aproximadamente 56,94 segundos de GPU por cada 30 segundos de vídeo. Si el comportamiento fuera lineal, un partido de 90 minutos necesitaría unas **2,85 horas de GPU**. Es una extrapolación, no una prueba sobre un partido completo.

La inferencia actual no garantiza tiempo real porque Roboflow acumula retraso. Para acercarse a una observación por segundo se debe medir y ajustar resolución, intervalo de cuadros, modelos activos, TensorRT u ONNX y procesamiento de segmentos. TeamSpotting sí tiene margen en la GPU medida.

## Opción 1: computadora GPU local

**Costo cloud:** USD 0.
**Mejor uso:** desarrollo, calibración y demo presencial.

- Ya está verificada con 6 GB para Roboflow y TeamSpotting.
- No hay cuota cloud, arranque en frío ni transferencia de vídeo.
- GameState puede no caber en 6 GB.
- Para ofrecer una API pública se pueden publicar únicamente observaciones en Event Hubs.

Esta es la alternativa más económica: **inferencia local → observaciones JSON → Azure Event Hubs → backend y frontend Azure**.

## Opción 2: Azure VM con NVIDIA T4

La máquina mínima razonable es `Standard_NC4as_T4_v3`: 4 vCPU, 28 GiB RAM y una NVIDIA T4 de 16 GB.

La API pública de precios de Azure mostró para Central US:

| Modalidad Linux | Precio aproximado por hora | 2,85 h por partido | 730 h al mes |
|---|---:|---:|---:|
| Pago por uso | USD 0,594 | USD 1,69 | USD 433,62 |
| Spot | USD 0,19899 | USD 0,57 | USD 145,26 |
| Low Priority | USD 0,119 | USD 0,34 | USD 86,87 |

Spot puede ser interrumpida. Low Priority se usa mediante servicios que admiten trabajo desalojable, como clústeres batch. Disco, snapshots, red y logs se cobran por separado.

Una VM detenida desde el sistema operativo puede seguir cobrando cómputo. Debe quedar **deallocated** desde Azure. Para una demo es viable iniciarla antes del partido y desasignarla al terminar.

## Opción 3: Azure Container Apps con GPU serverless

El perfil `Consumption-GPU-NC8as-T4` ofrece una T4, 8 vCPU y hasta 56 GiB. Admite cobro por segundo y escala a cero. Central US aparece en la API de precios y en la disponibilidad oficial.

Estimación pública de Central US:

| Medidor | Tarifa | Equivalente por hora |
|---|---:|---:|
| GPU T4 | USD 0,000090/s | USD 0,324 |
| 8 vCPU activos | 8 × USD 0,000024/s | USD 0,6912 |
| 56 GiB activos | 56 × USD 0,000003/GiB-s | USD 0,6048 |
| **Total máximo asignado** |  | **USD 1,62/h** |

Con 2,85 horas activas serían aproximadamente **USD 4,62 por partido** antes de la franquicia gratuita de CPU y memoria. Azure ofrece mensualmente 180.000 vCPU-s, 360.000 GiB-s y dos millones de solicitudes sin cargo para Container Apps; la GPU no aparece como gratuita. El costo real debe confirmarse en Cost Management después de una prueba corta.

Ventajas:

- escala a cero y factura por segundo;
- ejecuta contenedores con cambios moderados;
- usa identidad administrada para Blob, Event Hubs y Service Bus;
- resulta apropiado para jobs y workers activados por cola.

Riesgos:

- requiere cuota GPU y una región habilitada;
- puede tener arranque en frío largo por CUDA, imágenes y pesos;
- la imagen debe ejecutarse como usuario no root;
- factura los recursos asignados mientras la réplica está activa;
- Azure for Students puede negar la cuota aunque existan créditos.

## Opción 4: Azure Machine Learning

Azure ML no añade una tarifa propia al workspace, pero cobra cómputo, Container Registry, Storage, Key Vault y observabilidad.

### Entrenamiento

Se necesita dataset autorizado y anotado, workspace, Blob Storage, Container Registry, un clúster GPU con mínimo cero, entorno CUDA/PyTorch, job de entrenamiento y registro del modelo.

Para pruebas conviene un clúster Spot/Low Priority con `min_instances=0` y `max_instances=1`. La T4 sirve para ajuste y experimentos pequeños, pero GameState o entrenamientos grandes pueden requerir A10/A100 y multiplicar el costo.

### Despliegue

- **Managed online endpoint:** baja latencia, pero mantiene al menos una instancia; no escala a cero.
- **Batch endpoint:** consume instancias solo durante los jobs. Sirve para vídeos completos, no para eventos en vivo de baja latencia.
- **Azure ML sobre Kubernetes:** demasiado complejo para este hackathon.

Azure ML es útil para registrar versiones, experimentos y entrenamiento reproducible. No es la ruta más barata para servir continuamente los contenedores actuales.

## Arquitectura Azure recomendada

```text
Vídeo autorizado en Blob Storage
        ↓
Event Grid o solicitud de inicio
        ↓
Container Apps Job GPU T4
  ├─ Roboflow Sports
  └─ SoccerNet TeamSpotting
        ↓ VisionObservation
Event Hubs: vision-observations
        ↓
Backend: validación, deduplicación y fusión
  ├─ Event Hubs: match-metrics
  └─ Service Bus: important-events
        ↓
API/SSE → Centro del partido
```

Para una transmisión segmentada, el worker recibe fragmentos cortos con `match_id`, tiempo inicial y hash. Publica resultados incrementales y conserva el retraso. Los pesos deben quedar en la imagen o en Storage con caché para no descargarlos en cada trabajo.

## Recursos necesarios

| Recurso | Propósito | Obligatorio inicialmente |
|---|---|---|
| Azure Container Registry Basic | Guardar las imágenes GPU | Sí para Container Apps |
| Blob Storage | Vídeo permitido, pesos y salidas grandes | Ya existe |
| Container Apps Environment con workload profiles | Ejecutar GPU serverless | Sí |
| Container Apps Job T4 | Inferencia al recibir trabajo | Sí |
| Managed Identity | Acceso sin secretos | Sí |
| Event Hubs `vision-observations` | Observaciones continuas | Ya existe |
| Event Hubs `match-metrics` | Métricas reconstruibles | Preparado, pendiente de desplegar |
| Service Bus `important-events` | Jugadas durables | Preparado, pendiente de desplegar |
| Log Analytics/Application Insights | Diagnóstico | Opcional y con límites de ingesta |
| Azure ML workspace | Entrenamiento y registro | No para la primera demo |

## Qué es WebGPU

WebGPU es una API del navegador para usar la GPU de la computadora del espectador desde JavaScript. Puede ejecutar cómputo y modelos convertidos, por ejemplo con ONNX Runtime Web. No es una GPU de Azure y no genera costo de inferencia cloud.

Podría servir para un detector ligero:

```text
Vídeo en el navegador → modelo ONNX → WebGPU local → observaciones → backend
```

No sustituye directamente el pipeline actual:

- los modelos usan PyTorch, Python, OpenCV, ByteTrack y lógica propia;
- T-DEED y GameState pueden tener operadores incompatibles;
- se debe exportar y validar cada modelo en ONNX;
- memoria, velocidad y soporte cambian por navegador y dispositivo;
- requiere HTTPS y todavía no funciona igual en todos los navegadores;
- no conviene confiar en el espectador para producir el registro oficial.

La recomendación es evaluar WebGPU después para una vista ligera, no para reemplazar ahora al worker central.

## Alternativas externas más económicas

Los precios externos cambian y no consumen créditos Microsoft.

| Proveedor | Ejemplo publicado | Observación |
|---|---:|---|
| Runpod | RTX A5000 24 GB desde USD 0,27/h | Económico para jobs; sale del ecosistema Azure |
| Modal | T4 USD 0,000164/s, aproximadamente USD 0,5904/h, más CPU y memoria | Escala a cero y publica crédito mensual inicial |
| Lambda | V100 16 GB desde USD 0,79/h; A10 24 GB USD 1,29/h | Simple, pero menos económico para este caso |

Una RTX A5000 de Runpod podría procesar un partido por debajo de un dólar si conserva el rendimiento medido, pero se deben evaluar disponibilidad, almacenamiento, seguridad y transferencia.

## Recomendación por etapa

### Ahora

1. Mantener inferencia local en la RTX 3060.
2. Enviar observaciones a Azure, no el vídeo cuadro por cuadro.
3. Desplegar y probar `match-metrics` e `important-events`.
4. Medir un vídeo de 5 a 10 minutos antes de extrapolar a 90 minutos.

### Demo Azure

1. Solicitar cuota para `Consumption-GPU-NC8as-T4` en Central US, East US o East US 2.
2. Crear un Container Apps Job con mínimo cero y máximo uno.
3. Mantener la GPU activa solo durante la demo.
4. Configurar alertas al 50 %, 75 % y 90 % del crédito.

### Producción o tiempo real

1. Perfilar cada etapa por cuadro.
2. Exportar YOLO a TensorRT u ONNX y verificar nuevamente la calidad.
3. Separar detector espacial y modelo temporal solo si una GPU no mantiene el ritmo.
4. Aplicar contrapresión para no acumular segmentos ilimitados.
5. Medir latencia p50/p95, cuadros descartados y retraso respecto al vídeo.
6. Mantener GameState fuera del camino crítico hasta verificar su integración.

## Comandos para comprobar la suscripción

```bash
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.ContainerRegistry
az provider register --namespace Microsoft.MachineLearningServices

az vm list-usage \
  --location centralus \
  --query "[?contains(localName, 'NC')].{familia:localName,uso:currentValue,limite:limit}" \
  --output table

az vm list-skus \
  --location centralus \
  --size Standard_NC4as_T4_v3 \
  --all \
  --output table

az containerapp env workload-profile list-supported \
  --location centralus \
  --query "[?contains(name, 'GPU')]" \
  --output table
```

Si el límite NC o GPU serverless es cero, tener crédito no basta: se debe solicitar cuota o elegir otra región o suscripción.

## Fuentes consultadas

- Documentación oficial de Azure sobre NCasT4_v3, Azure Machine Learning endpoints y Container Apps serverless GPU.
- Documentación oficial de facturación de Azure Container Apps.
- API pública Azure Retail Prices para Central US.
- MDN WebGPU y documentación Microsoft de ONNX/Windows ML.
- Páginas oficiales de precios de Modal, Runpod y Lambda.
- Evidencias DV-US-20, DV-US-26 y DV-US-27 del repositorio.
