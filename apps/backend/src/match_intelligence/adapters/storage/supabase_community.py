from __future__ import annotations

import logging
import os
from datetime import datetime

from match_intelligence.application.community import (
    CommunityPersistence,
    Message,
    MessageKind,
    NullCommunityPersistence,
    PersistedRoom,
    Vote,
)

logger = logging.getLogger(__name__)


def _parts(topic: str) -> tuple[str, str]:
    prefix, match_id, draft_id = topic.split("/", 2)
    if prefix != "community":
        raise ValueError("Tema de comunidad inválido")
    return match_id, draft_id


class SupabaseCommunityRepository:
    """Votos y comentarios persistentes mediante la Data API de Supabase."""

    def __init__(self, client) -> None:
        self._client = client

    @classmethod
    def from_environment(cls) -> CommunityPersistence:
        if os.getenv("SUPABASE_ENABLED", "false").casefold() not in {"1", "true", "yes"}:
            return NullCommunityPersistence()
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
        except Exception as exc:  # La comunidad sigue disponible en memoria.
            logger.warning("Supabase %s falló: %s", operation, type(exc).__name__)

    def load_room(self, topic: str) -> PersistedRoom:
        try:
            match_id, draft_id = _parts(topic)
            votes_response = (
                self._client.table("community_votes")
                .select("client_id,author,vote")
                .eq("match_id", match_id)
                .eq("draft_id", draft_id)
                .execute()
            )
            messages_response = (
                self._client.table("community_messages")
                .select("message_id,kind,author,text,created_at")
                .eq("match_id", match_id)
                .eq("draft_id", draft_id)
                .order("created_at")
                .execute()
            )
            votes = {
                row["client_id"]: (Vote(row["vote"]), row["author"])
                for row in (votes_response.data or [])
            }
            messages = [
                Message(
                    message_id=row["message_id"],
                    kind=MessageKind(row["kind"]),
                    author=row["author"],
                    text=row["text"],
                    created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
                )
                for row in (messages_response.data or [])
            ]
            return PersistedRoom(votes=votes, messages=messages)
        except Exception as exc:
            logger.warning("Supabase load_community falló: %s", type(exc).__name__)
            return PersistedRoom()

    def save_vote(self, topic: str, client_id: str, author: str, vote: Vote) -> None:
        match_id, draft_id = _parts(topic)
        self._safe("save_community_vote", lambda: self._client.table("community_votes").upsert({
            "match_id": match_id,
            "draft_id": draft_id,
            "client_id": client_id,
            "author": author,
            "vote": vote.value,
        }).execute())

    def save_message(self, topic: str, client_id: str, message: Message) -> None:
        match_id, draft_id = _parts(topic)
        self._safe("save_community_message", lambda: self._client.table("community_messages").insert({
            "message_id": message.message_id,
            "match_id": match_id,
            "draft_id": draft_id,
            "client_id": client_id,
            "kind": message.kind.value,
            "author": message.author,
            "text": message.text,
            "created_at": message.created_at.isoformat(),
        }).execute())
