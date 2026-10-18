"""Crea el esquema y los datos ficticios de la analítica en Supabase (Persona 2).

1. ``--schema`` aplica ``infra/supabase/migrations`` (idempotente).
2. Guarda cada partido sintético con sus jugadores y eventos ``MatchEvent 1.0``.
3. Guarda observaciones de seguimiento simuladas con el formato de Persona 1.
4. Ejecuta el procesador analítico y guarda su registro, igual que en Blob.

Volver a ejecutarlo reemplaza esos partidos y borra sus análisis anteriores.
La cadena de conexión llega solo por variable de entorno y no se imprime::

    SUPABASE_DB_URL=postgresql://postgres.<ref>:<contraseña>@aws-0-<región>.pooler.supabase.com:5432/postgres

Desde la raíz del repositorio::

    python apps/backend/scripts/supabase_seed.py --dry-run
    python apps/backend/scripts/supabase_seed.py --schema
"""

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path

# Los datos simulados viven con las pruebas, fuera del código de producción.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from match_intelligence.adapters.storage.supabase_store import (  # noqa: E402
    DATABASE_URL_VARIABLE,
    SupabaseMatchStore,
)
from supabase_seed_data import DEFAULT_MATCHES, prepare, summary, write  # noqa: E402

MIGRATIONS = Path(__file__).resolve().parents[3] / "infra" / "supabase" / "migrations"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--schema", action="store_true", help="aplica las migraciones antes de cargar")
    parser.add_argument("--dry-run", action="store_true", help="genera y cuenta sin conectarse")
    parser.add_argument("--only", action="append", default=[], metavar="MATCH_ID",
                        help="carga solo ese partido (se puede repetir)")
    args = parser.parse_args()

    specs = [s for s in DEFAULT_MATCHES if not args.only or s.match_id in args.only]
    unknown = set(args.only) - {s.match_id for s in DEFAULT_MATCHES}
    if unknown:
        parser.error(f"partidos desconocidos: {', '.join(sorted(unknown))}")

    store = None
    if not args.dry_run:
        store = SupabaseMatchStore.from_env()
        if store is None:
            parser.error(f"falta la variable {DATABASE_URL_VARIABLE} (o use --dry-run)")
        if args.schema:
            for migration in sorted(MIGRATIONS.glob("*.sql")):
                store.apply_sql(migration.read_text(encoding="utf-8"))
                print(json.dumps({"migration": migration.name, "applied": True}))

    for spec in specs:
        prepared = asyncio.run(prepare(spec))
        result = summary(prepared)
        if store is not None:
            result["stored"] = len(write(store, prepared))
        print(json.dumps(result, ensure_ascii=False))

    if store is not None:
        for row in store.summaries():
            print(json.dumps({"in_database": asdict(row)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
