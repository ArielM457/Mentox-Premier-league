# **Persistencia en Supabase**

Supabase guarda los partidos sintéticos, sus eventos, los momentos narrativos, los resúmenes, la participación de la comunidad y las conversaciones del asistente. La interfaz React no se conecta directamente y nunca recibe la clave secreta.

## **Variables locales**

Completa estas variables en `apps/backend/.env`:

```text
SUPABASE_ENABLED=false
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_PUBLISHABLE_KEY=<clave pública>
SUPABASE_SECRET_KEY=<clave secreta del backend>
SUPABASE_JWKS_URL=https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json
```

El backend usa `SUPABASE_URL` y `SUPABASE_SECRET_KEY` para leer y escribir mediante la Data API. También usa `SUPABASE_URL` y `SUPABASE_JWKS_URL` para validar las sesiones de los editores, como se explica más abajo. `SUPABASE_PUBLISHABLE_KEY` queda reservada para un cliente público con RLS; la interfaz React se comunica con FastAPI y no la necesita.

La migración `202610270001_summary_variants.sql` amplía `match_summaries` con el tipo de resumen y el jugador elegido. Debe aplicarse antes de habilitar los resúmenes corto y personalizado contra la base remota.

La clave secreta debe ser una clave nueva de tipo secret. No uses la clave pública en el backend ni copies la clave secreta al frontend. El `.env` está ignorado por Git.

Antes de activar la persistencia, comprueba la conexión sin mostrar las claves:

```powershell
.\scripts\test-supabase-connection.ps1
```

Cuando las ocho tablas respondan con `[OK]`, cambia `SUPABASE_ENABLED=true` y reinicia el backend.

## **Enlace y migración**

Desde la raíz del repositorio:

```powershell
npx --yes supabase@latest login
# Añade temporalmente al archivo local apps/backend/.env:
# SUPABASE_DB_PASSWORD=<contraseña de la base>
.\scripts\setup-supabase.ps1
```

Las claves de la Data API no permiten modificar el esquema. Para aplicar migraciones también se necesita una sesión de Supabase CLI y `SUPABASE_DB_PASSWORD`. El script obtiene el project ref desde `SUPABASE_URL`; solo hace falta declarar `SUPABASE_PROJECT_REF` si la URL no tiene el formato habitual.

El script enlaza el proyecto y aplica las migraciones de `supabase/migrations`. No borra tablas ni reinicia la base. Después comprueba las ocho tablas mediante la Data API.

Cuando termine correctamente, cambia esta variable:

```text
SUPABASE_ENABLED=true
```

Reinicia el backend. Los errores temporales de escritura se registran, pero no detienen el partido en vivo.

## **Editores de la revisión editorial**

Aprobar o rechazar un resumen (`POST …/editorial/{draft_id}/review`) y confirmar o rechazar un recorte (`POST …/highlights/{clip_id}/review`) exigen una sesión de Supabase Auth con el rol `editor`. El backend comprueba la firma del token con las claves públicas del proyecto, además de su emisor, su audiencia y su vencimiento. Las claves se leen de `SUPABASE_JWKS_URL` o, si no está, de `<SUPABASE_URL>/auth/v1/.well-known/jwks.json`.

Quien revisa queda registrado con el identificador de usuario del token. La petición ya no envía un nombre. Sin sesión, la API responde `401`; con una cuenta sin el rol, `403`; y sin `SUPABASE_URL`, `503`. En Azure, `infra/azure/deploy-analytics.ps1` pasa `SUPABASE_URL` a la API: la toma de `-SupabaseUrl`, de `$env:SUPABASE_URL` o de `apps/backend/.env`.

Para dar de alta a un editor:

1. En el panel de Supabase, abre **Authentication → Users** y crea el usuario con correo y contraseña.
2. En **SQL Editor**, asígnale el rol. El usuario no puede cambiar `app_metadata` por su cuenta; solo un administrador del proyecto puede hacerlo:

   ```sql
   update auth.users
   set raw_app_meta_data = raw_app_meta_data || '{"role": "editor"}'
   where email = 'editor@ejemplo.com';
   ```

3. El editor vuelve a iniciar sesión para que su token incluya el rol.

Para probar con Postman, obtén el `access_token` del editor y guárdalo en la variable `editorToken` de la colección. Vence en una hora con la configuración predeterminada de Supabase:

```powershell
$url = 'https://<project-ref>.supabase.co'
$body = @{ email = 'editor@ejemplo.com'; password = Read-Host 'Contraseña' } | ConvertTo-Json
$session = Invoke-RestMethod -Method Post -Uri "$url/auth/v1/token?grant_type=password" `
  -Headers @{ apikey = '<SUPABASE_PUBLISHABLE_KEY>' } -ContentType 'application/json' -Body $body
$session.access_token | Set-Clipboard
```

## **Tablas**

- `matches`: metadatos y duración del partido.
- `match_events`: eventos normalizados y su carga original.
- `moments`: explicaciones, prioridad y eventos de origen.
- `assistant_messages`: pregunta, respuesta y fuentes disponibles en ese tiempo.
- `match_summaries`: resumen final, estado editorial, identificador del editor y nota de revisión. Solo se guarda cuando un editor decide o una verificación lo retira; pedir un resumen no lo guarda.
- `action_callouts`: frases breves por tipo de jugada para invitar a abrir su análisis.
- `community_votes`: un like o dislike por navegador y resumen.
- `community_messages`: sugerencias y comentarios de cada resumen.

Las ocho tablas tienen RLS activo y no exponen políticas públicas. El backend accede con la clave secreta.
