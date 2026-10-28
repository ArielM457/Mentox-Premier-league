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

El backend usa `SUPABASE_URL` y `SUPABASE_SECRET_KEY` para leer y escribir mediante la Data API. `SUPABASE_PUBLISHABLE_KEY` queda reservada para un cliente público con RLS y `SUPABASE_JWKS_URL` para validar sesiones cuando se integre Supabase Auth; actualmente la interfaz React se comunica con FastAPI y no necesita ninguna de las dos.

La clave secreta debe ser una clave nueva de tipo secret. No uses la clave pública en el backend ni copies la clave secreta al frontend. El `.env` está ignorado por Git.

Antes de activar la persistencia, comprueba la conexión sin mostrar las claves:

```powershell
.\scripts\test-supabase-connection.ps1
```

Cuando las siete tablas respondan con `[OK]`, cambia `SUPABASE_ENABLED=true` y reinicia el backend.

## **Enlace y migración**

Desde la raíz del repositorio:

```powershell
npx --yes supabase@latest login
# Añade temporalmente al archivo local apps/backend/.env:
# SUPABASE_DB_PASSWORD=<contraseña de la base>
.\scripts\setup-supabase.ps1
```

Las claves de la Data API no permiten modificar el esquema. Para aplicar migraciones también se necesita una sesión de Supabase CLI y `SUPABASE_DB_PASSWORD`. El script obtiene el project ref desde `SUPABASE_URL`; solo hace falta declarar `SUPABASE_PROJECT_REF` si la URL no tiene el formato habitual.

El script enlaza el proyecto y aplica las migraciones de `supabase/migrations`. No borra tablas ni reinicia la base. Después comprueba las siete tablas mediante la Data API.

Cuando termine correctamente, cambia esta variable:

```text
SUPABASE_ENABLED=true
```

Reinicia el backend. Los errores temporales de escritura se registran, pero no detienen el partido en vivo.

## **Tablas**

- `matches`: metadatos y duración del partido.
- `match_events`: eventos normalizados y su carga original.
- `moments`: explicaciones, prioridad y eventos de origen.
- `assistant_messages`: pregunta, respuesta y fuentes disponibles en ese tiempo.
- `match_summaries`: resumen final, estado editorial, responsable y nota de revisión.
- `community_votes`: un like o dislike por navegador y resumen.
- `community_messages`: sugerencias y comentarios de cada resumen.

Las siete tablas tienen RLS activo y no exponen políticas públicas. El backend accede con la clave secreta.
