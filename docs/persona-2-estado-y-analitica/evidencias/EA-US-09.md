# Evidencia técnica de EA-US-09

## Identificación

- **Historia:** EA-US-09 · Entregar ejemplos e integrar con Persona 3 y 4.
- **Estado:** verificada localmente; integración probada en una copia de la rama de Persona 4.
- **Prioridad:** P0.
- **Última verificación:** 9 de octubre de 2026.
- **Responsable:** Persona 2 · Estado y analítica.
- **Requisitos relacionados:** contratos de trabajo, RNF-04.

## Objetivo comprobado

Persona 3 y Persona 4 tienen ejemplos de cada contrato generados desde el código, y `MatchAnalytics` reemplaza la analítica provisional de Persona 4 sin cambiar sus rutas.

## Ejemplos

En [`ejemplos/`](../ejemplos/):

| Archivo | Contenido |
|---|---|
| `match-snapshot-v1.valido.json` | Snapshot final del partido de aceptación |
| `match-snapshot-v1.sin-opcionales.json` | Solo los campos obligatorios |
| `match-snapshot-v1.invalido.json` | Sin marcador y con una métrica disponible sin valor |
| `insight-candidate-v1.valido.json` | Gol del partido de aceptación con hechos, límites y motivos |
| `insight-candidate-v1.sin-opcionales.json` | Solo los campos obligatorios |
| `insight-candidate-v1.invalido.json` | Prioridad 120 y sin eventos de origen |
| `attention-decision-v1.descartado.json` | Un momento descartado con sus motivos |
| `partido-aceptacion.analitica.json` | Snapshot final, evolución del estado, jugadas, notas, momentos y decisiones por perfil |
| `escenario-analitica.analitica.json` | Lo mismo para el escenario de 178 eventos |

## Integración con Persona 4

En una copia temporal de `origin/persona-4/api-frontend` (`ce8b1e3`) se copiaron los archivos de Persona 2 y se hicieron los dos cambios descritos en el [README](../README.md#cómo-integrarlo-con-persona-4). Resultado:

```text
2 failed, 240 passed
```

Las dos pruebas que fallan dependen de la analítica provisional:

- `test_favorite_player_raises_priority_only_when_involved` busca `moment-evt-006`; el momento real con `aurora-8` es `moment-evt-009`.
- `test_language_changes_text_not_facts` falla porque la narración provisional no tiene plantillas para los tipos nuevos.

La rama de Persona 4 no se modificó.

## Cobertura de criterios

| Criterio | Evidencia | Estado |
|---|---|---|
| Válido, sin opcionales e inválido | `test_contract_examples_validate_as_documented` | Cumplido |
| Ejemplos al día con el código | `test_examples_are_current_with_the_code` | Cumplido |
| Campos que lee Persona 4 | `test_valid_examples_keep_the_fields_persona_4_reads` | Cumplido |
| `MatchAnalytics` cumple `AnalyticsPort` | Prueba de integración en la copia de la rama de Persona 4 | Cumplido con 2 ajustes pendientes en Persona 4 |

## Reproducción

```bash
.venv/Scripts/python -m pytest apps/backend/tests/test_analytics_contract_examples.py -q
python apps/backend/scripts/export_analytics_examples.py
```

## Resultado

```text
5 passed
```

## Dependencias

- Persona 4: aplicar los dos cambios de integración y ajustar las dos pruebas.
- Persona 3: cubrir los diez tipos de momento en la narración.
