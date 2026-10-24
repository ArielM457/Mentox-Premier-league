# Revisión de modelos GPU · 23 de octubre de 2026

## Alcance

Se revisó el paquete `docs/mentox-modelos-20261023T045413Z/` recibido desde una
computadora WSL 2 con NVIDIA GeForce RTX 3060 Laptop de 6144 MiB. La revisión
cubre integridad, logs, metadatos, conteos, rendimiento, tres capturas de
Roboflow y la recalibración de fusión. No evalúa la interfaz.

## Entorno

| Elemento | Valor |
|---|---|
| Sistema | Ubuntu 24.04 sobre WSL 2 |
| GPU | NVIDIA GeForce RTX 3060 Laptop |
| VRAM | 6144 MiB |
| Driver | 592.82 |
| Docker / Compose | 29.9.2 / 5.6.1 |
| uv | 0.13.5 |
| Python | 3.12.15 |
| Vídeo | 30 s, 1920 × 1080, 25 FPS |
| SHA-256 del vídeo | `7788719b32b944e42d8f1024fb4802f681bc2053d6301218a5bff6705b549f96` |

El manifiesto portable `SHA256-ZIP.txt` comprobó correctamente los 16 archivos
del paquete. El `sha256sum.txt` original usa rutas absolutas de Windows/WSL y no
es portable; el recolector se corrigió para producir rutas relativas en futuras
ejecuciones.

## Roboflow Sports

- Los tres pesos se ejecutaron con CUDA, 640 px y precisión FP16.
- Se procesaron 750 de 750 cuadros en 51.282,675 ms.
- Se produjeron 16.011 detecciones generales, 313 del detector especializado de
  balón y 75 observaciones de campo.
- Las detecciones generales contienen 14.125 jugadores, 1.375 árbitros, 471
  porteros y 40 balones.
- Se observaron 111 trayectorias únicas; el valor sugiere fragmentación frente
  al número esperado de participantes y debe evaluarse manualmente.
- Las capturas de 5, 15 y 25 segundos confirman cajas sobre participantes, pero
  las etiquetas se superponen y no permiten medir precisión.
- El JSON tiene SHA-256
  `825262770b591ad447f32d3cff0c192377962e39511dd9ad937703ab470d90af`.

Resultado: ejecución GPU verificada. Calidad, recobrado, F1 y estabilidad de
tracking pendientes de anotación manual.

## SoccerNet TeamSpotting

- CUDA 12.4 y AMP se activaron correctamente.
- Se procesaron 375 cuadros efectivos en 15 clips.
- Se produjeron 127 observaciones en 5.659,923 ms.
- Distribución: 48 conducciones, 46 pases, 16 pases altos, 7 cabezazos, 7
  salidas y 3 saques de banda.
- La confianza media fue 0,0723; 23 propuestas alcanzaron 0,10 y 3 alcanzaron
  0,50.
- El JSON tiene SHA-256
  `e15e9265cf913e648968a02a9799e9d87f3eb83e921db208ddb0efc79bd248a3`.

Resultado: ejecución GPU verificada y más rápida que la duración del vídeo. La
calidad sigue pendiente de anotaciones manuales para las doce clases.

## SoccerNet GameState

No se ejecutó porque la guía local indicaba erróneamente que el dataset debía
ser entregado aparte. La documentación oficial de `SoccerNet/sn-gamestate`
confirma que TrackLab descarga automáticamente SoccerNet GameState y los pesos
en el primer `tracklab -cn soccernet`.

Se corrigieron la guía y el lanzador. Para 6 GB, el smoke usa 100 cuadros y
lotes de 1 para detección y dorsal, 8 para ReID y tracking, y 1 para calibración.
La historia continúa pendiente hasta repetir la ejecución.

## Pruebas del backend

La computadora GPU obtuvo 159 aprobadas y 2 fallidas porque dos pruebas exigían
el conteo histórico exacto de 16.018 predicciones. La nueva suite genera 16.324
cajas porque añade los modelos de balón y campo. Las pruebas se corrigieron para
comparar la API con el artefacto cargado y exigir salidas no vacías, sin fijar un
resultado propio de una inferencia anterior.

Verificación posterior en Python 3.12:

```text
162 passed in 1.06s
```

## Recalibración de fusión

El informe incluido originalmente era obsoleto: correspondía a 16.018
detecciones y la nueva ejecución produjo 16.324. La calibración se repitió con
los dos JSON recibidos y produjo 19 hipótesis iniciales, 7 competidoras
suprimidas, 3 decisiones ambiguas y 12 candidatos finales. Ninguno se convirtió
en `MatchEvent`.

El backend ahora exige que las huellas SHA-256 de Roboflow y SoccerNet coincidan
con las registradas por la calibración. Para reportes antiguos comprueba además
conteos e identificadores. Por tanto, un informe viejo ya no puede aparecer
como listo junto a resultados nuevos.

## Cambios derivados

- Pruebas de integración desacopladas de conteos generados.
- `half=True` reemplazado por `quantize=16` conforme a la API vigente de
  Ultralytics.
- Manifiesto de evidencia con rutas relativas.
- El recolector de modelos ya no copia un informe de fusión posiblemente
  anterior a la ejecución.
- La calibración registra las huellas de sus dos entradas y la integración las
  valida antes de exponer resultados.
- Descarga automática de GameState documentada.
- Perfil GameState de lotes pequeños para GPU de 6 GB.

## Limitaciones

- No hay anotaciones manuales completas del vídeo real.
- Ningún conteo equivale a precisión.
- Las observaciones no se publicaron como `MatchEvent`.
- `dv-us-21-report.json` dentro del paquete es anterior; el archivo
  `dv-us-21-report-recalculado.json` sí corresponde a esta ejecución GPU.
- GameState aún no tiene una ejecución terminada.
