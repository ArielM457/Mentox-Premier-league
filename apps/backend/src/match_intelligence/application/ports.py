"""Puertos que la API usa para delegar en analítica (Persona 2) y narración (Persona 3).

La API solo depende de estas interfaces. Los adaptadores provisionales de
``adapters/provisional`` las implementan con reglas simples hasta que lleguen
los módulos reales; al integrarlos basta con inyectar otra implementación en
``adapters/http/dependencies.py``.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from match_intelligence.domain.contracts import MatchEvent, MatchMetadata
from match_intelligence.domain.presentation import (
    InsightCandidate,
    MatchSnapshot,
    NarrativeDraft,
    ViewerPreferences,
)


class AnalyticsPort(Protocol):
    def snapshot(
        self,
        metadata: MatchMetadata,
        events: Sequence[MatchEvent],
        *,
        video_time_ms: int,
    ) -> MatchSnapshot:
        """Calcula el estado con los eventos ya ocurridos en ``video_time_ms``."""

    def candidates(
        self,
        metadata: MatchMetadata,
        events: Sequence[MatchEvent],
        preferences: ViewerPreferences,
    ) -> list[InsightCandidate]:
        """Propone momentos ordenados por tiempo; las preferencias solo ajustan prioridad."""


class NarrativePort(Protocol):
    def live(
        self,
        metadata: MatchMetadata,
        snapshot: MatchSnapshot,
        candidate: InsightCandidate,
        preferences: ViewerPreferences,
    ) -> NarrativeDraft: ...

    def player_quiet(
        self,
        metadata: MatchMetadata,
        player_id: str,
        *,
        since_clock_ms: int,
        until_clock_ms: int,
        preferences: ViewerPreferences,
    ) -> NarrativeDraft:
        """Mensaje del modo jugador cuando no hay novedades sobre él (RF-26)."""

    def answer(
        self,
        metadata: MatchMetadata,
        events: Sequence[MatchEvent],
        snapshot: MatchSnapshot,
        question: str,
        preferences: ViewerPreferences,
    ) -> NarrativeDraft: ...

    def summary(
        self,
        metadata: MatchMetadata,
        snapshot: MatchSnapshot,
        candidates: Sequence[InsightCandidate],
        preferences: ViewerPreferences,
    ) -> NarrativeDraft: ...

    def verify(
        self,
        metadata: MatchMetadata,
        events: Sequence[MatchEvent],
        draft: NarrativeDraft,
    ) -> "VerificationResult":
        """Contrasta el texto con sus eventos de origen (RF-39)."""


class VerificationOutcome(StrEnum):
    CONFIRMED = "confirmed"
    WITHDRAWN = "withdrawn"


@dataclass(frozen=True)
class VerificationResult:
    outcome: VerificationOutcome
    issues: list[str] = field(default_factory=list)
