# DV-US-28 · Integrar visión con la aplicación oficial

## Resultado

Implementada en `integration/persona1-main-20261023`. Se incorporaron 33 commits de `origin/main` sin eliminar el trabajo de Persona 1. El frontend oficial consume la línea de tiempo de visión desde el backend común.

## Criterios cubiertos

- El backend registra contratos, narrativa, agentes, partido y visión.
- Play, pausa, salto y reinicio notifican al reproductor de observaciones.
- `Visión IA` muestra Roboflow, SoccerNet y candidatos sincronizados.
- La interfaz distingue observaciones experimentales de hechos publicados.
- La falta de artefactos no rompe el partido sintético.
- No se promueve un candidato a `MatchEvent` sin evidencia suficiente.

## Archivos

- `apps/backend/src/match_intelligence/main.py`
- `apps/backend/src/match_intelligence/application/vision_runtime.py`
- `apps/frontend/src/api/client.js`
- `apps/frontend/src/screens/MatchCenter.jsx`
- `apps/frontend/src/components/match/LiveExperiencePanels.jsx`
- `apps/frontend/src/i18n/strings.js`
- `apps/frontend/src/styles/experience.css`

## Verificación

`npm run build:frontend` aprobó. `npm run lint:frontend` aprobó con tres advertencias preexistentes. Las 26 pruebas aisladas de integración de Persona 1 aprobaron.

La suite HTTP combinada no se marca como aprobada: en el entorno resuelto, mezclar pruebas que importan `httpx.AsyncClient` y `fastapi.testclient.TestClient` puede bloquear el proceso. Falta normalizar las pruebas HTTP a un solo cliente.

## Azure y límites

La arquitectura de tres rutas ya estaba propuesta en `main`, pero no desplegada. Esta entrega no creó Service Bus, API Management ni costos adicionales. La vista usa inferencias calculadas previamente y publica cero `MatchEvent` de visión.
