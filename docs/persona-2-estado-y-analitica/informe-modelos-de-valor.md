# Informe de viabilidad de xT, VAEP y xG

Revisión del 9 de octubre de 2026. La regla de partida es la del plan: si faltan campos o un modelo no se puede validar, la métrica queda desactivada y no se presenta como xT, VAEP o xG.

## Resumen

| Modelo | Datos de `MatchEvent 1.0` | Pesos disponibles | Validación hecha | Estado |
|---|---|---|---|---|
| xT | Inicio y fin de pases y dirección de ataque. Faltan conducciones. | No. Hay que entrenar la cuadrícula con datos con licencia. | Algoritmo contra una referencia analítica y controles de plausibilidad | Adaptador listo, **desactivado** |
| xG | Posición del tiro y dirección. Faltan parte del cuerpo, tipo de asistencia, situación y posición del portero. | No. Hay que entrenar con tiros con licencia. | Recuperación de coeficientes conocidos, calibración y controles de plausibilidad | Adaptador listo, **desactivado** |
| VAEP | Insuficientes: falta `bodypart` y varios tipos de acción. | No | Medición de la brecha de datos | **Desactivado** |

Con el registro vacío, el snapshot publica `xt_added`, `xg` y `vaep` como no disponibles, con el motivo en `unavailable_reason`. Ningún momento incluye esas cifras (`test_without_validated_models_the_metrics_are_disabled_not_invented`).

## Por qué no entrenamos con nuestros datos sintéticos

Un modelo entrenado con eventos que generamos nosotros aprendería las reglas del generador, no el fútbol. Daría números con apariencia de xT o xG sin ninguna relación con la probabilidad real de gol. El control de procedencia rechaza un modelo entrenado solo con datos sintéticos si no tiene una comparación con una referencia externa.

Los datos sintéticos sí sirven para validar que la implementación es correcta: si generamos tiros con una probabilidad conocida, el ajuste debe recuperarla.

## xT (Expected Threat)

**Método.** Karun Singh (2019): el campo se divide en zonas y el valor de cada zona es la probabilidad de marcar desde ella, ya sea tirando o moviendo el balón a otra zona. Se resuelve por iteración de valor. La biblioteca socceraction (licencia MIT según su repositorio) implementa el mismo método sobre acciones SPADL con pandas. Lo reimplementamos en `adapters/models/expected_threat.py` sin dependencias para que el adaptador sea opcional.

**Entradas.** Inicio y fin de cada acción que mueve el balón, en coordenadas normalizadas por dirección de ataque, y los tiros con su resultado. `MatchEvent 1.0` trae pases con inicio y fin; no trae conducciones, así que el xT de un jugador que avanza con el balón se perdería.

**Valor de una acción.** `xT(zona final) − xT(zona inicial)` para pases `success`, publicado como `xt_added`.

**Validación hecha.**

- Referencia analítica de dos zonas: la zona A mueve el balón a B con éxito la mitad de las veces y B tira con 50 % de gol. El resultado exacto es xT(B) = 0,5 y xT(A) = 0,25. La implementación lo reproduce (`test_xt_value_iteration_matches_the_analytic_reference`).
- Controles de plausibilidad antes de activar una cuadrícula: valores entre 0 y 1, más amenaza junto a la portería rival que junto a la propia y máximo en las dos últimas columnas (`test_xt_grid_plausibility_and_provenance_gate_the_model`).
- Con una cuadrícula válida, los pases de una progresión rápida reciben `xt_added` con su versión de modelo (`test_enabled_xt_values_passes_and_appears_in_fast_progressions`).

**Falta.** Entrenar la cuadrícula con datos con licencia y compararla con una cuadrícula publicada como referencia de plausibilidad. La cuadrícula del artículo original de Singh no tiene una licencia explícita, así que no la incorporamos.

## xG (Expected Goals)

**Método.** Regresión logística con distancia y ángulo de tiro:

```text
p(gol) = 1 / (1 + exp(−(b0 + b1 · distancia_m + b2 · ángulo_rad)))
```

Es la forma más simple de xG basada en geometría. Los modelos de proveedores usan además parte del cuerpo, tipo de asistencia, situación de juego y posición del portero y defensores. Con `MatchEvent 1.0` solo es posible la versión geométrica, y así debe presentarse.

**Implementación.** `adapters/models/expected_goals.py`: ajuste por Newton-Raphson sin dependencias, informe de calibración (Brier, log-loss y diferencia máxima entre probabilidad media y tasa observada por tramo) y controles de plausibilidad.

**Validación hecha.**

- Con 6 000 tiros generados con coeficientes conocidos, el ajuste recupera el coeficiente de distancia con error menor que 0,02 y el de ángulo con error menor que 0,4. En 3 000 tiros nuevos, la diferencia máxima por tramo es menor que 0,05 (`test_xg_fit_recovers_known_coefficients_and_is_calibrated`).
- Controles de plausibilidad: la probabilidad baja con la distancia, sube con el ángulo, un tiro centrado desde 11 m está entre 0,2 y 0,9 y uno desde 30 m queda por debajo de 0,1 (`test_xg_plausibility_rejects_inverted_models`).
- Con coeficientes válidos, los tiros reciben `xg` y el total del equipo es la suma de sus tiros (`test_enabled_xg_adds_probability_to_shot_moments_and_team_totals`).

**Falta.** Coeficientes entrenados con tiros reales con licencia y validación fuera de muestra.

## VAEP

**Método.** Decroos et al. (2019): dos clasificadores estiman la probabilidad de marcar y de recibir gol en las próximas acciones; el valor de una acción es el cambio de esas probabilidades. socceraction lo implementa sobre SPADL y entrena con XGBoost u otros clasificadores.

**Brecha de datos.** `adapters/models/vaep.py` convierte nuestros eventos a acciones tipo SPADL y mide qué parte es representable:

- `pressure` y `possession_change` no tienen equivalente SPADL. En el partido de aceptación, 3 de 10 eventos quedan fuera (`test_vaep_stays_disabled_and_reports_the_data_gap`).
- `bodypart` no existe en `MatchEvent 1.0` y se marca `unknown`.
- Faltan tipos que VAEP usa: conducción, regate, centro, despeje, falta, saques y acciones del portero.
- Los clasificadores necesitan cientos de partidos con licencia para entrenarse y validarse.

**Conclusión.** VAEP no es viable con el formato actual. El adaptador queda siempre desactivado y explica los motivos.

## Cómo activar un modelo en Azure

1. Elegir un conjunto de datos con licencia que permita este uso y excluir los partidos de la Premier League. Candidatos por revisar: StatsBomb Open Data (con sus condiciones de atribución) y el conjunto público de eventos de Wyscout publicado por Pappalardo et al. (2019). Hay que confirmar la licencia de cada uno antes de descargarlos.
2. Entrenar con `train_expected_threat` o `fit_logistic_xg`, en local o como trabajo de Azure Machine Learning, y guardar el documento con `grid_document` o `coefficients_document`. El documento incluye fuente, licencia, datos de entrenamiento, versión y validación.
3. Subirlo a Blob Storage como `models/xt/current.json` o `models/xg/current.json`.
4. Ejecutar el procesador con `VALUE_MODELS_SOURCE=blob`. El registro vuelve a comprobar plausibilidad y procedencia al cargar; si algo falla, el modelo queda desactivado con el motivo.

Ningún dato de entrenamiento ni modelo real está incluido en el repositorio.
