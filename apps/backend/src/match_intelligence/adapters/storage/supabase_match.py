from __future__ import annotations

import logging
import os
from collections.abc import Sequence

from match_intelligence.application.persistence import MatchPersistence, NullMatchPersistence
from match_intelligence.domain.contracts import MatchEvent, MatchMetadata
from match_intelligence.domain.presentation import NarrativeDraft, OverlayMessage

logger = logging.getLogger(__name__)


class SupabaseMatchRepository:
    """Escritura idempotente en Supabase mediante su Data API."""

    def __init__(self, client) -> None:
        self._client = client
        self._saved_moments: set[str] = set()

    @classmethod
    def from_environment(cls) -> MatchPersistence:
        if os.getenv("SUPABASE_ENABLED", "false").casefold() not in {"1", "true", "yes"}:
            return NullMatchPersistence()
        url = os.getenv("SUPABASE_URL", "").strip()
        key = os.getenv("SUPABASE_SECRET_KEY", "").strip()
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_ENABLED=true requiere SUPABASE_URL y SUPABASE_SECRET_KEY"
            )
        from supabase import create_client

        return cls(create_client(url, key))

    def _safe(self, operation: str, callback) -> None:
        try:
            callback()
        except Exception as exc:  # La persistencia secundaria no detiene el directo.
            logger.warning("Supabase %s falló: %s", operation, type(exc).__name__)

    def save_match(self, metadata: MatchMetadata, events: Sequence[MatchEvent]) -> None:
        def write() -> None:
            duration_ms = max((event.video_time_ms or 0 for event in events), default=0) + 8_000
            self._client.table("matches").upsert({
                "id": metadata.match_id,
                "home_team": metadata.home_team.name,
                "away_team": metadata.away_team.name,
                "duration_ms": duration_ms,
                "metadata": metadata.model_dump(mode="json"),
            }).execute()
            if events:
                self._client.table("match_events").upsert([
                    {
                        "event_id": event.event_id,
                        "match_id": metadata.match_id,
                        "video_time_ms": event.video_time_ms,
                        "clock_ms": event.clock_ms,
                        "event_type": event.type.value,
                        "payload": event.model_dump(mode="json"),
                    }
                    for event in events
                ]).execute()

        self._safe("save_match", write)

    def save_moments(self, moments: Sequence[OverlayMessage]) -> None:
        pending = [moment for moment in moments if moment.message_id not in self._saved_moments]
        if not pending:
            return

        def write() -> None:
            self._client.table("moments").upsert([
                {
                    "message_id": moment.message_id,
                    "match_id": moment.match_id,
                    "candidate_id": moment.candidate_id,
                    "video_time_ms": moment.video_time_ms,
                    "priority": moment.priority,
                    "kind": moment.kind,
                    "headline": moment.headline,
                    "explanation": moment.explanation,
                    "source_event_ids": moment.source_event_ids,
                    "payload": moment.model_dump(mode="json"),
                }
                for moment in pending
            ]).execute()
            self._saved_moments.update(moment.message_id for moment in pending)

        self._safe("save_moments", write)

    def save_question(
        self,
        *,
        match_id: str,
        video_time_ms: int,
        question: str,
        answer: NarrativeDraft,
    ) -> None:
        self._safe("save_question", lambda: self._client.table("assistant_messages").insert({
            "match_id": match_id,
            "video_time_ms": video_time_ms,
            "question": question,
            "headline": answer.headline,
            "explanation": answer.explanation,
            "source_event_ids": answer.source_event_ids,
        }).execute())
