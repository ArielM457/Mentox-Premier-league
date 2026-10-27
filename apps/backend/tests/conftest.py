"""Configuración común de las pruebas."""

import os

# Las pruebas no leen el .env de cada persona: un MATCH_SOURCE=supabase o los agentes de Azure
# en ese archivo cambiarían su resultado.
os.environ["MATCH_INTELLIGENCE_ENV_FILE"] = ""
