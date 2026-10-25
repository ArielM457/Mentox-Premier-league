# **Documento local de la previa**

La primera versión de la información previa al partido se guarda en `apps/backend/data/prematch/synthetic-analytics-001.json`.

El archivo contiene únicamente datos sintéticos y aprobados para la demostración. La nota periodística compartida se usó para identificar secciones útiles, no como una fuente de nombres, resultados, lesiones o sanciones reales.

## **Contenido**

- Procedencia, fecha de actualización y estado de aprobación.
- Presentación general y datos destacados del partido.
- Cinco resultados recientes por equipo.
- Lesiones, sanciones y disponibilidad.
- Jugadores clave.
- Claves tácticas.
- Alineación probable.

## **Consumo**

El agente de previa lee el documento y lo incluye en la respuesta de `GET /api/v1/matches/{match_id}/preview`. React recibe el contrato y permite abrir el informe de cada equipo y buscar dentro de sus secciones.

Si no existe un documento para un partido, el backend entrega una estructura sintética mínima identificada como `local_generated`. No consulta datos reales ni inventa bajas durante la solicitud.

## **Migración pendiente**

Cuando Blob Storage esté disponible, se reemplazará el lector del archivo por un adaptador de almacenamiento. El documento mantendrá el mismo contrato para evitar cambios en la interfaz.
