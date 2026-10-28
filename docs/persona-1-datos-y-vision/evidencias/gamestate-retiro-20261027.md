# Retiro de GameState de la demo de The Prime Moment

Fecha local: 27 de octubre de 2026, America/La_Paz.
Comprobación final: 28 de octubre de 2026, 00:23:56 UTC.

## Decisión del usuario

Eliminar el contenedor GameState y continuar con Roboflow Suite, SoccerNet
TeamSpotting y datos del partido MESSI. No es un requisito nuevo del reto,
sino una decisión de alcance de la demo tras una evaluación real.

La prueba GPU del vídeo de 180 segundos tardó 1613,559 segundos de pipeline
y produjo 4 detecciones, ninguna posición calibrada y ninguna métrica
disponible. El resultado técnico no justifica depender de GameState para
estos renders. La evidencia original se conserva en
[la validación completa](gamestate-parche-validacion-20261027-7uTJjl/README.md).

## Recurso exacto y comprobación previa

- Suscripción: `7d45d958-156a-4278-9935-755ba5a395ca`.
- Grupo: `rg-prime-moment-dev`.
- Container App: `ca-mentox-gamestate-dev`.
- Imagen antes del retiro: `mentox138f2e77.azurecr.io/mentox/soccernet-gamestate:60da675eaafb`.
- Escala antes del retiro: mínimo 0, máximo 1.

El recurso se consultó por nombre, grupo y suscripción antes de eliminarlo.
No se cambió la suscripción global de Azure CLI. Se consultaron Azure MCP
y la documentación oficial de Azure CLI antes de operar. Versión de Azure CLI:
`2.88.0`.

## Operación realizada

El siguiente comando es el registro de una operación destructiva ya realizada,
no un paso necesario para ejecutar la demo:

```bash
az containerapp delete \
  --subscription 7d45d958-156a-4278-9935-755ba5a395ca \
  --resource-group rg-prime-moment-dev \
  --name ca-mentox-gamestate-dev \
  --yes --no-wait --only-show-errors
```

Resultado: código de salida 0. Después se consultó el estado por el plano
de administración, sin llamar al endpoint del modelo:

```bash
az containerapp list \
  --subscription 7d45d958-156a-4278-9935-755ba5a395ca \
  --resource-group rg-prime-moment-dev \
  --query "[?name=='ca-mentox-gamestate-dev'].{name:name,state:properties.provisioningState}" \
  --output json
```

Resultado: `[]`, código de salida 0. La aplicación ya no existe.

## Recursos preservados y recuperación

No se eliminaron el grupo de recursos, el entorno de Container Apps, ACR,
imágenes, identidades, Blob Storage, vídeos, colas ni el worker. Roboflow y
TeamSpotting no se encendieron, apagaron ni modificaron. Los artefactos de
investigación descargados y el código permanecen en el repositorio.

La aplicación se puede volver a desplegar con la imagen y los scripts
conservados, pero requerirá nueva autorización y configuración de secretos;
no hay una acción de deshacer para recuperar el estado efímero de la réplica.
La eliminación no implica costo cero del registro o de los demás recursos
que se conservaron.

## Configuración del backend

GameState es opcional cuando no tiene endpoint configurado. El cliente y
el coordinador actuales se revisaron para comprobar esta condición. No se
modificó el código de inferencia ni se afirma una nueva prueba de integración.
Para evitar solicitudes al servicio eliminado, antes de arrancar el backend:

```bash
unset SOCCERNET_GAMESTATE_ENDPOINT SOCCERNET_GAMESTATE_API_KEY
```

Eliminar las mismas variables de configuraciones locales que las vuelvan
a inyectar y reiniciar el backend existente. Este proceso no puede quitar
exports de otras terminales ni cambiar el entorno de procesos ya iniciados.

## Siguiente integración acordada, no verificada todavía

- Roboflow: observaciones espaciales con cajas y confianza del detector.
- TeamSpotting: candidatos temporales con clase y confianza, no hechos
  confirmados ni identificación nominal por sí solos.
- MESSI: eventos, identidades y posiciones del mismo partido, marcados como
  datos del simulador, nunca como predicciones de los modelos.
- Asociar las fuentes solo cuando coincidan partido, archivo y reloj de vídeo;
  conservar referencias y evitar duplicar acciones y estadísticas.
- La UI debe permitir distinguir «detectado por IA» de «dato del simulador».

La calidad de Roboflow y TeamSpotting aún necesita contraste con la referencia
del simulador. Un resultado que falte o contradiga esa referencia debe quedar
visible; completar los campos con MESSI no demuestra que el modelo los detectó.

## Archivos actualizados

`docs/07-decisiones-tomadas.md`, `apps/backend/.env.example`,
`deploy/azure-soccernet-gamestate/README.md`,
`docs/persona-1-datos-y-vision/despliegue-modelos-azure-equipo.md`,
`docs/persona-1-datos-y-vision/evidencias/DV-US-36.md` y su índice.

Se verificó localmente que GameState desconfigurado no necesita servicio remoto:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 --offline \
  pytest -q apps/backend/tests/test_gamestate_analysis.py::test_disabled_gamestate_does_not_require_remote_service
```

Resultado: **1 prueba aprobada**, 0,29 segundos. `git diff --check` sin errores.
No se ejecutaron nuevas inferencias, builds ni pruebas GPU para este retiro.
Referencia operativa: [Azure CLI: eliminar una Container App](https://learn.microsoft.com/en-us/cli/azure/containerapp#az-containerapp-delete).
