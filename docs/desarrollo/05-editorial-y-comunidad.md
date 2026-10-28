# SDD-05 · Revisión editorial y comunidad

## Especificación

**Objetivo:** permitir revisar el contenido antes de publicarlo y recibir opinión comunitaria con moderación y trazabilidad.

**Entradas:** borradores de resumen/mensajes, decisiones editoriales, reportes, votos, sugerencias y mensajes. **Salidas:** estados de revisión, contenido aprobado o rechazado, conteos y conversación actualizados.

Requisitos relacionados: RF-38, RF-39, RF-53 y los requisitos de revisión/comunidad del [catálogo](requisitos.md). La comunidad amplía la experiencia; su voto no autoriza automáticamente la publicación editorial.

### Criterios de aceptación

1. Consultar como publicado un borrador sin aprobación devuelve un rechazo de estado, no una publicación implícita.
2. Aprobar o rechazar conserva la decisión asociada al borrador.
3. Un reporte permite contrastar contenido con sus eventos y registrar la resolución.
4. Los mensajes comunitarios se moderan y las acciones tienen límites de frecuencia.
5. El estado puede recuperarse con persistencia configurada; un fallo secundario no debe corromper la sesión.
6. Una propuesta de recorte conserva intervalo y fuentes; no se afirma que exista un archivo recortado si solo se han calculado límites.

## Diseño implementado

La sesión de partido gestiona borradores, revisión, reportes y propuestas de highlights. `adapters/http/community_router.py` separa las operaciones comunitarias; `application/community.py` define salas, votos, mensajes, persistencia y bus.

`application/moderation.py` normaliza texto y aplica reglas locales. `adapters/storage/supabase_community.py` permite guardar información cuando está configurado. Las migraciones están en `supabase/migrations/`, junto al esquema de experiencia, variantes de resumen y callouts.

El frontend integra revisión y comunidad en `src/screens/Editorial.jsx`. La interfaz consulta y escucha cambios; el bus en memoria es propio del proceso. Tener un adaptador de base de datos no implica que se haya verificado difusión entre varias réplicas.

## Tareas y estado

- [x] Implementar retención editorial, aprobación/rechazo y consulta de publicación.
- [x] Ofrecer reportes, resolución y fuentes del contenido.
- [x] Incorporar propuestas de recorte con revisión humana.
- [x] Agregar votos, mensajes, sugerencias y moderación local.
- [x] Integrar la vista editorial y el adaptador opcional de Supabase.
- [ ] Verificar autenticación y autorización adecuadas para un entorno público con usuarios reales.
- [ ] Validar sincronización comunitaria y límites de frecuencia con múltiples réplicas.
- [ ] Implementar y verificar el corte/carga física de highlights si se requiere publicar vídeo.
- [ ] Completar pruebas operativas de persistencia y restauración en una base real.

## Validación

Pruebas: `test_community.py`, `test_moderation.py`, `test_supabase_community_repository.py`, `test_supabase_match_repository.py` y los casos editoriales de `test_match_experience_api.py`.

Los dobles de persistencia verifican contratos locales; no prueban RLS, permisos, redes ni políticas de una instancia real de Supabase. El estado observado se recoge en [validación](validacion.md).
