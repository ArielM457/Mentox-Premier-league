# **Despliegue en Azure paso a paso**

Esta guía permite que cualquier integrante del equipo cree todo el entorno de la demo:

- **En Azure:** Event Hubs, Storage, registro de imágenes y Container Apps con la API, la interfaz, el procesador continuo y la repetición de partidos.
- **En Supabase:** la base de datos con partidos ficticios.

Todo lo hace un solo script. El detalle técnico de cada recurso está en [despliegue en Azure y Supabase](persona-2-estado-y-analitica/despliegue-azure-supabase.md).

- **Estado:** desplegado y verificado el 25 de octubre de 2026, en Azure for Students (`eastus2`), el entorno `cae-mentoxp2-demo-wp` sigue activo, la API lee los 3 partidos y su seguimiento desde Supabase, y la interfaz, el análisis de momentos y la previa responden. Antes se resolvieron los problemas de la sección 8 (entorno Express, suspensión y cadena solo IPv6).
- **Responsable:** Persona 2 (estado y analítica).

## **Antes de empezar: ¿un despliegue para todos o uno por persona?**

Cada cuenta de Azure for Students trae 100 USD de crédito y permite un solo entorno de Container Apps por región. El costo principal es Event Hubs Standard, alrededor de 1 USD al día aunque nadie lo use.

| Opción | Cuándo usarla | Costo |
|---|---|---|
| **Un despliegue compartido** (recomendado) | La demo y las pruebas del equipo. Una persona despliega y comparte las URL. | Unos 30 USD al mes de una sola cuenta |
| **Uno por persona** | Alguien necesita probar cambios de infraestructura sin afectar la demo. | Lo mismo en cada cuenta; bórrelo al terminar |

La base de Supabase es una sola para todo el equipo. Quien la creó comparte la cadena de conexión por un canal privado, nunca por el chat del proyecto ni en Git.

## **1. Preparar el equipo**

