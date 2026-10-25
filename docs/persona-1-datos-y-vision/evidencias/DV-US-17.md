# Evidencia técnica de DV-US-17

## Identificación

- **Historia:** DV-US-17 · Preparar el paquete de vídeo permitido.
- **Estado:** verificada localmente el 13 de octubre de 2026 con un vídeo sintético de 30 segundos y una anotación manual mínima.
- **Prioridad:** P0.
- **Última verificación:** 13 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.
- **Eleva:** DV-US-10 y habilita DV-US-11 a DV-US-13.

## Objetivo comprobado hasta ahora

Se seleccionó Google Research Football como fuente de un clip sintético y reproducible. El repositorio oficial se fijó al commit `3d9e754720a95621bba6475c4d3b0d56fe919014` y se aisló mediante Docker para no incorporar sus dependencias antiguas al backend Python 3.12.

El arnés ejecutó inicialmente `academy_pass_and_shoot_with_keeper` con bots integrados, generó una repetición, la convirtió a MP4 y escribió un manifiesto con origen, commit, licencia declarada por el proyecto, tamaño, SHA-256, duración, resolución y FPS. La ejecución demostró el flujo completo, pero el episodio terminó a los 20 pasos y produjo solo 2 segundos. Por ello se cambió el escenario a `11_vs_11_stochastic`, con un límite explícito de 300 pasos, antes de preparar la anotación final.

## Decisiones

- No instalar `gfootball` en `apps/backend`.
- No usar TensorFlow, checkpoints ni datos de transmisiones reales.
- Ejecutar el motor con CPU y `render=False`; GRF produce una animación simple de la repetición.
- Usar un escenario de 300 pasos, equivalente a 30 segundos.
- Convertir AVI a MP4 H.264 con `ffmpeg` para la futura interfaz web.
- Mantener videos, trazas y dumps fuera de Git.
- Conservar el resultado localmente y, después de revisar el manifiesto, permitir únicamente Blob Storage privado.
- Usar el MP4 en la interfaz de Mentox de DV-US-18; la ventana propia de GRF no sustituye esa prueba.

## Fuente y permiso

| Elemento | Registro |
|---|---|
| Proyecto | Google Research Football |
| Repositorio | `https://github.com/google-research/football` |
| Revisión fijada | `3d9e754720a95621bba6475c4d3b0d56fe919014` |
| Licencia declarada | Apache-2.0 |
| Estado upstream | Archivado y de solo lectura desde agosto de 2026 |
| Naturaleza del medio | Simulación generada, no partido real |
| Premier League | No se usan imágenes, equipos ni transmisiones reales |

La licencia del repositorio y el hecho de generar el clip se registran como base de uso técnico. Antes de publicación externa se revisará que el video no incluya marcas o recursos con condiciones separadas.

## Archivos

| Archivo | Función |
|---|---|
| `experiments/google-research-football/Dockerfile` | Compilar GRF desde la revisión fijada |
| `experiments/google-research-football/generate_video.py` | Ejecutar bots, convertir video y producir manifiesto |
| `experiments/google-research-football/run.sh` | Construcción y ejecución reproducibles con Docker |
| `experiments/google-research-football/README.md` | Requisitos, comandos, resultados y límites |
| `experiments/google-research-football/annotations/grf-dv-us-17.csv` | Referencia manual del balón en tres momentos |
| `.gitignore` | Excluir AVI, dumps y salida del experimento |

## Cobertura de criterios de aceptación

| Criterio | Evidencia actual | Estado |
|---|---|---|
| Base del permiso y referencia | Repositorio, commit, Apache-2.0 e inspección del MP4 registrados | Cumplido |
| SHA-256, duración, resolución, FPS y origen | Manifiesto final y comprobación independiente con `sha256sum` y `ffprobe` | Cumplido |
| Tabla manual de tiempos, clases y cajas | CSV con tres referencias temporales del balón, en píxeles y normalizadas | Cumplido |
| No contener datos reales de Premier League | Escenario sintético inspeccionado en los segundos 5, 15 y 25 | Cumplido |
| Definir ubicación permitida | Fuera de Git; local y Blob privado tras revisión | Cumplido |

## Comprobaciones realizadas

```bash
sudo docker info --format 'Docker Server: {{.ServerVersion}}'
sudo docker run --rm hello-world
python3 -m py_compile experiments/google-research-football/generate_video.py
bash -n experiments/google-research-football/run.sh
git diff --check
```

Resultados:

- Docker Server 27.0.3.
- `hello-world` ejecutado correctamente.
- Script Python compilado sin errores.
- Script Bash válido.
- Diferencias Git sin errores de espacio.

