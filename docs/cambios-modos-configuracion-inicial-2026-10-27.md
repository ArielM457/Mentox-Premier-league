# **Modos en la configuración inicial**

## **Resultado**

Actualizamos el paso Visualización de la configuración inicial de The Prime Moment.

Al seleccionar un modo, su tarjeta se expande y muestra tres ejemplos concretos de lo que la persona podrá ver. Las demás tarjetas conservan su tamaño normal. El contenido cambia para Aficionado, Analista, Analista profesional y Centrado en jugador.

Quitamos la sección “Resumen de tu experiencia”. Después de elegir el modo, la persona puede terminar directamente con el botón “Explorar partidos”. Las preferencias se siguen guardando de la misma manera.

## **Idiomas**

Los detalles nuevos están disponibles en español, inglés, alemán, chino, hindi, francés y portugués.

## **Archivos modificados**

- `apps/frontend/src/screens/Onboarding.jsx`: expansión de la tarjeta elegida y eliminación del resumen repetido.
- `apps/frontend/src/styles/onboarding.css`: tamaño, transición y lista de capacidades.
- `apps/frontend/src/i18n/strings.js`: contenido de cada modo en todos los idiomas.
- `docs/03-requisitos.md`: requisito RF-94.

## **Pruebas**

```powershell
cd F:\Proyectos\Premier-league\apps\frontend
npm run lint
npm run build
```

La revisión visual final en navegador sigue siendo manual.

## **Límites**

- No cambiamos el backend.
- No creamos contenedores.
- No regeneramos colecciones de Postman.
