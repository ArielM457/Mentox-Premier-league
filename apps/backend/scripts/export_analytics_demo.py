"""Genera el tablero de demostración de Persona 2 con datos del motor real.

Desde la raíz del repositorio::

    python apps/backend/scripts/export_analytics_demo.py
    python apps/backend/scripts/export_analytics_demo.py --fragmento <ruta.html>

Escribe ``experiments/analytics-demo/tablero.html``, que se abre
directamente en el navegador. ``--fragmento`` escribe además la misma página sin
el envoltorio ``<html>`` para publicarla como artefacto.
"""

import argparse
import json
import sys
from pathlib import Path

# Los escenarios y datos simulados son de prueba y viven en tests/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from analytics_demo import build_demo_data

DEMO = Path(__file__).resolve().parents[3] / "experiments" / "analytics-demo"
WRAPPER = (
    '<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    "</head>\n<body>\n{content}\n</body>\n</html>\n"
)


def render_page() -> str:
    template = (DEMO / "plantilla.html").read_text(encoding="utf-8")
    data = json.dumps(build_demo_data(), ensure_ascii=False, separators=(",", ":"))
    return template.replace("__DATOS__", data.replace("</", "<\\/"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fragmento", type=Path)
    args = parser.parse_args()
    page = render_page()
    (DEMO / "tablero.html").write_text(WRAPPER.format(content=page), encoding="utf-8")
    print(f"tablero.html: {(DEMO / 'tablero.html').stat().st_size} bytes")
    if args.fragmento:
        args.fragmento.write_text(page, encoding="utf-8")
        print(f"{args.fragmento}: {args.fragmento.stat().st_size} bytes")


if __name__ == "__main__":
    main()