### Primera ejecución del contenedor

Comando ejecutado el 13 de octubre de 2026:

```bash
bash experiments/google-research-football/run.sh
```

Resultados:

- La imagen se construyó correctamente con Docker Server 27.0.3.
- La compilación completa tardó 1508,2 segundos.
- La imagen producida fue `mentox/google-research-football:3d9e754`.
- El proceso se detuvo antes de generar el vídeo con `ModuleNotFoundError: No module named 'six'`.
- La causa es que la revisión fijada de GRF importa `six.moves` desde `football_action_set.py`, pero no instala `six` como dependencia.
- Se añadió `six==1.17.0` en una capa posterior a la instalación de GRF. Esto permite reutilizar la capa costosa de compilación en el siguiente intento.
- No se generó ni se confirmó ningún MP4 o manifiesto en este intento.

### Segunda ejecución del contenedor

La ejecución posterior a la instalación de `six==1.17.0` terminó correctamente:

| Dato | Resultado |
|---|---|
| Escenario | `academy_pass_and_shoot_with_keeper` |
| Pasos | 20 |
| Archivo | `grf-dv-us-17.mp4` |
| Códec | H.264 |
| Tamaño | 25.167 bytes |
| SHA-256 | `7b6e0d1be3a07509e04fbe8bb418030a5e3ee7e1cfa05df78a46fbe231089849` |
| Duración | 2 segundos |
| Resolución | 800 × 450 |
| FPS | 10 |

La comprobación independiente con `sha256sum` y `ffprobe` coincidió con el manifiesto. Una captura del segundo 1 mostró la representación sintética del campo, jugadores, balón, marcador y acciones; no mostró material de la Premier League.

Ese resultado validó técnicamente la generación y conversión, pero no fue el paquete final porque 2 segundos no permiten probar adecuadamente pausa, saltos y reconstrucción temporal en DV-US-18. Por ello, el generador se ajustó a `11_vs_11_stochastic` y 300 pasos para la ejecución final documentada a continuación.

### Ejecución final de 30 segundos

La ejecución ajustada terminó correctamente y produjo el paquete usado por esta evidencia:

| Dato | Resultado |
|---|---|
| Escenario | `11_vs_11_stochastic` |
| Pasos y cuadros | 300 |
| Archivo | `grf-dv-us-17.mp4` |
| Códec | H.264 |
| Tamaño | 434.492 bytes |
| SHA-256 | `1baede86f5274f0ff23af416d1f1d21932a84ebcfbae0d27066bdecd1ec9a7f6` |
| Duración | 30 segundos |
| Resolución | 800 × 450 |
| FPS | 10 |

`sha256sum` y `ffprobe` reprodujeron los valores del manifiesto. Se extrajeron y revisaron cuadros de los segundos 5, 15 y 25. Los tres cuadros son diferentes y muestran desplazamientos de jugadores y balón, marcador y acciones del simulador. No se observaron imágenes, escudos, nombres ni marcas de la Premier League.

La anotación manual `experiments/google-research-football/annotations/grf-dv-us-17.csv` registra la clase `ball` y cajas en píxeles y normalizadas para los cuadros 50, 150 y 250. Es una referencia humana para pruebas de localización y sincronización; no se presenta como detección automática ni como conjunto de entrenamiento.

## Documentación consultada

- Docker oficial de GRF.
- API de entorno y `render`.
- Guía de guardado de repeticiones, trazas y AVI.
- `dump_to_video.py` oficial.
- Licencia del repositorio.
- Context7 no devolvió documentación específica del paquete `six`; únicamente encontró `pdfminer.six`, que es otro proyecto y no se utilizó como referencia.

La documentación oficial confirma que `write_video` puede generar una animación simple incluso sin renderizado interactivo.

## Reproducción

```bash
bash experiments/google-research-football/run.sh
```

Resultados generados, ignorados por Git:

```text
experiments/google-research-football/output/grf-dv-us-17.mp4
experiments/google-research-football/output/grf-dv-us-17.manifest.json
```

## Limitaciones y siguientes pasos

- La primera compilación puede tardar varios minutos y descargar dependencias.
- GRF está archivado; un error de compilación debe documentarse y corregirse solo dentro del contenedor.
- Las cajas manuales cubren solo tres cuadros; no constituyen una evaluación estadística de visión.
- El MP4 permanece local y fuera de Git. Puede cargarse en `authorized-videos` privado si DV-US-18 necesita consumo remoto.
- La salida visual de GRF es una representación de depuración y no simula la apariencia de una transmisión televisiva.
- DV-US-18 puede comenzar con este archivo para validar reproducción y sincronización.
