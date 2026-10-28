# **Distribución del Centro del Partido**

## **Resultado**

Reorganizamos la vista Partido de The Prime Moment para aprovechar mejor el ancho disponible.

En escritorio, el estadio queda alineado a la izquierda. La parte derecha contiene los comentarios en vivo y, debajo, un espacio propio para el momento actual, el selector y el acceso a los momentos ocurridos.

Los comentarios y las tarjetas de momentos ya no cubren a los jugadores ni las líneas del campo.

En pantallas de hasta 1050 píxeles, los paneles pasan debajo del estadio. En móvil se muestran en una sola columna para evitar desplazamiento horizontal.

## **Barra de reproducción**

La barra queda completamente oculta cuando no se usa. Aparece en estos casos:

- Al pasar el cursor por el reproductor.
- Al enfocar un control mediante el teclado.
- Siempre que el dispositivo no tenga cursor, como una pantalla táctil.

La etiqueta de la fuente del seguimiento vuelve al borde inferior cuando la barra está oculta y sube cuando aparecen los controles.

## **Archivos modificados**

- `apps/frontend/src/screens/MatchCenter.jsx`: nueva distribución de estadio, comentarios y momentos.
- `apps/frontend/src/styles/match.css`: cuadrícula principal y panel derecho.
- `apps/frontend/src/styles/ux.css`: barra oculta, aparición por interacción y ajustes adaptables.
- `docs/03-requisitos.md`: requisitos RF-90 y RF-91.

## **Pruebas ejecutadas**

```powershell
cd F:\Proyectos\Premier-league\apps\frontend
npm run lint
npm run build
```

El lint terminó correctamente y conservó dos advertencias anteriores en `useCatalog.js` y `MomentDetail.jsx`. La comprobación de idiomas mantuvo 716 claves equivalentes entre español e inglés.

La compilación de producción terminó correctamente con Vite 8.3.3 y transformó 72 módulos.

También iniciamos Vite y comprobamos la respuesta de la API local con los tres partidos sintéticos. La captura automática no se pudo generar porque Chrome y Edge no iniciaron su modo sin interfaz en este entorno. Por este motivo no presentamos una captura nueva como evidencia visual.

## **Límites**

- No cambiamos eventos, narraciones ni contratos del backend.
- No creamos contenedores.
- No regeneramos colecciones de Postman.
