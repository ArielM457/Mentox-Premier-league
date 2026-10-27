"""Filtro de contenido para los comentarios de la comunidad.

Rechaza groserías e insultos en español e inglés, enlaces (spam) y textos
vacíos o hechos solo de caracteres repetidos. Normaliza antes de comparar
para resistir trucos habituales: tildes, mayúsculas, números en lugar de
letras («put4»), letras estiradas («puuuta») y separadores («p.u.t.a»).
Compara palabras completas para no bloquear palabras sanas que contienen
otra («computadora» contiene «puta»).
"""

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

MAX_LENGTH = 500

# Raíces: se bloquea la palabra si es exactamente la raíz o la raíz con una terminación común.
BLOCKED_ROOTS = {
    # español
    "puta", "puto", "putita", "putazo", "hijueputa", "hijoputa", "hdp", "hdlgp", "ptm", "ctm", "conchatumadre",
    "mierda", "mierdero", "verga", "vergazo", "pendejo", "pendeja", "cabron", "cabrona", "culero", "culera",
    "culiao", "culiado", "pelotudo", "pelotuda", "boludo", "boluda", "gilipollas", "gil", "imbecil",
    "estupido", "estupida", "idiota", "maricon", "marica", "mamaguevo", "malparido", "malparida",
    "gonorrea", "chingada", "chingado", "chingar", "chingue", "joder", "jodido", "coño",
    "huevon", "huevona", "weon", "wn", "zorra", "perra", "concha", "cojudo", "cojuda",
    "mongolico", "retrasado", "subnormal", "tarado", "pajero", "malnacido",
    # inglés
    "fuck", "fucker", "fucking", "motherfucker", "shit", "bullshit", "bitch", "asshole", "bastard",
    "dick", "cunt", "whore", "slut", "retard", "faggot", "fag", "nigger", "nigga", "wanker", "twat",
}
SUFFIXES = ("", "s", "es", "a", "as", "o", "os", "ito", "ita", "itos", "itas", "azo", "aza", "ing", "er", "ers", "ed")

LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b", "@": "a", "$": "s", "!": "i", "|": "i"})
URL = re.compile(r"(https?://|www\.|\b[\w-]+\.(com|net|org|io|ly|me|xyz|bo|es|co)\b)", re.IGNORECASE)


class Rejection(StrEnum):
    EMPTY = "empty"
    TOO_LONG = "too_long"
    PROFANITY = "profanity"
    LINK = "link"
    SPAM = "spam"


REASONS = {
    Rejection.EMPTY: "El mensaje está vacío.",
    Rejection.TOO_LONG: f"El mensaje supera los {MAX_LENGTH} caracteres.",
    Rejection.PROFANITY: "El mensaje contiene lenguaje ofensivo y no cumple las normas de la comunidad.",
    Rejection.LINK: "No se permiten enlaces en los comentarios.",
    Rejection.SPAM: "El mensaje parece spam (caracteres repetidos).",
}


@dataclass(frozen=True)
class ModerationResult:
    allowed: bool
    text: str
    rejection: Rejection | None = None

    @property
    def reason(self) -> str | None:
        return REASONS[self.rejection] if self.rejection else None


def _strip_accents(text: str) -> str:
    # Conserva la ñ para no confundir «coño» con otras palabras al quitar tildes.
    text = text.replace("ñ", "\0").replace("Ñ", "\0")
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return text.replace("\0", "ñ")


def _squeeze(word: str) -> str:
    """«puuuuta» → «puta»: reduce cualquier letra repetida a una sola."""
    return re.sub(r"(.)\1+", r"\1", word)


def _is_blocked(word: str) -> bool:
    for candidate in {word, _squeeze(word)}:
        for root in BLOCKED_ROOTS:
            if candidate.startswith(root) and candidate[len(root):] in SUFFIXES:
                return True
    return False


def normalize(text: str) -> str:
    return _strip_accents(text.lower()).translate(LEET)


def words(text: str) -> list[str]:
    """Palabras normalizadas, más las que se forman uniendo letras sueltas («p.u.t.a», «p u t a»)."""
    tokens = re.findall(r"[a-zñ]+", normalize(text))
    found = list(tokens)
    run: list[str] = []
    for token in tokens + [""]:
        if len(token) == 1:
            run.append(token)
            continue
        if len(run) >= 3:
            found.append("".join(run))
        run = []
    return found


def moderate(text: str) -> ModerationResult:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return ModerationResult(False, cleaned, Rejection.EMPTY)
    if len(cleaned) > MAX_LENGTH:
        return ModerationResult(False, cleaned, Rejection.TOO_LONG)
    if URL.search(cleaned):
        return ModerationResult(False, cleaned, Rejection.LINK)
    if re.search(r"(.)\1{9,}", cleaned) or len(set(cleaned.replace(" ", ""))) == 1 and len(cleaned) > 3:
        return ModerationResult(False, cleaned, Rejection.SPAM)
    if any(_is_blocked(word) for word in words(cleaned)):
        return ModerationResult(False, cleaned, Rejection.PROFANITY)
    return ModerationResult(True, cleaned)
