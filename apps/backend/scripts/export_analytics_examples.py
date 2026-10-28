"""Regenera los ejemplos de contrato de Persona 2.

Desde la raíz del repositorio::

    python apps/backend/scripts/export_analytics_examples.py
"""

import sys
from pathlib import Path

# Los escenarios y datos simulados son de prueba y viven en tests/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from analytics_examples import build_examples, render

TARGET = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "contracts" / "analytics"


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    for name, value in build_examples().items():
        (TARGET / name).write_text(render(value), encoding="utf-8")
        print(f"{name}: {(TARGET / name).stat().st_size} bytes")


if __name__ == "__main__":
    main()
