"""Llamados breves que invitan a explorar la evidencia de una jugada."""

from __future__ import annotations

import zlib
from dataclasses import dataclass

from match_intelligence.domain.presentation import Language


@dataclass(frozen=True)
class ActionCallout:
    callout_id: str
    kind: str
    language: str
    text: str


_PHRASES: dict[str, tuple[str, ...]] = {
    "goal": (
        "¿Cómo nació el gol? Revisa la jugada completa.",
        "El marcador cambió. Mira los eventos que explican el gol.",
        "¿Gol inevitable o error evitable? Descubre qué pasó.",
        "La red se movió, pero la historia empezó antes. Mírala.",
        "¿Quién hizo posible el gol? Sigue la secuencia.",
    ),
    "shot": (
        "¿Era una ocasión clara? Mira la posición y el contexto.",
        "El remate cuenta una historia. Revisa cómo se creó.",
        "¿Peligro real o intento lejano? Comprueba la jugada.",
        "Estuvo cerca. Mira qué abrió el espacio para rematar.",
        "¿Quién fabricó esta ocasión? Sigue el ataque.",
    ),
    "progressive_pass": (
        "¿Un pase que rompió líneas? Mira cuánto avanzó.",
        "Ese pase cambió el ataque. Descubre por qué.",
        "¿Pase de gol en camino? Revisa la secuencia.",
        "El balón encontró un espacio. Mira cómo ocurrió.",
        "Un pase puede cambiarlo todo. Comprueba su impacto.",
    ),
    "foul": (
        "Una falta cambió el ritmo. Revisa qué ocurrió.",
        "¿Falta táctica o llegada tarde? Mira la evidencia.",
        "El juego se detuvo aquí. Descubre la razón.",
        "Contacto decisivo. Revisa quién llegó primero.",
        "¿Esta falta frenó un ataque? Sigue la jugada.",
    ),
    "yellow_card": (
        "Tremenda falta de tarjeta. Revisa los amonestados.",
        "Hay amarilla. Mira la acción que la provocó.",
        "¿Amonestación justa? Revisa el contexto de la falta.",
        "La tarjeta cambia el duelo. Descubre qué pasó.",
        "Un jugador queda condicionado. Mira por qué fue amonestado.",
    ),
    "red_card": (
        "El partido cambia con esta roja. Revisa la acción.",
        "Expulsión decisiva. Mira qué ocurrió antes de la tarjeta.",
        "Un equipo queda con diez. Descubre el motivo.",
        "¿Roja directa? Revisa la evidencia de la jugada.",
        "Momento crítico: mira cómo llegó la expulsión.",
    ),
    "recovery": (
        "Todo empezó al recuperar el balón. Sigue la secuencia.",
        "¿Robo clave? Mira dónde cambió la posesión.",
        "Recuperó y activó el ataque. Descubre cómo.",
        "Aquí volvió a tener el balón. Revisa la presión previa.",
        "Una recuperación puede abrir el partido. Mira esta.",
    ),
    "turnover": (
        "Cambió la posesión. Mira quién ganó el duelo.",
        "Una pérdida dejó espacio. Revisa qué ocurrió después.",
        "¿Error forzado o pase impreciso? Descúbrelo.",
        "El balón cambió de dueño. Sigue la transición.",
        "Esta pérdida pudo costar caro. Mira la jugada.",
    ),
    "pressure": (
        "¿Presión efectiva o acción aislada? Revisa la evidencia.",
        "La presión obligó a decidir rápido. Mira el resultado.",
        "Aquí empezó el asedio. Descubre cómo cerraron espacios.",
        "Sin dejar respirar al rival. Revisa esta presión.",
        "La presión cambió la jugada. Mira quién la inició.",
    ),
    "generic": (
        "Hay más detrás de esta jugada. Descubre por qué importa.",
        "Este momento merece otra mirada. Revisa la evidencia.",
        "¿Qué cambió aquí? Abre el análisis de la jugada.",
        "No fue una acción cualquiera. Mira su impacto.",
        "La clave está en los detalles. Descúbrelos aquí.",
    ),
}

DEFAULT_CALLOUTS = tuple(
    ActionCallout(f"cta-{kind}-{index:02d}", kind, "es", text)
    for kind, phrases in _PHRASES.items()
    for index, text in enumerate(phrases, start=1)
)

_ALIASES = {
    "fast_progression": "progressive_pass",
    "pass": "progressive_pass",
    "recovery_to_shot": "recovery",
    "high_recovery": "recovery",
    "sustained_pressure": "pressure",
    "tackle": "turnover",
}

_GENERIC_BY_LANGUAGE = {
    Language.ES: "Descubre por qué esta jugada importa.",
    Language.EN: "Discover why this play matters.",
    Language.DE: "Entdecke, warum diese Szene wichtig ist.",
    Language.ZH: "了解这次进攻为何重要。",
    Language.HI: "जानें कि यह खेल क्यों महत्वपूर्ण है।",
    Language.FR: "Découvrez pourquoi cette action compte.",
    Language.PT: "Descubra por que esta jogada importa.",
}


def select_callout(
    callouts: tuple[ActionCallout, ...], *, kind: str, language: Language, stable_id: str
) -> str:
    """Elige una frase compatible y reproducible para una misma jugada."""

    category = _ALIASES.get(kind, kind if kind in _PHRASES else "generic")
    candidates = [
        item for item in callouts if item.kind == category and item.language == language.value
    ]
    if not candidates and language is Language.ES:
        candidates = [item for item in DEFAULT_CALLOUTS if item.kind == category]
    if not candidates:
        return _GENERIC_BY_LANGUAGE.get(language, _GENERIC_BY_LANGUAGE[Language.ES])
    index = zlib.crc32(stable_id.encode("utf-8")) % len(candidates)
    return candidates[index].text
