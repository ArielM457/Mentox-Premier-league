"""Cada tipo de momento que llega a la pantalla tiene nombre en la interfaz, en los dos idiomas."""

import re
from pathlib import Path

import pytest

from match_intelligence.adapters.http.registry import _default_registry
from match_intelligence.adapters.provisional.narrative import _ANALYTICS_KINDS
from match_intelligence.domain.presentation import ViewerMode, ViewerPreferences

STRINGS = Path(__file__).resolve().parents[2] / "frontend/src/i18n/strings.js"


def labelled_kinds() -> list[set[str]]:
    """Claves de los bloques ``kinds`` de español e inglés."""
    text = re.sub(r"//[^\n]*", "", STRINGS.read_text(encoding="utf-8"))
    blocks = re.findall(r"^  kinds: \{(.*?)^  \},", text, re.S | re.M)
    assert len(blocks) == 2, "strings.js debe tener un bloque kinds por idioma"
    return [set(re.findall(r"(\w+):", block)) for block in blocks]


@pytest.mark.parametrize("engine", ["provisional", "persona2"])
def test_every_emitted_kind_has_a_label(monkeypatch: pytest.MonkeyPatch, engine: str) -> None:
    monkeypatch.setenv("ANALYTICS_ENGINE", engine)
    monkeypatch.delenv("MATCH_SOURCE", raising=False)
    registry = _default_registry()
    emitted = {
        overlay.kind
        for session in registry.all()
        for mode in (ViewerMode.CASUAL, ViewerMode.ANALYST)
        for overlay in session.overlays(ViewerPreferences(mode=mode), until_video_ms=session.duration_ms).overlays
    }
    for labels in labelled_kinds():
        assert emitted - labels == set()


def test_persona_2_kinds_have_a_label() -> None:
    """Incluye los que el escenario sintético no llega a producir."""
    for labels in labelled_kinds():
        assert set(_ANALYTICS_KINDS) - labels == set()
