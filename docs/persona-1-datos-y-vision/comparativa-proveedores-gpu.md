# Comparativa de nubes GPU para los modelos de Mentox

**Fecha de consulta:** 23 de octubre de 2026.
**Moneda:** USD. Los precios son públicos, sin impuestos, almacenamiento ni transferencia de red.

## Conclusión

Sí, existen alternativas más económicas que Azure para ejecutar Roboflow Sports, SoccerNet TeamSpotting y, más adelante, SoccerNet GameState.

La recomendación para Mentox es una arquitectura híbrida:

```text
Azure Blob o fuente autorizada
          ↓ descarga única del segmento
Worker GPU externo
  ├─ Roboflow Sports
  ├─ SoccerNet TeamSpotting
  └─ GameState, cuando esté validado
          ↓ solo observaciones JSON
API de Mentox → Event Hubs / Service Bus
          ↓
Backend y frontend en Azure
```

Para el hackathon, el mejor equilibrio es **Runpod Secure Cloud con una RTX A5000 de 24 GB**. El precio publicado es USD 0,27 por hora, acepta contenedores y proporciona suficiente VRAM para evaluar los tres pipelines. Si el objetivo absoluto es minimizar el costo, **SaladCloud con RTX 3090 de 24 GB y prioridad alta** publica USD 0,17 por hora, pero su infraestructura distribuida requiere tolerar cambios de disponibilidad y validar el tratamiento del vídeo autorizado.

Azure sigue siendo útil para Blob Storage, Event Hubs, Service Bus, API y frontend. No es necesario abandonar Microsoft: solo se reemplaza el cómputo GPU, que es la parte más costosa.

## Punto de partida medido

En la RTX 3060 Laptop de 6 GB se midieron estos tiempos para un vídeo autorizado de 30 segundos:

| Pipeline | Tiempo medido |
|---|---:|
| Roboflow Sports, tres pesos | 51,283 s |
| SoccerNet TeamSpotting | 5,660 s |
| Total secuencial | 56,943 s |

La extrapolación lineal es de **2,85 horas de GPU por partido de 90 minutos**. Esta cifra sirve únicamente para comparar tarifas. Una A5000, 3090 o 4090 no tendrá el mismo rendimiento que la 3060 y debe medirse con el mismo vídeo antes de calcular un presupuesto definitivo.

## Comparación económica

| Proveedor y modalidad | GPU | VRAM | Precio publicado/h | Estimación por partido a 2,85 h | Evaluación |
|---|---|---:|---:|---:|---|
| SaladCloud, prioridad alta | RTX 3090 | 24 GB | USD 0,170 | USD 0,48 | Más barato; disponibilidad distribuida |
| Runpod Secure Pod | RTX A5000 | 24 GB | USD 0,270 | USD 0,77 | Mejor equilibrio para Mentox |
| SaladCloud, prioridad alta | RTX 4090 | 24 GB | USD 0,330 | USD 0,94 | Más velocidad probable, por medir |
| Google Compute Engine | T4, solo GPU | 16 GB | USD 0,350 | USD 1,00 más CPU/RAM | No mejora claramente el costo total |
| Runpod Secure Pod | RTX 3090 | 24 GB | USD 0,500 | USD 1,43 | Fácil, pero la A5000 publicada es más barata |
| Modal | T4, solo GPU | 16 GB | USD 0,5904 | USD 1,68 más CPU/RAM | Excelente experiencia serverless |
| Azure VM, pago por uso | T4 | 16 GB | USD 0,594 | USD 1,69 | Integra bien con Azure; exige administrar VM |
| Lambda Cloud | Quadro RTX 6000 | 24 GB | USD 0,690 | USD 1,97 | Simple, pero no es la más económica |
| Azure Container Apps GPU | T4 + 8 vCPU + 56 GiB | 16 GB | hasta USD 1,620 | hasta USD 4,62 | Escala a cero; sujeto a cuota y región |

Las estimaciones multiplican la tarifa por 2,85 horas. No incluyen el posible aumento de velocidad de una GPU superior, tiempo de arranque, descarga de pesos, disco, almacenamiento ni tráfico. Google aclara que la GPU se cobra además de CPU y memoria. Modal también cobra CPU y RAM por separado. En SaladCloud, vCPU y RAM están incluidos en la tarifa de GPU.

## Evaluación por proveedor

### Runpod: opción recomendada

Ventajas:

- ejecuta imágenes Docker similares a las que ya usa el repositorio;
- permite usar un Pod dedicado para una prueba larga o Serverless para trabajos esporádicos;
- ofrece GPU con 24 GB a un costo bajo;
- requiere pocos cambios en los scripts actuales;
- un Pod caliente evita el arranque en frío durante una demostración.

Limitaciones:

- el Pod debe detenerse o eliminarse cuando no se use;
- los volúmenes y la transferencia pueden tener cargos adicionales;
- Serverless necesita adaptar el proceso a un `handler` y puede tener arranque en frío;
- no utiliza el crédito de Azure for Students.

Para la primera prueba conviene un **Pod Secure RTX A5000 de 24 GB**, no Serverless. Cuando el pipeline sea estable, se puede empaquetar como worker Serverless.

### SaladCloud: menor costo publicado

Ventajas:

- RTX 3090 de 24 GB desde USD 0,17/h en prioridad alta;
- RTX 4090 de 24 GB desde USD 0,33/h en prioridad alta;
- CPU y RAM incluidas;
- cobro por segundo y despliegue de contenedores.

