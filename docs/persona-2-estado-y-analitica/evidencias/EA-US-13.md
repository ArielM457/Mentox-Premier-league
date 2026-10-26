# Evidencia técnica de EA-US-13

## Identificación

- **Historia:** EA-US-13 · Explicar un momento con datos en el resumen.
- **Estado:** verificada localmente y en Azure: el análisis de un momento responde a través de la interfaz desplegada (imagen `0635142`).
- **Prioridad:** P1.
- **Última verificación:** 25 de octubre de 2026.
- **Responsable:** Persona 2 · Estado y analítica (con cambios acotados en la pestaña Resumen de Persona 4).
- **Requisitos relacionados:** RF-14 (motivos visibles), RF-23 y RF-36 (detalle según el perfil), RF-11 y RF-12 (seguimiento).

## Objetivo comprobado

Antes, la pestaña Resumen mostraba:

- el titular del momento;
- una cancha con una formación fija;
- un «resultado estimado» que era el mismo texto para cualquier momento.

Ahora muestra lo que calcula la analítica:

- por qué el motor eligió el momento;
- sus cifras;
- las posiciones del instante;
- cuatro lecturas alternativas medidas.

Las reglas están en [reglas de jugadas, patrones y atención](../reglas-de-patrones-y-atencion.md), en la sección `what_if@1`.

## Cambios técnicos

| Archivo | Cambio |
|---|---|
| `domain/analytics/what_if.py` | `what_if@1`: posiciones de un instante con tolerancia de 0,3 s, cuadro para la cancha y las cuatro lecturas |
| `application/analytics/moment_analysis.py` | `MomentAnalysis`: motivos y prioridad del perfil, hechos, posiciones y lecturas, solo con eventos hasta el momento |
| `adapters/http/analytics_router.py` y `main.py` | `GET /api/v1/matches/{id}/moments/{candidate_id}/analysis` |
| `application/match_session.py` | `track_set()` deja disponibles las pistas del partido |
| `apps/frontend/src/components/match/LiveExperiencePanels.jsx` | `MomentWorkspace` carga el análisis y muestra motivos, datos medidos y la comparación de cada alternativa |
| `apps/frontend/src/components/match/Pitch.jsx` | Posiciones reales opcionales y jugadores marcados de la alternativa |
| `apps/frontend/src/i18n/strings.js`, `api/client.js`, estilos | Textos en español e inglés con números según el idioma, llamada a la API y estilos |
| `postman/` | Petición nueva en la colección |
| `apps/backend/Dockerfile` | El código conserva la estructura del repositorio y se copia `data/`: la previa táctica encuentra su archivo y la ruta de integración puede ubicar la raíz |

## Cobertura de criterios

| Criterio | Evidencia | Estado |
|---|---|---|
| Motivos, prioridad y hechos del momento | `test_moment_analysis_uses_only_events_until_the_moment`; en el navegador, una progresión rápida del partido en vivo mostró prioridad 70 con sus cuatro motivos y cinco cifras | Cumplido |
| Posiciones reales del instante | La respuesta trae 24 posiciones y la cancha las usa; con el apoyo se marcan el poseedor y el compañero | Cumplido |
| Cifras real y alternativa, o motivo si no aplica | Pruebas de `test_analytics_what_if.py` con geometría conocida; en el navegador, «El remate salía antes» muestra «No aplica a este momento» en una progresión sin remate | Cumplido |
| Sin eventos futuros y con origen declarado | `test_moment_analysis_uses_only_events_until_the_moment`; cada lectura lleva `tracking_evidence` y avisa que las posiciones son simuladas | Cumplido |
| Funciona con los dos motores | `test_moment_analysis_route_works_with_both_engines` | Cumplido |
| Imagen de Docker | La API en el contenedor respondió 200 al análisis, al seguimiento y a la previa con su archivo real | Cumplido en local |

## Reproducción

```bash
.venv/Scripts/python -m pytest apps/backend/tests/test_analytics_what_if.py -q
npm run build:frontend
```

## Resultado

```text
8 passed
Suite completa: 412 passed, 8 skipped, 10 failed; las 10 fallas ya ocurren en main (visión de Persona 1 y las peticiones de Postman que la cubren)
```

## Limitaciones

- Las posiciones son simuladas: las lecturas muestran el método, no mediciones.
- Si el motor de Persona 2 no ve un momento en ese evento, la pantalla muestra solo las posiciones y las lecturas.
- No hubo verificación visual con capturas: el panel del navegador estaba oculto durante la prueba. Se comprobaron el texto, el estado y los estilos calculados.
