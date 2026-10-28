# Perfil Analista profesional

## Resultado

The Prime Moment ahora tiene un cuarto perfil llamado **Analista profesional**.

Este perfil aparece en la página de inicio, la configuración inicial, Preferencias y el selector rápido del Centro del Partido. Su descripción explica que incluye una vista inclinada, narración completa y datos avanzados.

Al elegirlo se activa automáticamente el nivel avanzado y se mantienen encendidos los comentarios en vivo. El backend acepta `professional_analyst` como valor del contrato y puede seleccionar hasta tres hechos cuando la evidencia disponible los contiene. No se inventan cifras para completar ese límite.

## Perspectiva del campo

Los perfiles **Analista** y **Analista profesional** muestran una perspectiva media de 10 grados en escritorio y 7 grados en móvil.

La inclinación se aplica en:

- El campo del partido en vivo o reproducido.
- El campo principal de Resumen.
- Los campos pequeños de la lista de momentos.
- La vista previa de comentarios.
- El detalle completo de un momento.

La transformación solo afecta al campo. La barra de reproducción, el narrador, los comentarios, los botones y los textos permanecen planos y legibles. Los perfiles Aficionado y Centrado en jugador conservan la vista 2D.

## Idiomas

El nombre y la descripción del nuevo perfil están disponibles en español, inglés, alemán, chino, hindi, francés y portugués.

## Archivos principales

- `apps/backend/src/match_intelligence/domain/presentation.py`: nuevo valor del contrato y nivel avanzado obligatorio.
- `apps/backend/src/match_intelligence/application/narrative/`: contrato, selección de hechos y demostración por línea de comandos.
- `apps/frontend/src/screens/Onboarding.jsx`: cuarto perfil en la configuración inicial.
- `apps/frontend/src/screens/Profile.jsx`: selección y persistencia en Preferencias.
- `apps/frontend/src/screens/MatchCenter.jsx`: selector rápido y clase de perspectiva para Partido y Resumen.
- `apps/frontend/src/screens/MomentDetail.jsx`: perspectiva en el detalle del momento.
- `apps/frontend/src/i18n/strings.js`: nombre y descripción en siete idiomas.
- `apps/frontend/src/styles/ux.css`: inclinación media y ajuste móvil.

## Pruebas ejecutadas

### Backend

Comando:

```powershell
cd F:\Proyectos\Premier-league\apps\backend
uv run pytest tests/test_narrative.py tests/test_match_experience_api.py tests/test_analytics_presentation.py -q
```

Resultado: **76 pruebas aprobadas**. Aparecieron 14 advertencias de dependencias externas de CrewAI y Pydantic; no hubo errores.

Las pruebas nuevas comprueban que:

- El contrato acepta `professional_analyst`.
- El perfil fuerza `advanced` aunque se solicite `simple`.
- La API devuelve superposiciones con el modo y nivel correctos.
- La planificación mantiene una sola superposición visible.

### Frontend

Comandos:

```powershell
cd F:\Proyectos\Premier-league\apps\frontend
npm run lint
npm run build
```

Resultado: ambos comandos terminaron correctamente. Vite transformó 72 módulos. El lint conservó dos advertencias ya existentes sobre actualizaciones de estado dentro de efectos en `MomentDetail.jsx` y `useCatalog.js`.

## Límites

- La experiencia usa datos sintéticos, como exige el proyecto.
- El perfil profesional muestra más hechos solo cuando existen en la evidencia. No crea datos faltantes.
- No se crearon contenedores ni se regeneraron colecciones de Postman.
