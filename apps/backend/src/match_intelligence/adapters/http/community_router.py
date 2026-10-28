"""Rutas de la revisión comunitaria: votos, sugerencias y chat en tiempo real."""

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from match_intelligence.application.community import (
    CommunityError,
    CommunityService,
    MessageKind,
    RateLimitError,
    Vote,
    message_dict,
    tally_dict,
    topic_for,
)
from match_intelligence.adapters.messaging.azure_community import build_community_bus
from match_intelligence.application.match_session import MatchSession, NotFoundError

from .match_schemas import ErrorResponse
from .registry import MatchRegistry, get_registry

HEARTBEAT_S = 15

_service: CommunityService | None = None


def get_community_service() -> CommunityService:
    global _service
    if _service is None:
        from match_intelligence.adapters.storage.supabase_community import SupabaseCommunityRepository

        _service = CommunityService(
            build_community_bus(),
            persistence=SupabaseCommunityRepository.from_environment(),
        )
    return _service


async def start_community_bus() -> None:
    """Arranca el envío y la lectura del bus cuando es de Azure."""
    bus = get_community_service().bus
    if hasattr(bus, "start"):
        await bus.start()


async def close_community_bus() -> None:
    bus = _service.bus if _service is not None else None
    if bus is not None and hasattr(bus, "close"):
        await bus.close()


Community = Annotated[CommunityService, Depends(get_community_service)]
Registry = Annotated[MatchRegistry, Depends(get_registry)]


def _topic(match_id: str, draft_id: str, registry: Registry) -> str:
    """Solo se puede comentar un resumen final que exista en la cola editorial."""
    session: MatchSession = registry.get(match_id)
    if not any(record.draft.draft_id == draft_id for record in session.editorial_queue()):
        raise NotFoundError(f"No existe el resumen {draft_id}")
    return topic_for(match_id, draft_id)


Topic = Annotated[str, Depends(_topic)]
ClientId = Annotated[str, Query(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]


class TallyResponse(BaseModel):
    approve: int
    reject: int
    total: int
    approve_pct: int | None


class MessageResponse(BaseModel):
    message_id: str
    kind: Literal["chat", "suggestion"]
    author: str
    text: str
    created_at: datetime


class RoomResponse(BaseModel):
    draft_id: str
    tally: TallyResponse
    my_vote: Literal["approve", "reject"] | None
    suggestions: list[MessageResponse]
    chat: list[MessageResponse]


class VoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    author: str = Field(min_length=1, max_length=40)
    vote: Literal["approve", "reject"]


class MessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    author: str = Field(min_length=1, max_length=40)
    kind: Literal["chat", "suggestion"]
    text: str = Field(max_length=2000)


class CommunityErrorResponse(BaseModel):
    detail: str
    rejection: str | None = None
    retry_after_s: float | None = None


class SummaryTally(BaseModel):
    draft_id: str
    tally: TallyResponse


ERRORS = {
    404: {"model": ErrorResponse, "description": "Partido o resumen inexistente"},
    422: {"model": CommunityErrorResponse, "description": "El mensaje no pasó la moderación"},
    429: {"model": CommunityErrorResponse, "description": "Demasiados mensajes seguidos"},
}

router = APIRouter(prefix="/api/v1/matches/{match_id}/community", tags=["Comunidad"], responses=ERRORS)


def _error(error: CommunityError) -> JSONResponse:
    body = CommunityErrorResponse(detail=str(error), rejection=getattr(error, "rejection", None))
    headers = {}
    if isinstance(error, RateLimitError):
        body.retry_after_s = error.retry_after_s
        headers["Retry-After"] = str(max(1, round(error.retry_after_s)))
    return JSONResponse(status_code=error.status_code, content=body.model_dump(), headers=headers)


@router.get("", response_model=list[SummaryTally], summary="Votos de la comunidad por resumen")
def list_tallies(match_id: str, registry: Registry, community: Community) -> list[SummaryTally]:
    drafts = [record.draft.draft_id for record in registry.get(match_id).editorial_queue()]
    tallies = community.tallies([topic_for(match_id, d) for d in drafts])
    return [SummaryTally(draft_id=d, tally=tally_dict(tallies[topic_for(match_id, d)])) for d in drafts]


@router.get("/{draft_id}", response_model=RoomResponse, summary="Votos, sugerencias y chat de un resumen")
def get_room(draft_id: str, topic: Topic, community: Community, client_id: ClientId | None = None) -> RoomResponse:
    room = community.snapshot(topic, client_id)
    return RoomResponse(
        draft_id=draft_id,
        tally=tally_dict(room.tally),
        my_vote=room.my_vote.value if room.my_vote else None,
        suggestions=[message_dict(m) for m in room.suggestions],
        chat=[message_dict(m) for m in room.chat],
    )


@router.post(
    "/{draft_id}/votes",
    response_model=TallyResponse,
    summary="Votar si se aprueba el resumen",
    description="Un voto por persona (client_id); volver a votar lo cambia. Es una señal para la revisión editorial, no la reemplaza.",
)
async def vote(body: VoteRequest, topic: Topic, community: Community) -> TallyResponse | JSONResponse:
    try:
        return tally_dict(community.vote(topic, body.client_id, body.author, Vote(body.vote)))
    except CommunityError as error:
        return _error(error)


@router.post(
    "/{draft_id}/messages",
    response_model=MessageResponse,
    status_code=201,
    summary="Enviar una sugerencia o un mensaje al chat",
    description="Pasa por el filtro de contenido (groserías, enlaces y spam) y un límite de un mensaje cada 2 segundos.",
)
async def post_message(body: MessageRequest, topic: Topic, community: Community) -> MessageResponse | JSONResponse:
    try:
        return message_dict(community.post(topic, body.client_id, body.author, MessageKind(body.kind), body.text))
    except CommunityError as error:
        return _error(error)


@router.get(
    "/{draft_id}/stream",
    summary="Canal en tiempo real (Server-Sent Events)",
    description="Emite `ready` y después `vote` y `message` en cuanto ocurren. Envía un latido cada 15 s para mantener viva la conexión.",
    response_class=StreamingResponse,
)
async def stream(request: Request, topic: Topic, community: Community) -> StreamingResponse:
    return StreamingResponse(
        _events(request, topic, community),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


async def _events(request: Request, topic: str, community: CommunityService) -> AsyncIterator[str]:
    subscription = community.subscribe(topic)
    yield _sse("ready", {"topic": topic})
    next_event = asyncio.ensure_future(anext(subscription))
    try:
        while True:
            done, _ = await asyncio.wait({next_event}, timeout=HEARTBEAT_S)
            if await request.is_disconnected():
                return
            if not done:
                yield ": latido\n\n"
                continue
            event = next_event.result()
            yield _sse(event["type"], event)
            next_event = asyncio.ensure_future(anext(subscription))
    finally:
        next_event.cancel()
        with contextlib.suppress(asyncio.CancelledError, StopAsyncIteration):
            await next_event
        await subscription.aclose()
