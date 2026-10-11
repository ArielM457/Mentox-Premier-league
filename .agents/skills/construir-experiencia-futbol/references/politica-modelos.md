# Política operativa de modelos

Aplica estas reglas al planear o implementar IA en este repositorio.

## Asignación base

- Usa código determinista para filtro, estado, métricas, catálogo, refinamiento, deduplicación y comprobaciones exactas.
- Usa GPT-4.1 mini para orquestación semántica, selección de momentos y validación de coherencia breve.
- Usa GPT-4.1 para narración, explicación de peligro, redacción contrafactual, respuestas complejas, resúmenes, investigación y validación de fuentes.
- Usa GPT-4.1 mini en respuestas directas y GPT-4.1 cuando haya varias evidencias o calidad editorial.
- Trata GPT-4o mini como alternativa de contingencia tras una evaluación, no como modelo inicial.
- No uses GPT-4 original en una integración nueva.

## Búsqueda y recuperación

- Para investigación web, usa GPT-4.1 con la herramienta `web_search` de Responses API.
- Evalúa `gpt-5-search-api` solo si la integración necesita Chat Completions y búsqueda obligatoria.
- Reserva investigación profunda para informes programados. Comprueba el modelo vigente antes de configurarla.
- No uses modelos search preview retirados.
- Usa embeddings solo para recuperación semántica de contenido interno aprobado. No los presentes como búsqueda web ni como verificación de vigencia.

## Evaluación

- Prueba cada modelo con solicitudes representativas del agente.
- Mide esquema, evidencia, naturalidad, selección, fuentes, latencia y coste.
- Ajusta primero el contexto y las instrucciones.
- Sube a GPT-4.1 si GPT-4.1 mini no alcanza la calidad.
- Baja a GPT-4.1 mini solo si mantiene la calidad requerida.
- Registra el resultado por agente. No cambies todos los agentes de forma automática.

## Integración

- Mantén separados los despliegues de clasificación y narrativa.
- Configura nombres de despliegue y credenciales mediante variables de entorno.
- Encapsula búsqueda y proveedor de modelos detrás de adaptadores.
- Verifica disponibilidad, región, cuota y compatibilidad de herramientas en el entorno real antes de declarar la integración completa.
