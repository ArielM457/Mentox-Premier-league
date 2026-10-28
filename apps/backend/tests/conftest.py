"""Configuración común de las pruebas."""

import os

import pytest

import editor_tokens

# Las pruebas no leen el .env de cada persona: un MATCH_SOURCE=supabase o los agentes de Azure
# en ese archivo cambiarían su resultado.
os.environ["MATCH_INTELLIGENCE_ENV_FILE"] = ""


@pytest.fixture
def editor_headers():
    """Sesión de editor válida: la API comprueba los tokens con la clave de prueba."""
    from match_intelligence.adapters.http.editor_auth import get_editor_verifier
    from match_intelligence.main import app

    app.dependency_overrides[get_editor_verifier] = editor_tokens.verifier
    yield editor_tokens.headers()
    app.dependency_overrides.pop(get_editor_verifier, None)
