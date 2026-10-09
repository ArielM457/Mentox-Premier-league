# Evidencia técnica de DV-US-09

## Identificación

- **Historia:** DV-US-09 · Conservar artefactos autorizados.
- **Estado:** contrato y adaptador verificados localmente; Azure real pendiente.
- **Prioridad:** P1.
- **Última verificación:** 9 de octubre de 2026.
- **Responsable:** Persona 1 · Datos y visión.
- **Requisitos relacionados:** DV-RF-14 y DV-RNF-03.

## Objetivo comprobado

El backend clasifica partidos sintéticos, vídeos declarados como autorizados y observaciones experimentales, los dirige a contenedores privados distintos y conserva en el nombre y los metadatos la relación con el partido y el origen. La recuperación comprueba metadatos, tipo de contenido y hash SHA-256 antes de entregar los mismos bytes.

La integración local usa dobles del servicio, pero ejecuta las clases reales de dominio y el adaptador real del SDK. La prueba contra una cuenta Azure queda documentada y pendiente.

## Alcance implementado

- Tipos `synthetic_match`, `authorized_video` y `observation`.
- Procedencias obligatorias `synthetic`, `authorized` y `experimental` según el tipo.
- Contenedores `matches`, `authorized-videos` y `observations`.
- Nombre determinista `<match_id>/<artifact_id>`.
- Metadatos `artifact_id`, `match_id`, `kind`, `provenance`, `origin` y `content_sha256`.
- Conservación del tipo MIME mediante `ContentSettings`.
- Escritura sin sobrescritura para no reemplazar evidencia por accidente.
- Recuperación exacta y comprobación de integridad SHA-256.
- Autenticación sin secretos mediante `DefaultAzureCredential`.
- Cierre del cliente asíncrono y de la credencial.
- Prueba manual con un partido generado localmente y explícitamente sintético.

## Fuera del alcance

- No se subió ningún vídeo ni dato real de la Premier League.
- No se verificó una cuenta Azure real en esta ejecución.
- No se crean contenedores desde la aplicación; DV-US-06 los declara en Bicep.
- No se asignan roles RBAC automáticamente.
- La declaración `authorized` no reemplaza una revisión humana de licencia o permiso.
- No se implementó catálogo, retención, borrado, versionado ni interfaz HTTP.

## Entradas y resultados

| Entrada | Regla | Resultado |
|---|---|---|
| Partido sintético | Procedencia `synthetic` | Contenedor `matches` |
| Vídeo con permiso documentado | Procedencia `authorized` | Contenedor `authorized-videos` |
| Observación experimental | Procedencia `experimental` | Contenedor `observations` |
| `match_id` y `artifact_id` | Identificadores seguros, sin `/` ni rutas relativas | Nombre `<match_id>/<artifact_id>` |
| Contenido y tipo MIME | Bytes no vacíos y `content_type` obligatorio | Blob con metadatos y SHA-256 |

La prueba manual requiere solo `AZURE_BLOB_SERVICE_ENDPOINT`. No admite ni documenta claves o cadenas de conexión.

## Cambios técnicos

| Archivo | Cambio | Motivo |
|---|---|---|
| `apps/backend/src/match_intelligence/application/artifacts.py` | Contratos, reglas de procedencia, contenedores e integridad | Mantener la política independiente de Azure |
| `apps/backend/src/match_intelligence/adapters/storage/azure_blob.py` | Adaptador asíncrono de Blob Storage | Cargar y recuperar con identidad Azure |
| `apps/backend/src/match_intelligence/adapters/storage/__init__.py` | Paquete de almacenamiento | Separar el borde de infraestructura |
| `apps/backend/scripts/blob_storage_smoke.py` | Prueba manual con datos sintéticos | Verificar el servicio desplegado sin secretos |
| `apps/backend/tests/test_azure_blob_storage.py` | Trece pruebas automatizadas | Cubrir criterios y fallos de integridad |
| `apps/backend/pyproject.toml` y `apps/backend/uv.lock` | Dependencia `azure-storage-blob` | Usar el SDK oficial y fijar versiones |
| `apps/backend/.env.example` | Endpoint Blob comentado | Mostrar configuración sin credenciales |
| `infra/azure/README.md` | Pasos de RBAC y prueba | Hacer reproducible la integración real |
| Documentos de Persona 1 | Estado y vínculo de evidencia | Mantener trazabilidad del backlog |

## Diseño

```text
Artifact
  │ valida tipo, procedencia, origen e identificadores
  ▼
AzureBlobArtifactStore
  ├─ synthetic_match ──► matches/<match_id>/<artifact_id>
  ├─ authorized_video ─► authorized-videos/<match_id>/<artifact_id>
  └─ observation ──────► observations/<match_id>/<artifact_id>
                              │
                              ▼
                    metadatos + content_type + SHA-256
```

El contrato de aplicación no importa Azure. El adaptador traduce el contrato a `BlobServiceClient` y puede recibir un cliente inyectado para pruebas.

## Decisiones técnicas

### Procedencia obligatoria por tipo

Un vídeo solo puede construirse con procedencia `authorized`. Esta regla evita mezclar una carga sin clasificar con los artefactos autorizados. No demuestra legalmente el permiso: quien carga el archivo debe conservar esa documentación fuera del blob si contiene información sensible.

### Nombre seguro y trazable

`match_id`, `artifact_id` y `origin` aceptan letras ASCII, números, punto, guion y guion bajo. Se excluyen `/`, espacios iniciales y rutas relativas. El nombre incluye el partido y el identificador; los metadatos repiten ambos valores y añaden el origen.

