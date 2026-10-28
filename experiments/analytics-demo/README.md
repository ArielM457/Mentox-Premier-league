# Tablero analítico de demostración

`plantilla.html` y `tablero.html` se conservaron desde la documentación histórica. El tablero permite inspeccionar estadísticas y momentos de los escenarios sintéticos; su seguimiento está marcado como simulado.

Desde la raíz y con el entorno Python del backend activo:

```powershell
python apps/backend/scripts/export_analytics_demo.py
```

Abrir `experiments/analytics-demo/tablero.html` en el navegador. `test_analytics_demo.py` compara la página con el motor y la plantilla. La generación de ejemplos de contratos es independiente y escribe en `apps/backend/tests/fixtures/contracts/analytics/`.

Este tablero es una herramienta de desarrollo, separada del frontend de producto. Consultar la [especificación de analítica](../../docs/desarrollo/02-estado-y-analitica.md).
