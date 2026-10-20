from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from match_intelligence.domain.contracts import MatchEvent, MatchMetadata
from match_intelligence.domain.presentation import NarrativeDraft, OverlayMessage


class MatchPersistence(Protocol):
    """Persistencia secundaria. Nunca debe detener el partido en vivo."""

    def save_match(self, metadata: MatchMetadata, events: Sequence[MatchEvent]) -> None: ...

    def save_moments(self, moments: Sequence[OverlayMessage]) -> None: ...

    def save_question(
        self,
        *,
        match_id: str,
        video_time_ms: int,
        question: str,
        answer: NarrativeDraft,
    ) -> None: ...


class NullMatchPersistence:
    def save_match(self, metadata: MatchMetadata, events: Sequence[MatchEvent]) -> None:
        return None

    def save_moments(self, moments: Sequence[OverlayMessage]) -> None:
        return None

    def save_question(
        self,
        *,
        match_id: str,
        video_time_ms: int,
        question: str,
        answer: NarrativeDraft,
    ) -> None:
        return None