### Escritura inmutable

`overwrite=False` hace visible una colisión en vez de reemplazar silenciosamente un artefacto. La política de versionado o reemplazo debe definirse antes de habilitar modificaciones.

### Integridad de recuperación

El hash SHA-256 se calcula antes de cargar y se guarda como metadato. Al recuperar se comparan los metadatos esperados, el tipo MIME y el hash de los bytes. Una diferencia produce `ArtifactIntegrityError`.

### Identidad de Azure

La fábrica usa el endpoint de la cuenta y `DefaultAzureCredential`. La infraestructura deshabilita claves compartidas; la identidad necesita `Storage Blob Data Contributor`.

## Context7

Se consultó el 9 de octubre de 2026 la documentación vigente del repositorio oficial `/azure/azure-sdk-for-python`. Context7 confirmó:

- `BlobServiceClient` con URL OAuth y credencial Azure;
- clientes asíncronos en `azure.storage.blob.aio`;
- `upload_blob` para cargar bytes;
- `download_blob` seguido de `readall()` para recuperar los bytes;
- cierre asíncrono tanto del cliente como de `DefaultAzureCredential`.

La implementación añade `metadata` y `ContentSettings(content_type=...)` sobre esas firmas del SDK.

## Cobertura de criterios de aceptación

| Criterio | Implementación | Evidencia | Estado |
|---|---|---|---|
| Cada tipo usa el contenedor definido | `CONTAINER_BY_KIND` | `test_each_artifact_kind_uses_its_defined_container` para los tres tipos | Cumplido localmente |
| Nombre o metadato relaciona partido y origen | Nombre jerárquico y seis metadatos | `test_blob_name_and_metadata_preserve_match_and_origin` | Cumplido localmente |
| Recuperar el mismo contenido | `download_blob`, `readall` y SHA-256 | `test_retrieve_returns_the_exact_same_content` y prueba de alteración | Cumplido localmente |
| No entregar datos reales de Premier League | Fixtures y prueba manual exclusivamente sintéticas; no se confirma ningún medio | `test_delivered_fixtures_are_explicitly_synthetic` y revisión de artefactos versionados | Cumplido para lo entregado |

## Pruebas automatizadas

| Grupo | Comportamiento comprobado |
|---|---|
| Tres casos parametrizados de contenedor | Enrutamiento de partido, vídeo y observación |
| Trazabilidad | Nombre, partido, origen, procedencia y hash |
| Ida y vuelta | Igualdad exacta de bytes y referencia |
| Alteración | Rechazo cuando cambia el contenido |
| Autorización declarada | Rechazo de vídeo con procedencia distinta de `authorized` |
| Cuatro identificadores inseguros | Bloqueo de rutas, vacío y espacio inicial |
| Recursos | Cierre de cliente y credencial |
| Datos entregados | Fixture sintético explícito y sin referencias a Premier League |

## Reproducción

Pruebas específicas:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  pytest apps/backend/tests/test_azure_blob_storage.py -q
```

Suite completa:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 pytest -q
```

Prueba manual después del despliegue y RBAC:

```bash
export AZURE_BLOB_SERVICE_ENDPOINT="https://<storage-account>.blob.core.windows.net"
uv run --project apps/backend --python 3.12 \
  python apps/backend/scripts/blob_storage_smoke.py
```

Comprobaciones adicionales:

```bash
UV_CACHE_DIR=/tmp/mentox-uv-cache \
uv run --project apps/backend --python 3.12 \
  python -m compileall -q apps/backend/src apps/backend/scripts
az bicep build --file infra/azure/main.bicep --stdout >/dev/null
git diff --check
```

## Entorno verificado

| Componente | Versión |
|---|---|
| Python | 3.12.13 |
| uv | 0.11.32 |
| pytest | 9.1.1 |
| azure-storage-blob | 12.31.0 |
| azure-identity | 1.26.0 |
| Azure CLI Bicep | 0.48.1 |
| Azure real | No utilizado |

## Resultado

Pruebas específicas:

```text
.............                                                            [100%]
13 passed in 0.51s
```

Suite completa:

```text
........................................................................ [ 88%]
.........                                                                [100%]
81 passed in 0.60s
```

`compileall`, la compilación de `infra/azure/main.bicep` y `git diff --check` terminaron correctamente y sin salida de error. Bicep emitió una plantilla ARM que conserva los tres contenedores privados y `blobServiceEndpoint`.

## Limitaciones y riesgos

- Los dobles verifican el uso del SDK, pero no prueban red, permisos, límites ni respuestas reales de Azure.
- La aplicación exige procedencia explícita, pero no puede validar por sí sola derechos de uso de un vídeo.
- El hash detecta cambios respecto a la referencia en memoria; una política de auditoría externa requeriría un catálogo inmutable o firma.
- Los contenedores deben existir antes de ejecutar el adaptador.
- `overwrite=False` requiere un `artifact_id` nuevo para una nueva versión.
- La prueba manual conserva el blob para revisión y puede generar costo mínimo de almacenamiento.

## Dependencias y siguientes pasos

- Desplegar DV-US-06 y asignar `Storage Blob Data Contributor` a la identidad usada.
- Ejecutar `blob_storage_smoke.py` y conservar la salida sin tokens para elevar el estado a verificada en integración.
- Definir con el equipo la política de retención, versiones y borrado.
- Conservar fuera del repositorio la prueba documental de autorización de cualquier vídeo.
- DV-US-10 puede referenciar un vídeo autorizado mediante `ArtifactLocation` sin mezclarlo con datos sintéticos.
