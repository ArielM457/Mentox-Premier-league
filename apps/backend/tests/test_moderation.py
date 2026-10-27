"""Filtro de contenido de los comentarios de la comunidad."""

import pytest

from match_intelligence.application.moderation import Rejection, moderate


@pytest.mark.parametrize(
    "text",
    [
        "Muy buen resumen, pero falta el gol de Río Unido",
        "Esta computadora computa bien",
        "maldita suerte en el segundo tiempo",
        "¡Qué golazo! jajajajajajaja",
        "Gilberto y Cumbre jugaron genial",
    ],
)
def test_clean_comments_pass(text: str) -> None:
    assert moderate(text).allowed


@pytest.mark.parametrize(
    ("text", "rejection"),
    [
        ("eres un put4", Rejection.PROFANITY),
        ("p.u.t.a", Rejection.PROFANITY),
        ("puuuuta madre", Rejection.PROFANITY),
        ("HIJUEPUTA", Rejection.PROFANITY),
        ("el árbitro es un imbécil", Rejection.PROFANITY),
        ("what the fuck", Rejection.PROFANITY),
        ("mira www.spam.com", Rejection.LINK),
        ("visita https://ejemplo.org", Rejection.LINK),
        ("aaaaaaaaaaaaaa", Rejection.SPAM),
        ("   ", Rejection.EMPTY),
        ("x" * 501, Rejection.TOO_LONG),
    ],
)
def test_bad_comments_are_rejected(text: str, rejection: Rejection) -> None:
    result = moderate(text)
    assert not result.allowed and result.rejection is rejection and result.reason
