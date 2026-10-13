# Tablero de demostración

`tablero.html` reproduce el escenario sintético de 178 eventos y muestra lo que calcula el motor de Persona 2: marcador y posesión, campo con seguimiento, control, impulso y caos en el tiempo, cifras por equipo y jugador, momentos por perfil con sus motivos y el estado de cada etapa. Se abre con doble clic en cualquier navegador; necesita conexión solo para las fuentes tipográficas.

## Qué es real y qué es simulado

| Parte | Origen |
|---|---|
| Estado, estadísticas, indicadores, jugadas, patrones, momentos, prioridades y motivos | Motor real (`MatchAnalytics`) sobre el escenario sintético |
| Posiciones del campo, distancias, velocidades y avisos por umbral | Módulo de seguimiento real sobre **observaciones simuladas** (`tracking_mock`) con el formato de Persona 1 |
| Frase de cada momento | **Texto de ejemplo**; la narración real es de Persona 3 |

La página marca cada parte simulada.

## Regenerar

Desde la raíz del repositorio:

```bash
python apps/backend/scripts/export_analytics_demo.py
```

`plantilla.html` contiene la página y `export_analytics_demo.py` le inserta los datos. La prueba `test_saved_dashboard_contains_current_engine_output` falla si `tablero.html` quedó desactualizado.

## Guion sugerido para presentar avances (5 minutos)

1. **El problema (30 s).** El marcador no explica el partido. Persona 2 convierte eventos en estado, cifras trazables y momentos que merecen atención.
2. **Reproducción (1 min).** Iniciar en 0 a 10×. Mostrar cómo cambian marcador, posesión y el campo. Detenerse a los 190 s: aparece la presión sostenida de Río.
3. **Por qué importa (1 min).** Abrir el gol de Aurora (07:51). Mostrar la prioridad como suma de motivos, los hechos con fórmula y versión, los eventos de origen marcados en el campo y lo que los datos no permiten afirmar.
4. **Ritmo (45 s).** Señalar en los gráficos el cambio de control hacia Río y la fase de caos con su umbral. Recordar que son indicadores propios del equipo, con sus componentes visibles.
5. **Personalización (45 s).** Cambiar el perfil a casual, analista, afición de Río y modo jugador: los hechos son los mismos, pero cambian la selección y la prioridad. El bloque «El mismo partido para cada espectador» lo resume.
6. **Seguimiento (30 s).** Mostrar distancias y velocidades por jugador y los avisos por umbral. Aclarar que hoy son observaciones simuladas y que el mismo módulo recibirá las observaciones reales de vídeo de Persona 1.
7. **Estado y próximos pasos (30 s).** Bloque «Qué está listo»: despliegue en Azure, observaciones reales de vídeo de Persona 1, entrenamiento de xT y xG con datos con licencia.
