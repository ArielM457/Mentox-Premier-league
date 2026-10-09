from collections.abc import Callable
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from match_intelligence.domain.contracts import MatchEvent


class MatchEventEnvelope(BaseModel):
    """Sobre observable que transporta un evento sin modificarlo."""

    model_config = ConfigDict(extra="forbid")

    message_version: Literal["1"] = "1"
    message_id: str = Field(min_length=1)
    message_type: Literal["match_event.created"] = "match_event.created"
    produced_at: AwareDatetime
    producer: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    payload: MatchEvent


Clock = Callable[[], datetime]
MessageIdFactory = Callable[[], str]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_message_id() -> str:
    return f"msg-{uuid4()}"


def create_match_event_envelope(
    event: MatchEvent,
    *,
    producer: str,
    clock: Clock = utc_now,
    message_id_factory: MessageIdFactory = new_message_id,
) -> MatchEventEnvelope:
    """Crea el sobre con una copia validada del evento deportivo."""
    return MatchEventEnvelope(
        message_id=message_id_factory(),
        produced_at=clock(),
        producer=producer,
        correlation_id=event.match_id,
        payload=event,
    )
