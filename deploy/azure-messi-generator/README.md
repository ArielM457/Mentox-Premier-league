# Generador MESSI para The Prime Moment

Este paquete ejecuta MESSI en una GPU T4 como un Azure Container Apps Job. Genera
30 partidos sintéticos comprimidos, sube cada MP4 y sus datos de repetición a Azure
Blob Storage y termina. No mantiene una API ni una réplica encendida.

## Alcance predeterminado

- 30 vídeos de 180 segundos.
- Partido completo comprimido, con descanso en la mitad del vídeo.
- Renderizado `light` a 15 FPS.
- Simulación a 15 Hz. Ambos valores deben coincidir para evitar que MESSI conserve
  todos los subpasos físicos del lote durante el `lax.scan` de JAX.
- Tracking persistido cada 15 pasos, aproximadamente una muestra por segundo.
- MESSI fijado al commit `b04b15c59d36c1e4f44e02d0886b2d0d7261f689`.
- Estilos `balanced`, `tiki_taka` y `long_ball` combinados entre los partidos.

El modo se puede cambiar con `MENTOX_RENDER_MODE=rich`. `light` genera una vista
táctica rápida de 672 × 448; `rich` genera una vista más detallada de 1920 × 1080
con dorsales visibles, pero aumenta el tiempo de renderizado y el tamaño del MP4.

No son 90 minutos de vídeo real. Cada archivo representa un partido completo en
una reproducción táctica comprimida de tres minutos. Generar 30 vídeos de 90
minutos se admite cambiando `MENTOX_MATCH_SECONDS=5400`, pero multiplicaría el
tiempo de renderizado, el almacenamiento y la transferencia.

## Artefactos

```text
synthetic-videos/
└── messi/<batch-id>/
    ├── batch-manifest.json
    ├── messi-001/
    │   ├── match.mp4
    │   ├── events.jsonl
    │   ├── tracking.jsonl
    │   ├── metadata.jsonl
    │   └── manifest.json
    └── messi-030/
```

Los contenedores de Storage permanecen privados. La aplicación debe solicitar al
backend una URL SAS de lectura corta; la credencial de Storage nunca se entrega al
navegador.

## Licencia y procedencia

MESSI declara Apache-2.0. Este contenedor conserva el commit, la semilla y los
hashes de cada artefacto. The Prime Moment utiliza únicamente los partidos
sintéticos generados; no incorpora ni redistribuye vídeo real de la Premier League.

## Ejecución

La creación del Job está documentada en:

```bash
bash infra/azure/deploy-messi-generator.sh
```

El script no inicia la generación automáticamente salvo que se configure
`MENTOX_START_JOB=1`. Esto permite revisar el Job antes de comenzar a consumir GPU.

Antes del lote completo se debe ejecutar una prueba corta con una semilla y un
`batch_id` independientes. Solo se inicia el lote de 30 cuando esa ejecución
termina en `Succeeded` y publica sus cinco artefactos.

Cuando la ejecución termine y se comprueben los 30 manifiestos, se puede eliminar
solamente el Job:

```bash
export MENTOX_CONFIRM_DELETE_JOB=1
bash infra/azure/delete-messi-generator-job.sh
```

Los vídeos permanecen en Blob Storage. La identidad, ACR y el entorno compartido
no se eliminan porque otros servicios de The Prime Moment pueden utilizarlos.
