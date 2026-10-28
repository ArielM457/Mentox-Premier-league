# Resultados precomputados de visión

Estos tres JSON proceden del lote `mentox-modelos-20261023T045413Z`, antes guardado bajo `docs/`. Se trasladaron a datos del backend el 28 de octubre de 2026 para que el empaquetado no dependa del archivo documental ignorado.

- `roboflow-sports-predictions.json`: detecciones espaciales.
- `soccernet-predictions.json`: acciones temporales.
- `dv-us-21-report-recalculado.json`: fusión recalculada de esas entradas.

Los dos archivos de predicciones tenían finales de línea CRLF en esta copia local. Se restauraron a LF para coincidir exactamente con los hashes ya registrados por la fusión, sin cambiar el contenido JSON. El informe se conservó byte a byte y los originales archivados permanecen intactos. `IntegratedPipeline` verifica esos hashes; `.gitattributes` evita nuevas conversiones de texto aquí.

El Dockerfile backend copia estos resultados y configura sus rutas. El pipeline local conserva rutas predeterminadas en `experiments/`; se puede seleccionar este lote mediante variables de entorno.

No contienen el vídeo original ni pesos de modelos. Los resultados no prueban una inferencia ejecutada hoy ni autorizan el uso de otro material. Consultar [datos y visión](../../../../docs/funcionamiento/datos-y-vision.md).
