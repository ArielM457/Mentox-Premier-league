# **Evidencia de previa táctica**

## **Alcance cubierto**

Implementamos RF-65 a RF-76 con datos sintéticos.

Descubrir separa los partidos por estado. Si el catálogo no contiene un partido en vivo, esa sección no se renderiza. La misma pantalla muestra el partido más reciente y el próximo partido. El próximo abre una ruta de previa.

La previa muestra ambos equipos, permite elegir tres posibles formaciones por equipo y actualiza las posiciones en la cancha. Cada equipo tiene un menú con cinco tácticas ofensivas. Cada reproducción usa trece fotogramas: doce contactos de balón con al menos cinco atacantes y el trayecto final del remate. También muestra a los dos conjuntos, al poseedor, la respuesta defensiva y el gol simulado.

Debajo de las tácticas se muestra un resumen por equipo. El usuario puede extenderlo y buscar resultados recientes, jugadores, lesiones, sanciones, claves tácticas y la alineación probable. Los datos proceden de un documento JSON local aprobado mientras Blob Storage está pendiente.

La vista táctica del centro del partido conserva la alineación inicial y presenta ambos equipos. El control superior permite cambiar entre Repetir y Simular. Repetir crea opciones con los eventos disponibles hasta el reloj actual y conserva `source_event_ids`. Simular reutiliza las cinco propuestas por equipo que entrega el agente.

Las simulaciones conservan el estado de cada jugador entre fotogramas y limitan su avance según su función. Cada formación y cada fotograma contienen once jugadores por equipo. El portero participa en la salida, los defensores mantienen una cobertura detrás del balón, los mediocampistas conectan líneas y los atacantes realizan los apoyos y rupturas de finalización. El rival completo ajusta sus líneas, acompaña el lado del balón y repliega conforme avanza la jugada. La superioridad por banda forma un triángulo y un 2 contra 1; el remate lejano mueve al rival y libera al delantero fuera del área; la presión alta mantiene una línea adelantada y compacta antes del ataque rápido.

Cada fotograma identifica a los participantes directos. La interfaz ilumina al poseedor, al receptor que prepara el apoyo, al participante anterior y a los dos defensores más cercanos. Los demás permanecen visibles con menor intensidad y se mueven como parte del bloque.

El centro del partido permite mostrar u ocultar el agente lateral y conserva esta elección en el navegador. Cuando el agente está abierto, las tarjetas de selección táctica se colocan encima del campo para evitar el desborde. Cuando está oculto, el campo recupera todo el ancho y las tarjetas pueden mantenerse a su lado.

Cada fotograma con posesión ubica el balón en la misma coordenada que el poseedor. La interfaz lo dibuja junto al borde del jugador para que ambos sean visibles y se entienda que está en sus pies. Un pase parte del pasador y termina en el receptor. El último fotograma del remate deja el balón sin poseedor en el arco. Esta regla se usa tanto en las propuestas de la previa como en la reconstrucción de eventos del partido en vivo.

Las tarjetas de Descubrir redujeron su altura. El próximo partido usa el color de Aurora FC a la izquierda, el color de Río Unido a la derecha y una separación diagonal negra en el centro.

## **Archivos principales**

- `apps/backend/src/match_intelligence/application/prematch_agent.py`
- `apps/backend/src/match_intelligence/adapters/http/match_router.py`
- `apps/backend/src/match_intelligence/adapters/http/match_schemas.py`
- `apps/frontend/src/screens/Discover.jsx`
- `apps/frontend/src/screens/PrematchPreview.jsx`
- `apps/frontend/src/components/match/TacticalSimulationPitch.jsx`
- `apps/frontend/src/components/match/LiveExperiencePanels.jsx`
- `apps/frontend/src/components/match/MatchCard.jsx`
- `apps/frontend/src/styles/prematch.css`
- `apps/backend/tests/test_match_experience_api.py`
- `apps/backend/data/prematch/synthetic-analytics-001.json`
- `docs/persona-4-api-y-frontend/documento-local-previa.md`

## **Decisiones**

El backend expone un contrato estructurado y no controla la interfaz. La versión inicial usa reglas deterministas para que el mismo partido produzca la misma propuesta. No usa información real de la Premier League ni afirma que una táctica ocurrirá. La previa periodística compartida se usó solo como referencia para organizar las secciones; sus hechos y nombres no se redistribuyen.

El catálogo marca el partido corto como finalizado, el escenario analítico como próximo y `synthetic-live-001` como `LIVE`. Descubrir muestra las tres secciones al mismo tiempo: En vivo, Partido más reciente y Próximo partido. La tarjeta en vivo abre el centro del partido y permite revisar Repetir y Simular sin cambiar los otros dos estados.

El partido en vivo usa el escenario completo de once jugadores por equipo. No reutiliza el escenario corto de cuatro jugadores, porque no permite representar las funciones, coberturas y marcas de un partido completo.

## **Base táctica consultada**

Se usaron materiales formativos oficiales de FIFA como referencia conceptual, sin importar datos de partidos reales:

- La superioridad por banda busca crear ventajas de 2 contra 1 o 3 contra 2 y mantener apoyos cercanos.
- La presión alta exige distancias cortas entre líneas, línea defensiva adelantada, coberturas y desplazamiento colectivo.

