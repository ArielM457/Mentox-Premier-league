# SDD-02 · Estado y analítica

## Especificación

**Objetivo:** transformar eventos aceptados en estado, estadísticas, patrones y momentos con evidencia que otra capa pueda explicar sin inventar cifras.

**Entradas:** eventos, metadatos, tiempo de consulta, preferencias y seguimiento opcional. **Salidas:** `MatchSnapshot`, métricas, `InsightCandidate`, decisiones de atención y comparaciones locales.

Requisitos relacionados: RF-07 a RF-12, RF-14 a RF-17, RF-28 a RF-33 y los requisitos de estadísticas y vista táctica del [catálogo](requisitos.md).

### Criterios de aceptación

1. Marcador y estadísticas coinciden con la secuencia aceptada hasta el tiempo consultado.
2. Las métricas conservan unidad, disponibilidad, versión de fórmula y eventos de origen.
3. Un dato ausente se expresa como no disponible; no se transforma en cero para aparentar cobertura.
4. Cada patrón tiene casos positivos y negativos y explicita sus límites.
5. Los modos cambian la selección de momentos sin alterar los hechos calculados.
6. Una comparación simulada no modifica el estado original ni presenta probabilidades sin modelo validado.

## Diseño implementado

`domain/analytics/` contiene estado, estadísticas, indicadores, patrones, secuencias, hitos y seguimiento. `application/analytics/pipeline.py` reúne el motor; `presentation.py` adapta su salida a la experiencia HTTP y `moment_analysis.py` prepara explicaciones del momento.

`ANALYTICS_ENGINE=provisional` mantiene la salida inicial de la demo. `persona2` selecciona `MatchAnalytics` mediante `PresentationAnalytics`. La elección ocurre en `adapters/http/registry.py`; instalar el backend no cambia ese valor por sí solo.

El seguimiento sintético declara su procedencia. Los adaptadores de xG, xT y VAEP viven en `adapters/models/`; sus resultados dependen de modelos y configuración disponibles. Su presencia no demuestra que todas las métricas estén activas en la API.

`domain/analytics/what_if.py` contiene comparaciones reproducibles. Se presentan como estimación o simulación local, no como hechos ni como una predicción garantizada de IA.

## Tareas y estado

- [x] Implementar estado y estadísticas deterministas.
- [x] Agregar patrones, secuencias, atención e hitos con fuentes.
- [x] Adaptar analítica a los contratos consumidos por la experiencia.
- [x] Preparar seguimiento y comparación táctica local.
- [x] Mantener ejemplos de contratos en `apps/backend/tests/fixtures/contracts/analytics/`.
- [x] Separar el tablero reproducible en `experiments/analytics-demo/`.
- [ ] Validar modelos de valor y métricas que requieren seguimiento real en el entorno objetivo.
- [ ] Completar un índice de dificultad del pase si se exige: la existencia de precisión/distancia no lo sustituye.
- [ ] Medir calidad de patrones y latencia con datos autorizados representativos.

## Validación

Las pruebas `test_analytics_*.py` cubren estado, fórmulas, patrones, seguimiento, atención, contratos, modelos y demo. `test_analytics_contract_examples.py` compara los ejemplos con el código; `test_analytics_demo.py` comprueba el HTML generado.

Los scripts `export_analytics_examples.py` y `export_analytics_demo.py`, en `apps/backend/scripts/`, regeneran los recursos. Las rutas nuevas deben funcionar en un clon sin `docs-anteirores/`.