| Herramienta | Para qué | Cómo instalarla en Windows |
|---|---|---|
| Cuenta Azure for Students | Créditos y suscripción | [azure.microsoft.com/free/students](https://azure.microsoft.com/free/students) con el correo de la universidad |
| Azure CLI | Crear los recursos | `winget install -e --id Microsoft.AzureCLI`; después abra otra terminal |
| Docker Desktop | Construir las imágenes | [docker.com](https://www.docker.com/products/docker-desktop/); debe estar abierto al desplegar |
| Python 3.12 o 3.13 | Cargar datos en Supabase | `winget install -e --id Python.Python.3.13` |
| Node.js 22 o superior | Ejecutar la interfaz en local | `winget install -e --id OpenJS.NodeJS.LTS` |
| Git | Obtener el código | `winget install -e --id Git.Git` |

Desde la raíz del repositorio, prepare el entorno de Python y la interfaz una sola vez:

```powershell
python -m venv .venv
```

```powershell
.\.venv\Scripts\python.exe -m pip install -e "apps/backend[dev,db]"
```

```powershell
npm install
```

En cada terminal nueva de PowerShell, permita los scripts del proyecto solo para esa ventana:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

## **2. Base de datos en Supabase**

Hágalo una sola vez para todo el equipo.

1. Cree un proyecto gratuito en [supabase.com](https://supabase.com), en la región **East US (North Virginia)**. Genere la contraseña con el botón y guárdela en un gestor de contraseñas.
2. En **Connect → Direct → Session pooler**, copie la URI y cambie `[YOUR-PASSWORD]` por la contraseña. No use la conexión directa: solo funciona por IPv6 y Azure no la alcanza.
3. Guarde la cadena en la terminal. El comando muestra `Pega la cadena:` y espera: pegue ahí y pulse Enter.

   ```powershell
   $env:SUPABASE_DB_URL = Read-Host 'Pega la cadena'
   ```

4. Cree las tablas y cargue los datos ficticios:

   ```powershell
   .\.venv\Scripts\python.exe apps/backend/scripts/supabase_seed.py --schema
   ```

Debe terminar con tres líneas `in_database`: el partido de aceptación, el de analítica y el partido en vivo. Para verlos en Supabase, abra **Table Editor** y elija el esquema `match_analytics` en el selector de esquemas.

Volver a ejecutar la carga reemplaza esos partidos. Hágalo cada vez que cambien los escenarios o las migraciones.

## **3. Desplegar en Azure**

1. Inicie sesión y elija la suscripción **Azure for Students**:

   ```powershell
   az login
   ```

2. Revise qué se va a crear. No cuesta nada: solo registra los proveedores y crea un grupo vacío.

   ```powershell
   ./infra/azure/deploy-analytics.ps1 -ResourceGroup rg-mentox-analytics -Location eastus2 -WhatIf
   ```

3. Con Docker Desktop abierto, despliegue:

   ```powershell
   ./infra/azure/deploy-analytics.ps1 -ResourceGroup rg-mentox-analytics -Location eastus2
   ```

   - Responda `s` a las confirmaciones.
   - Pegue la cadena de Supabase cuando la pida; no se ve mientras se escribe.
   - Tarda entre 15 y 25 minutos.

4. Al final aparecen la URL de la interfaz y la de la API (con `/docs`). El script espera 90 s y comprueba que el entorno siga activo.

| Opción del script | Para qué |
|---|---|
| `-Prefix otro` | Usar otros nombres; obligatorio si dos personas despliegan en la misma suscripción |
| `-ApiAlwaysOn` | Dejar la API encendida el día de la demo, sin arranque en frío |
| `-WorkerOn` | Dejar encendido el procesador continuo |
| `-SeedDatabase` | Cargar Supabase dentro del mismo despliegue |
| `-RecreateEnvironment` | Volver a crear el entorno de Container Apps si Azure lo suspendió |
| `-SkipWeb` | Desplegar solo la API |

## **4. Mostrar el flujo en directo**

Los nombres usan el prefijo `mentoxp2`. Si desplegó con otro, el script muestra los nombres correctos al terminar.

1. Encienda el procesador continuo:

   ```powershell
   az containerapp update -n ca-mentoxp2-worker -g rg-mentox-analytics --min-replicas 1 --max-replicas 1
   ```

2. Repita un partido de Supabase en Event Hubs:

   ```powershell
   az containerapp job start -n caj-mentoxp2-replay -g rg-mentox-analytics
   ```

3. Siga lo que procesa:

   ```powershell
   az containerapp logs show -n ca-mentoxp2-worker -g rg-mentox-analytics --follow
   ```

4. Treinta segundos después del último evento, el análisis aparece en Supabase. Consúltelo en el editor SQL:

   ```sql
   select run_id, match_id, event_count, candidate_count
   from match_analytics.analytics_runs where produced_by = 'stream-worker'
   order by created_at desc;
   ```

5. Apague el procesador al terminar:

   ```powershell
   az containerapp update -n ca-mentoxp2-worker -g rg-mentox-analytics --min-replicas 0 --max-replicas 1
   ```

## **5. Cuidar los créditos**

| Recurso | Costo aproximado |
|---|---|
| Event Hubs Standard | 0,03 USD por hora, unos 22 USD al mes. Corre siempre |
| Container Registry Basic | Unos 5 USD al mes |
| Container Apps | Gratis mientras se apaga sin tráfico; el procesador encendido cuesta de 4 a 14 USD al mes |
| Log Analytics y Storage | Céntimos, con tope de 0,1 GB de registros al día |
| Supabase (plan gratuito) | 0 USD. Se pausa tras una semana sin uso |

El saldo restante está en el portal de Azure, en la suscripción **Azure for Students**. Al terminar la demo, borre todo:

```powershell
./infra/azure/remove-analytics.ps1 -ResourceGroup rg-mentox-analytics
```

Pide escribir el nombre del grupo y no se puede deshacer. `-StopOnly` solo apaga las aplicaciones; Event Hubs y el registro siguen cobrando.

## **6. Ejecutar todo en local**

Con la cadena de Supabase en la terminal, la API usa la analítica real y los partidos de la base:

```powershell
$env:ANALYTICS_ENGINE = 'persona2'; $env:MATCH_SOURCE = 'supabase'
```

```powershell
.\.venv\Scripts\python.exe -m uvicorn match_intelligence.main:app --port 8000
```

En otra terminal, inicie la interfaz:

```powershell
npm run dev --workspace frontend
```

La interfaz queda en `http://localhost:5173` y reenvía `/api` a la API. Sin `MATCH_SOURCE`, la API usa los partidos sintéticos en memoria y no necesita Supabase.

## **7. Secretos**

- La cadena de Supabase, las claves `sb_secret_…` y las contraseñas viven solo en variables de la terminal o en `apps/backend/.env`, que Git ignora.
- Nunca las pegue en el chat, en issues ni en commits. Si ocurre, cámbielas de inmediato: en Supabase, **Project Settings → Database → Reset database password** y **API Keys**.
- La clave publicable y las variables `NEXT_PUBLIC_*` no hacen falta: la interfaz nunca se conecta a Supabase directamente.

## **8. Problemas conocidos y solución**

| Mensaje | Causa | Solución |
|---|---|---|
| `deploy-analytics.ps1 no se reconoce` | La terminal no está en la raíz del repositorio | `cd` a la carpeta del repositorio |
| `la ejecución de scripts está deshabilitada` | Política de PowerShell | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` |
| `No module named 'match_intelligence'` | Se usó el Python del sistema | Use `.\.venv\Scripts\python.exe` |
| `falta la variable SUPABASE_DB_URL` | Terminal nueva o se pegó la cadena como texto de la pregunta | Repita el `Read-Host` y pegue cuando aparezca `Pega la cadena:` |
| La región no está permitida | Azure for Students limita las regiones (`eastus2`, `eastus`, `canadacentral`, `brazilsouth`, `chilecentral` en nuestras cuentas) | Use una de las que lista el script |
| `ExpressEnvironmentResourceNotSupported` | Azure creó el entorno en modo Express | Ya resuelto: la plantilla pide `WorkloadProfiles`. Vuelva a ejecutar el script |
| `GatewayTimeout` al borrar | Azure tardó en responder | El script espera y comprueba; vuelva a ejecutarlo si se detuvo |
| `ManagedClusterSuspended` | Azure suspendió el cómputo del entorno (nos ocurrió con un entorno recién recreado con el mismo nombre) | Ejecute con `-RecreateEnvironment`. Si se repite, deje la API y la interfaz en un entorno Express y corra el procesador desde un equipo |
| La API no responde y sus registros dicen `connection is bad: connection to server at "2600:…" … Cannot assign requested address` | Se usó la conexión directa de Supabase (`db.<ref>.supabase.co`), que solo tiene IPv6; Container Apps sale por IPv4 | Use la del **Session pooler** (`…pooler.supabase.com`, usuario `postgres.<ref>`) y vuelva a desplegar. El script ahora la rechaza antes de desplegar, y la API arranca con los partidos sintéticos si no alcanza la base |
| `MaxNumberOfRegionalEnvironmentsInSubExceeded` | Solo se permite un entorno por región | Borre el anterior (el script lo ofrece) o use otra región |
| `503` en `/api/v1/integration/*` | Faltan archivos de experimentos de visión de Persona 1 (`experiments/…/output`) | Es esperado hasta que Persona 1 los publique; el resto de la API funciona |
| Docker no responde | Docker Desktop cerrado | Ábralo y espere a que diga que está en marcha |
| ACR Tasks no permitido | Algunas suscripciones de estudiante lo bloquean | Use Docker local (es lo predeterminado); no use `-UseAcrBuild` |
