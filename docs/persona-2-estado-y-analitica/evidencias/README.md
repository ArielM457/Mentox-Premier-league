# Evidencias técnicas de Persona 2

Cada historia se da por verificada solo si sus criterios pasan con una prueba o una comprobación reproducible. Se separa siempre lo verificado en local de lo que necesita Azure, vídeo o modelos externos. El formato sigue la [plantilla de Persona 1](../../persona-1-datos-y-vision/evidencias/PLANTILLA.md).

## Estado

| Historia | Estado | Evidencia |
|---|---|---|
| EA-US-01 · Consultar el estado del partido | Verificada localmente | [EA-US-01](EA-US-01.md) |
| EA-US-02 · Reconstruir el estado ante tardíos y correcciones | Verificada localmente | [EA-US-02](EA-US-02.md) |
| EA-US-03 · Calcular estadísticas recalculables | Verificada localmente | [EA-US-03](EA-US-03.md) |
| EA-US-04 · Agrupar jugadas y detectar patrones | Verificada localmente | [EA-US-04](EA-US-04.md) |
| EA-US-05 · Comparar tramos, hitos e indicadores propios | Verificada localmente | [EA-US-05](EA-US-05.md) |
| EA-US-06 · Seleccionar momentos con motivos visibles | Verificada localmente | [EA-US-06](EA-US-06.md) |
| EA-US-07 · Evaluar xT, VAEP y xG | Adaptadores verificados; modelos desactivados | [EA-US-07](EA-US-07.md) |
| EA-US-08 · Procesar el flujo en Azure | Verificada con dobles de Azure; despliegue pendiente | [EA-US-08](EA-US-08.md) |
| EA-US-09 · Entregar ejemplos e integrar con Persona 3 y 4 | Verificada localmente; integración probada en copia de la rama de Persona 4 | [EA-US-09](EA-US-09.md) |
| EA-US-10 · Medir velocidad y distancia desde posiciones | Verificada con observaciones simuladas en el formato de Persona 1; vídeo real pendiente | [EA-US-10](EA-US-10.md) |
| EA-US-11 · Presentar la analítica en un tablero | Verificada localmente | [EA-US-11](EA-US-11.md) |
| EA-US-12 · Desplegar la analítica en Azure con datos ficticios en Supabase | Verificada en local y en Azure, con el flujo continuo | [EA-US-12](EA-US-12.md) |
| EA-US-13 · Explicar un momento con datos en el resumen | Verificada en local y en Azure | [EA-US-13](EA-US-13.md) |

## Entorno común de verificación

| Componente | Versión |
|---|---|
| Sistema | Windows 11 Pro 10.0.26200 |
| Python | 3.13.9 (el proyecto admite `>=3.12,<3.14`) |
| pydantic | 2.14.0 |
| pytest | 9.1.1 |
| azure-eventhub | 5.15.1 |
| azure-storage-blob | 12.31.0 |
| azure-identity | 1.26.0 |
| fastapi | 0.143.0 |
| Contrato de entrada | `MatchEvent 1.0` |
| Base | `main` en `3ce1a86` |

`uv` no estaba instalado en el equipo, así que se usó un entorno virtual con `pip install -e "apps/backend[dev]"`, que resuelve las mismas dependencias declaradas en `pyproject.toml`. Context7 no estaba disponible en esta sesión. Los adaptadores de Azure siguen las mismas llamadas del SDK que Persona 1 ya usa en `azure_event_hubs.py` y `azure_blob.py`; las llamadas nuevas (`list_blobs`, `get_container_client` y `EventData.properties`) están cubiertas solo con dobles y deben confirmarse en la prueba de humo.

## Reproducción general

Desde la raíz del repositorio:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e "apps/backend[dev]"
.venv/Scripts/python -m pytest apps/backend/tests -q
```

Resultado del 13 de octubre de 2026:

```text
225 passed in 7.51s
```

Son 134 pruebas previas y 91 de Persona 2. El 13 de octubre la analítica de seguimiento pasó a consumir las observaciones de visión de Persona 1.
