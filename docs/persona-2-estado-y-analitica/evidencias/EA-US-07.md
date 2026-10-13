# Evidencia técnica de EA-US-07

## Identificación

- **Historia:** EA-US-07 · Evaluar xT, VAEP y xG sin presentar valores sin validar.
- **Estado:** adaptadores verificados localmente; los tres modelos están desactivados.
- **Prioridad:** P1.
- **Última verificación:** 9 de octubre de 2026.
- **Responsable:** Persona 2 · Estado y analítica.

## Objetivo comprobado

El puerto `ValueModelRegistry` publica xT, xG y VAEP solo con un modelo activado por procedencia y plausibilidad. Sin modelo, la cifra sale no disponible con el motivo. El análisis completo está en el [informe de viabilidad](../informe-modelos-de-valor.md).

## Alcance implementado

- Puerto y registro de modelos sin dependencias externas.
- xT: cuadrícula con controles de plausibilidad, valor de pases y entrenador por iteración de valor.
- xG: regresión logística de distancia y ángulo, ajuste por Newton-Raphson, informe de calibración y controles de plausibilidad.
- VAEP: conversión a acciones tipo SPADL, medición de cobertura y estado siempre desactivado.
- Carga desde una carpeta local o desde Blob Storage (`models/<modelo>/current.json`).

## Fuera del alcance

- Descargar o entrenar con datos reales: falta elegir un conjunto con licencia adecuada.

## Cambios técnicos

| Archivo | Cambio |
|---|---|
| `application/analytics/value_models.py` | Puerto, estado, procedencia y registro |
| `adapters/models/expected_threat.py` | xT |
| `adapters/models/expected_goals.py` | xG |
| `adapters/models/vaep.py` | VAEP y conversión SPADL |
| `adapters/models/loader.py` | Carga local y desde Azure Blob |

## Cobertura de criterios

| Criterio | Evidencia | Estado |
|---|---|---|
| Sin modelo, no disponible con motivo | `test_without_validated_models_the_metrics_are_disabled_not_invented` | Cumplido |
| xT contra referencia analítica | `test_xt_value_iteration_matches_the_analytic_reference` | Cumplido |
| xG contra coeficientes conocidos y calibración | `test_xg_fit_recovers_known_coefficients_and_is_calibrated` | Cumplido |
| Plausibilidad | `test_xt_grid_plausibility_and_provenance_gate_the_model`, `test_xg_plausibility_rejects_inverted_models` | Cumplido |
| Sin procedencia o solo sintético no se activa | `test_xt_grid_plausibility_and_provenance_gate_the_model` | Cumplido |
| Activado, aparece en momentos y totales | `test_enabled_xt_values_passes_and_appears_in_fast_progressions`, `test_enabled_xg_adds_probability_to_shot_moments_and_team_totals` | Cumplido |
| VAEP desactivado con la brecha medida | `test_vaep_stays_disabled_and_reports_the_data_gap` | Cumplido |

## Reproducción

```bash
.venv/Scripts/python -m pytest apps/backend/tests/test_analytics_value_models.py -q
```

## Resultado

```text
8 passed
```

## Limitaciones y riesgos

- Un xG solo geométrico es menos preciso que los modelos con parte del cuerpo y contexto; debe presentarse como tal.
- El xT con pases pierde el valor de las conducciones.
- La carga desde Blob no se probó contra Azure.

## Dependencias

- Equipo: elegir y revisar la licencia de los datos de entrenamiento, excluyendo la Premier League.
