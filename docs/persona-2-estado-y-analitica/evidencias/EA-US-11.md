# Evidencia técnica de EA-US-11

## Identificación

- **Historia:** EA-US-11 · Presentar la analítica en un tablero.
- **Estado:** verificada localmente.
- **Prioridad:** P1.
- **Última verificación:** 11 de octubre de 2026.
- **Responsable:** Persona 2 · Estado y analítica.

## Objetivo comprobado

[`demo/tablero.html`](../demo/tablero.html) reproduce el escenario de 178 eventos y muestra marcador, posesión, campo con seguimiento, control, impulso y caos en el tiempo, cifras por equipo y jugador, momentos por perfil con sus motivos y hechos, avisos de seguimiento y el estado de cada etapa. Todo sale del motor; las posiciones y las frases de cada momento están marcadas como simuladas.

## Cambios técnicos

| Archivo | Cambio |
|---|---|
| `adapters/sources/analytics_demo.py` | Datos del tablero desde `MatchAnalytics`, `MatchAnalyzer`, `build_snapshot` y el seguimiento |
| `scripts/export_analytics_demo.py` | Inserta los datos en la plantilla y escribe el tablero |
| `docs/persona-2-estado-y-analitica/demo/plantilla.html` | Página: HTML, CSS y JavaScript sin dependencias externas salvo las fuentes |
| `docs/persona-2-estado-y-analitica/demo/tablero.html` | Tablero generado (unos 436 KB) |
| `docs/persona-2-estado-y-analitica/demo/README.md` | Qué es real y qué es simulado, cómo regenerarlo y guion de presentación |

## Decisiones técnicas

- El seguimiento se submuestrea a 1 Hz en la página y se interpola entre cuadros para que la reproducción sea fluida.
- Los colores de los equipos y del índice de caos se validaron para daltonismo con el script de la guía de visualización, en modo claro y oscuro. El violeta inicial del caos se confundía con el azul de Río en modo oscuro y se cambió por verde agua.
- La página abre justo después del gol de Aurora con ese momento seleccionado, para que se entienda sin reproducir.

## Cobertura de criterios

| Criterio | Evidencia | Estado |
|---|---|---|
| Cifras, momentos y motivos del motor real | `test_demo_data_comes_from_the_engine_and_labels_the_mock` (los momentos emitidos del perfil casual coinciden con `MatchAnalytics.candidates`) | Cumplido |
| Lo simulado está marcado | La misma prueba comprueba `simulated_fixture`; la página lo indica en el campo, la tabla, los avisos y cada frase | Cumplido |
| Regeneración comprobada | `test_saved_dashboard_contains_current_engine_output` | Cumplido |

## Reproducción

```bash
python apps/backend/scripts/export_analytics_demo.py
.venv/Scripts/python -m pytest apps/backend/tests/test_analytics_demo.py -q
```

## Resultado

```text
2 passed
```

Revisión visual en el navegador integrado, en modo oscuro y a escritorio: sin errores de consola. Se corrigieron la celda de pases que se partía en dos líneas, la cabecera de equipos y la falta de marcas de tiempo en los gráficos.

## Limitaciones y riesgos

- No es la interfaz del producto: la experiencia final es de Persona 4 y el diseño, de Persona 5.
- Las frases de cada momento son plantillas de ejemplo, no la narración de Persona 3.
- No se revisó la página a ancho de teléfono en esta verificación.