Limitaciones:

- usa una red distribuida de GPU de consumo;
- las prioridades bajas pueden perder disponibilidad frente a trabajos de mayor prioridad;
- se debe revisar seguridad, región y condiciones de uso antes de procesar material autorizado;
- para un partido en vivo se debe usar prioridad alta, reintentos y puntos de control.

Es una buena opción para pruebas batch y videos no sensibles. No sería la primera elección para una transmisión crítica hasta validar estabilidad.

### Modal: mejor experiencia serverless

Ventajas:

- cobra por segundo y no cobra GPU inactiva;
- permite funciones, colas y endpoints con escalado automático;
- publica crédito inicial para desarrollo;
- es apropiado para segmentos cortos e inferencia bajo demanda.

Limitaciones:

- requiere adaptar los contenedores y scripts al modelo de ejecución de Modal;
- la T4 cuesta aproximadamente lo mismo que la VM T4 de Azure antes de sumar CPU y RAM;
- para vídeo continuo puede convenir mantener una GPU caliente, reduciendo el beneficio de escala a cero.

### Vast.ai: económico, con mayor variabilidad

Vast.ai funciona como un mercado de hosts que ejecutan instancias Linux con Docker. Puede ser muy económico, pero el precio, ancho de banda, disponibilidad y confiabilidad dependen del host. Es útil para experimentación y entrenamiento interrumpible; exige seleccionar máquinas verificadas y guardar resultados fuera de la instancia.

### Google Cloud y Lambda

Son opciones técnicamente sólidas, pero sus tarifas públicas no superan a Runpod o SaladCloud para este caso. Google cobra la T4 además de CPU y memoria. Lambda ofrece una plataforma preparada para IA, pero una GPU de 24 GB parte de un precio mayor que la A5000 de Runpod.

## Qué significa «mejor» para este proyecto

El proveedor más barato no garantiza el mejor resultado. Para Mentox importan estos criterios:

1. **24 GB de VRAM:** deja margen para GameState y evita trabajar al límite de 6 GB.
2. **Contenedores Docker:** permite reutilizar la integración ya preparada.
3. **GPU caliente durante el partido:** evita que cada segmento espere la carga de CUDA y de los pesos.
4. **Facturación por uso:** la GPU debe apagarse al terminar la prueba.
5. **Región y red:** el vídeo debe descargarse una vez; no debe enviarse cuadro por cuadro entre nubes.
6. **Seguridad:** los pesos deben quedar en un registro privado y el vídeo debe usar una URL temporal.
7. **Observabilidad:** registrar retraso, tiempo por segmento, VRAM, cuadros descartados y errores.

## Diseño de despliegue propuesto

Para evitar que el cambio de proveedor afecte al backend:

1. Azure Blob genera una URL SAS de lectura con duración corta para el vídeo o segmento.
2. El backend crea un trabajo con `match_id`, URL, intervalo temporal y configuración de modelos.
3. El worker GPU descarga el segmento una sola vez.
4. Ejecuta los modelos y normaliza resultados a `VisionObservation`.
5. Envía lotes pequeños al endpoint HTTPS de ingesta de Mentox.
6. El backend valida, deduplica y publica en Event Hubs o Service Bus.
7. El worker elimina el archivo temporal y reporta métricas.

No se deben entregar al proveedor externo secretos con permisos de propietario de Event Hubs o Blob. Para la prueba se debe usar un token restringido del backend y una URL SAS de lectura. En producción conviene identidad federada o credenciales de corta duración.

## Plan de validación antes de decidir

1. Construir una sola imagen privada con los modelos y pesos permitidos.
2. Ejecutar el vídeo autorizado de 30 segundos en una A5000 de Runpod.
3. Medir tiempo total, uso máximo de VRAM, tiempo de arranque y costo real.
4. Repetir con un vídeo de 5 a 10 minutos para detectar acumulación de retraso.
5. Probar GameState por separado antes de incluirlo en el camino principal.
6. Comparar el mismo contenedor en SaladCloud solo si el vídeo puede procesarse allí.
7. Elegir proveedor con evidencia, no únicamente con la tarifa anunciada.

## Decisión recomendada

- **Demo inmediata y desarrollo:** GPU local de 6 GB para Roboflow y TeamSpotting.
- **Prueba cloud integral:** Runpod Secure RTX A5000 de 24 GB.
- **Lote de costo mínimo:** SaladCloud RTX 3090, prioridad alta.
- **Serverless después de optimizar:** Modal o Runpod Serverless.
- **Servicios compartidos:** conservar Azure Blob, Event Hubs, Service Bus, backend y frontend.
- **Azure GPU:** usarla solo si los créditos, la cuota disponible o las reglas del hackathon justifican el costo adicional.

## Fuentes oficiales

- [Precios de Runpod](https://www.runpod.io/pricing)
- [Precios de SaladCloud](https://salad.com/pricing/)
- [Precios de Modal](https://modal.com/pricing)
- [Preguntas frecuentes de Vast.ai](https://console.vast.ai/faq/)
- [Precios de GPU de Google Cloud](https://cloud.google.com/products/compute/gpus-pricing)
- [Instancias y precios de Lambda](https://lambda.ai/instances)
- [Evaluación de Azure y WebGPU de Mentox](evaluacion-costos-modelos-en-la-nube.md)
