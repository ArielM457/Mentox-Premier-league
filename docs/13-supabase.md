# **Persistencia en Supabase**

Supabase guarda los partidos sintéticos, sus eventos, los momentos narrativos y las conversaciones del asistente. La interfaz React no se conecta directamente y nunca recibe la clave secreta.

## **Variables locales**

Completa estas variables en `apps/backend/.env`:

```text
SUPABASE_ENABLED=false
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SECRET_KEY=<clave secreta del backend>
SUPABASE_PROJECT_REF=<project-ref>
SUPABASE_DB_PASSWORD=<contraseña de la base>
```

La clave secreta debe ser una clave nueva de tipo secret. No uses la clave pública ni copies la clave secreta al frontend. El `.env` está ignorado por Git.

## **Enlace y migración**

Desde la raíz del repositorio:

```powershell
npx --yes supabase@latest login
.\scripts\setup-supabase.ps1
```

El script enlaza el proyecto indicado en `SUPABASE_PROJECT_REF` y aplica las migraciones de `supabase/migrations`. No borra tablas ni reinicia la base.

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

Las cuatro tablas tienen RLS activo y no exponen políticas públicas. El backend accede con la clave secreta.
