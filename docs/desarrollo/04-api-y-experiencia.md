# SDD-04 · API y experiencia del partido

## Especificación

**Objetivo:** permitir descubrir, configurar, reproducir y entender un partido desde una interfaz conectada a contratos verificables.

**Entradas:** catálogo de partidos, preferencias, tiempo de reproducción y acciones del usuario. **Salidas:** pantallas, campo animado, mensajes, estadísticas, momentos, respuestas y resúmenes.

Requisitos relacionados: RF-18 a RF-28, RF-34 a RF-39, RF-52 a RF-63, RF-65 en adelante según el [catálogo](requisitos.md), y requisitos de personalización/accesibilidad.

### Criterios de aceptación

1. La API entrega eventos y métricas ocurridos hasta el tiempo solicitado, sin adelantar el futuro.
2. La sesión de reproducción conserva el reloj al cambiar de vista.
3. El campo muestra procedencia del seguimiento y no cambia hechos por una preferencia.
4. Seleccionar un momento permite consultar sus datos y eventos de origen.
5. La preferencia de idioma, club, jugador, modo y detalle puede guardarse en el navegador.
6. La vista de preferencias muestra cuatro tarjetas cuadradas juntas, conserva escudo/foto y abre sus opciones debajo.
7. Los mensajes importantes siguen siendo legibles y los controles se pueden activar con teclado.

## Diseño implementado

`application/match_session.py` coordina analítica, narrativa, reproducción, resumen y editorial. `adapters/http/match_router.py` expone sus operaciones; los demás routers separan sistema, analítica, narrativa, comunidad e integración.

React organiza cada pantalla en `src/screens/`, usa componentes compartidos, preferencias mediante contexto y rutas hash en `src/app/router.js`. `src/api/client.js` centraliza peticiones y errores. El proxy de Vite mantiene `/api` en un solo origen de desarrollo.

La previa usa metadatos y datos sintéticos estructurados, formaciones y secuencias reproducibles. El centro del partido mantiene reloj y canales mediante hooks. Los modos profesional y jugador tienen condiciones específicas: el profesional fuerza nivel avanzado/comentarios; jugador requiere un jugador seleccionado.

Los tokens y estilos de `src/styles/` soportan temas claro y oscuro. Los escudos y fotos se resuelven con `src/data/branding.js`; son recursos visuales asignados a identidades sintéticas, no prueba de identidad real.

## Tareas y estado

- [x] Exponer sesiones, eventos, estado, overlays, preguntas y resumen.
- [x] Incorporar navegación, preferencias, idiomas y pantallas de producto.
- [x] Integrar campo, estadísticas, vista táctica, momentos y previa.
- [x] Mantener imágenes de club y jugador en Preferencias.
- [x] El 28 de octubre: convertir las cuatro opciones en tarjetas cuadradas, en una fila con desplazamiento horizontal en pantallas pequeñas.
- [x] El 28 de octubre: eliminar la barra inicial de resumen de preferencias.
- [ ] Completar revisión visual de todos los idiomas y textos largos.
- [ ] Validar accesibilidad y navegación de extremo a extremo sobre todos los tamaños de pantalla objetivo.
- [ ] Verificar la experiencia con los proveedores y transportes remotos habilitados.

## Validación

`test_match_experience_api.py` cubre contratos, tiempo, personalización, fuentes y operaciones del partido. `test_live_tracking_api.py`, `test_live_simulation.py`, `test_action_callouts.py` y `test_frontend_kind_labels.py` cubren partes del recorrido.

El 28 se comprobaron en navegador cuatro tarjetas cuadradas en la misma fila en escritorio/móvil y el cambio de nivel. El frontend compiló después de recuperar imágenes y retirar el resumen superior. Eso no constituye una prueba completa de todas las pantallas.
