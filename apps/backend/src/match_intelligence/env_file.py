"""Carga apps/backend/.env al iniciar la API, sin dependencias externas.

Las variables que ya existen en el entorno (la terminal o Azure) tienen prioridad: el archivo solo
completa las que faltan. MATCH_INTELLIGENCE_ENV_FILE indica otra ruta; vacía, desactiva la carga
(las pruebas lo hacen para no depender del .env de cada persona).
"""

import logging
import os
from pathlib import Path

DEFAULT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# El registro de uvicorn ya está configurado cuando importa la aplicación: así el aviso se ve.
logger = logging.getLogger("uvicorn.error")


def parse_env_file(text: str) -> dict[str, str]:
    """Líneas NOMBRE=valor; admite comentarios con #, «export» y comillas que rodean el valor."""
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").lstrip()
        name, separator, value = line.partition("=")
        name, value = name.strip(), value.strip()
        if not separator or not name.isidentifier():
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        values[name] = value
    return values


def load_env_file(path: Path | None = None) -> list[str]:
    """Añade al entorno las variables del archivo que falten y devuelve sus nombres, nunca sus valores."""
    if path is None:
        configured = os.environ.get("MATCH_INTELLIGENCE_ENV_FILE")
        if configured == "":
            return []
        path = Path(configured) if configured else DEFAULT_ENV_FILE
    if not path.is_file():
        return []
    loaded = []
    for name, value in parse_env_file(path.read_text(encoding="utf-8-sig")).items():
        if name not in os.environ:
            os.environ[name] = value
            loaded.append(name)
    if loaded:
        logger.info("Variables cargadas de %s: %s", path, ", ".join(sorted(loaded)))
    return loaded
