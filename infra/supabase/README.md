# Base de datos en Supabase

`migrations/` define el esquema `match_analytics` para los partidos ficticios, el seguimiento simulado y los resultados de la analítica (Persona 2). Es PostgreSQL estándar y se puede ejecutar varias veces.

Se aplica de tres formas:

- **Script del proyecto:**

  ```powershell
  python apps/backend/scripts/supabase_seed.py --schema
  ```

  Aplica el esquema y carga los datos. La cadena de conexión llega solo por `SUPABASE_DB_URL`.

- **Editor SQL de Supabase:** pegue el archivo de `migrations/` y ejecútelo.

- **Supabase CLI:** `supabase --workdir infra db push`, con el proyecto ya enlazado mediante `supabase link`.

Nunca guarde la cadena de conexión ni la contraseña en el repositorio. La guía completa está en [despliegue en Azure y Supabase](../../docs/funcionamiento/despliegue.md).
