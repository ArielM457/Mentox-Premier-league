from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from match_intelligence.domain.contracts import MatchEvent, MatchMetadata
from match_intelligence.domain.presentation import EditorialStatus, NarrativeDraft, OverlayMessage


@dataclass(frozen=True)
class PersistedSummary:
    draft: NarrativeDraft
    status: EditorialStatus
    reviewer: str | None = None
    note: str | None = None
    decided_at: datetime | None = None


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

    def save_summary(
        self,
        *,
        match_id: str,
        draft: NarrativeDraft,
        status: EditorialStatus,
        reviewer: str | None,
        note: str | None,
        decided_at: datetime | None,
    ) -> None: ...

    def load_summaries(self, match_id: str) -> list[PersistedSummary]: ...


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

    def save_summary(
        self,
        *,
        match_id: str,
        draft: NarrativeDraft,
        status: EditorialStatus,
        reviewer: str | None,
        note: str | None,
        decided_at: datetime | None,
    ) -> None:
        return None

    def load_summaries(self, match_id: str) -> list[PersistedSummary]:
        return []
