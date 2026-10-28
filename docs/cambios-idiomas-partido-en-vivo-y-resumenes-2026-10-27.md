# Idiomas, partido en vivo y resúmenes

## Resultado

Actualizamos The Prime Moment para simplificar los controles superiores y mantener una experiencia consistente entre un partido en curso y un partido finalizado.

## Cambios realizados

- La aplicación comienza en inglés para una sesión nueva o restablecida.
- El control de idioma es un único selector con español, inglés, alemán, chino, hindi, francés y portugués.
- Los textos visibles de partidos ya no usan la palabra “simulación”.
- La barra del Centro del Partido muestra “Partido en vivo” e “Iniciar partido”.
- Quitamos el selector de perfil de esa barra porque el perfil se elige durante la configuración.
- El asistente se abre y se cierra con una flecha alineada con las pestañas. La flecha solo aparece en Partido.
- Los filtros y contadores de Partidos usan texto blanco en el tema oscuro.
- El resumen de un partido finalizado reutiliza el selector compacto, el jugador condicional, el momento seleccionado, el análisis y la lista de situaciones del resumen del partido.
- La cabecera del resumen usa una ilustración profesional guardada dentro del frontend.

## Archivos principales

- `apps/frontend/src/components/ui/LanguageSwitch.jsx`
- `apps/frontend/src/app/preferences.js`
- `apps/frontend/src/screens/MatchCenter.jsx`
- `apps/frontend/src/screens/Recap.jsx`
- `apps/frontend/src/i18n/strings.js`
- `apps/frontend/public/images/match-recap-professional.png`
- `apps/frontend/src/styles/landing.css`
- `apps/frontend/src/styles/layout.css`
- `apps/frontend/src/styles/match.css`
- `apps/frontend/src/styles/recap-profile.css`
- `apps/frontend/src/styles/theme.css`
- `docs/03-requisitos.md`

## Pruebas ejecutadas

```powershell
cd F:\Proyectos\Premier-league\apps\frontend
npm run lint
npm run build
```

El lint y la comprobación de traducciones terminaron correctamente. Se conservaron dos advertencias anteriores en `useCatalog.js` y `MomentDetail.jsx`. La comprobación encontró 721 claves equivalentes en español e inglés.

La compilación de producción terminó correctamente con Vite 8.3.3, transformó 72 módulos y generó los archivos de `dist`.

## Límites de la validación

- No se modificaron contenedores, servicios de Azure ni colecciones de Postman.
- El lint y la compilación validan la integración del código, pero la revisión visual final en un navegador sigue pendiente.