Fuentes: [creación de superioridades](https://www.fifatrainingcentre.com/en/practice/elite-sessions/in-possession/creating-and-exploiting-overloads.php), [presión alta](https://www.fifatrainingcentre.com/en/game/game-analysis/out-of-possession/high-press.php) y [defensa compacta](https://www.fifatrainingcentre.com/en/practice/talent-coach-programme/press-and-regain/8v7-team-game-compact-defending.php).

## **Comprobación**

```powershell
cd F:\Proyectos\Premier-league\apps\frontend
npm run lint
npm run build

cd F:\Proyectos\Premier-league\apps\backend
uv run pytest tests/test_match_experience_api.py -q
uv run pytest -q
```

Resultados del 23 de octubre de 2026:

- `npm run lint`: terminó sin errores y conservó tres advertencias preexistentes de estado dentro de efectos.
- `npm run build`: compiló 54 módulos correctamente.
- Prueba enfocada: 37 pruebas aprobadas.
- Las pruebas comprueban que el balón coincide con su poseedor, que hay doce contactos y al menos cinco participantes directos durante cada táctica, que el remate acaba sin poseedor en el arco y que cada cambio tarda como máximo un segundo.
- Las pruebas comprueban que el portero no abandona el primer cuarto del campo, que los defensores no superan la zona de cobertura y que el pasador continúa desde su última posición sin volver de golpe a la formación inicial.
- La API devuelve once jugadores por equipo y las diez tácticas con trece fotogramas. Cada fotograma conserva 22 identificadores únicos, identifica entre tres y cinco participantes directos y contiene movimiento para todos los jugadores durante la secuencia.
- En las seis tácticas, el siguiente receptor quedó a un máximo de 7,59 unidades del destino antes del pase; el pasador se desplazó como máximo 12 unidades después de soltarlo. El portero no superó la coordenada 17 y ningún defensor superó la 51 en el sentido del ataque.
- Suite completa del backend: 334 pruebas aprobadas.
- `git diff --check`: sin errores de espacios.
- Revisión visual en Chrome a 1440 píxeles: tarjetas de Descubrir y composición completa de la previa verificadas con frontend y API locales.
- Revisión visual del centro del partido en Chrome a 1440 píxeles: modo Repetir con jugadas de ambos equipos y modo Simular con movimiento del balón verificados.

## **Limitaciones**

Las simulaciones son propuestas deterministas y no estiman probabilidades. La información previa vive en un archivo local; la carga desde Blob Storage sigue pendiente. No se probó en un teléfono físico.

## **Actualización de 22 jugadores del 24 de octubre de 2026**

Sustituimos las plantillas reducidas por formaciones completas de once jugadores. Tanto Simular como Repetir conservan a los dos equipos, mueven los bloques de ataque y defensa y diferencian visualmente a los participantes directos de los apoyos y coberturas.

La respuesta del servidor local confirmó once jugadores por formación, 22 identificadores únicos por fotograma, movimiento para los 22 jugadores y participantes resaltados de ambos equipos. Las 344 pruebas del backend superaron la suite completa. El lint del frontend terminó sin errores nuevos y conservó tres advertencias anteriores; la compilación de producción terminó correctamente con Vite 8.3.3.

## **Actualización de transiciones y defensa activa del 24 de octubre de 2026**

Añadimos dos propuestas por equipo. Contraataque de campo completo comienza con una recuperación en campo propio y lleva la pelota hasta el área rival. Progresión vertical y pase al espacio distribuye apoyos en las tres zonas y avanza con pases sucesivos hacia adelante. El menú ahora contiene cinco opciones por equipo y diez simulaciones en total.

La defensa ya no se desplaza como una forma fija. En cada fotograma, el rival más cercano a la pelota sale a presionar. Los demás jugadores toman referencias por carril, mantienen la cobertura del arco y repliegan según los movimientos de los atacantes. Esta regla sigue el mismo criterio usado por el seguimiento sintético del partido en vivo.

La prueba enfocada comprueba las diez simulaciones, 22 jugadores por fotograma, movimiento de al menos nueve jugadores de cada equipo entre cada par de fotogramas, presión cercana, ocupación de zonas alejadas del campo y al menos diez avances de la pelota en las dos tácticas nuevas. La revisión visual en navegador de esta actualización sigue pendiente.

La comprobación del 24 de octubre de 2026 terminó con 39 pruebas enfocadas y 345 pruebas del backend aprobadas. El lint del frontend terminó sin errores y conservó tres advertencias anteriores. La compilación de producción transformó 56 módulos correctamente. La ruta `http://localhost:5173/api` devolvió las diez tácticas y las cuatro opciones nuevas para el partido próximo y el partido en vivo.

## **Actualización de remate lejano y tarjetas del 24 de octubre de 2026**

Reemplazamos Combinación por dentro por Remate desde fuera del área. La secuencia conserva doce contactos, libera espacio frente al área y asigna el último contacto a uno de los tres atacantes. El remate sale desde la coordenada 83 en el sentido del ataque y el fotograma siguiente lleva el balón hasta el arco sin poseedor.

Unificamos `MatchCard` para los estados En vivo, Próximo y Finalizado. Todas las tarjetas usan los colores de ambos equipos y el rayo oscuro central. El estado En vivo añade un icono de transmisión, una luz que recorre el fondo y un destello diagonal. Las animaciones se desactivan cuando el sistema solicita movimiento reducido.

La actualización se aplica tanto en Descubrir como en la pantalla de todos los partidos porque ambas usan el mismo componente. La revisión visual en Chrome a 1440 píxeles confirmó las tres tarjetas con colores, rayo, textos legibles y la tarjeta en vivo ocupando todo el ancho de su sección. La prueba enfocada terminó con 40 casos aprobados y la suite completa con 346. El lint no tuvo errores nuevos y la compilación de producción transformó 56 módulos. La revisión en un teléfono físico sigue pendiente.
