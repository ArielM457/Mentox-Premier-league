"""Revisión comunitaria de los resúmenes que genera la IA.

La comunidad vota si aprueba o rechaza cada resumen, deja sugerencias y
conversa en un chat. Cada cambio se publica en un bus de mensajes por tema
(un tema por resumen) y los navegadores suscritos lo reciben al instante.

El voto de la comunidad es una señal para la revisión editorial: no aprueba
ni publica el resumen por sí solo (RF-38).
"""

import asyncio
import time
import uuid
from collections import deque
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from match_intelligence.application.moderation import ModerationResult, moderate

MAX_MESSAGES = 300
RATE_LIMIT_S = 2.0
QUEUE_SIZE = 200


class Vote(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class MessageKind(StrEnum):
    CHAT = "chat"
    SUGGESTION = "suggestion"


class CommunityError(Exception):
    status_code = 400


class ModerationError(CommunityError):
    status_code = 422

    def __init__(self, result: ModerationResult) -> None:
        super().__init__(result.reason)
        self.rejection = result.rejection


class RateLimitError(CommunityError):
    status_code = 429

    def __init__(self, retry_after_s: float) -> None:
        super().__init__("Estás escribiendo muy rápido. Espera un momento.")
        self.retry_after_s = retry_after_s


@dataclass(frozen=True)
class Message:
    message_id: str
    kind: MessageKind
    author: str
    text: str
    created_at: datetime


@dataclass(frozen=True)
class Tally:
    approve: int
    reject: int

    @property
    def total(self) -> int:
        return self.approve + self.reject

    @property
    def approve_pct(self) -> int | None:
        return round(100 * self.approve / self.total) if self.total else None


@dataclass
class _Room:
    votes: dict[str, tuple[Vote, str]] = field(default_factory=dict)
    messages: deque[Message] = field(default_factory=lambda: deque(maxlen=MAX_MESSAGES))

    def tally(self) -> Tally:
        approve = sum(1 for vote, _ in self.votes.values() if vote is Vote.APPROVE)
        return Tally(approve=approve, reject=len(self.votes) - approve)


@dataclass(frozen=True)
class RoomSnapshot:
    topic: str
    tally: Tally
    my_vote: Vote | None
    suggestions: list[Message]
    chat: list[Message]


@dataclass(frozen=True)
class PersistedRoom:
    votes: dict[str, tuple[Vote, str]] = field(default_factory=dict)
    messages: list[Message] = field(default_factory=list)


class CommunityPersistence(Protocol):
    """Persistencia secundaria de la participación de la comunidad."""

    def load_room(self, topic: str) -> PersistedRoom: ...

    def save_vote(self, topic: str, client_id: str, author: str, vote: Vote) -> None: ...

    def save_message(self, topic: str, client_id: str, message: Message) -> None: ...


class NullCommunityPersistence:
    def load_room(self, topic: str) -> PersistedRoom:
        return PersistedRoom()

    def save_vote(self, topic: str, client_id: str, author: str, vote: Vote) -> None:
        return None

    def save_message(self, topic: str, client_id: str, message: Message) -> None:
        return None


class MessageBus(Protocol):
    """Publicación y suscripción por tema. Se puede reemplazar por MQTT o Azure Service Bus."""

    def publish(self, topic: str, event: dict) -> None: ...

    def subscribe(self, topic: str) -> AsyncIterator[dict]: ...


class InMemoryMessageBus:
    """Cola en memoria por suscriptor (asyncio.Queue).

    Alcanza mientras la API corra en un solo proceso, como en el despliegue
    actual (una réplica). Si un suscriptor se atrasa demasiado, se descartan
    sus eventos más viejos en vez de bloquear a los demás.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = {}

    def subscribers(self, topic: str) -> int:
        return len(self._subscribers.get(topic, ()))

    def publish(self, topic: str, event: dict) -> None:
        for queue in list(self._subscribers.get(topic, ())):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(event)

    def subscribe(self, topic: str) -> AsyncIterator[dict]:
        # La cola se registra ya, no al pedir el primer evento: así no se pierde
        # nada de lo que se publique entre la conexión y la primera lectura.
        queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
        self._subscribers.setdefault(topic, set()).add(queue)
        return self._drain(topic, queue)

    async def _drain(self, topic: str, queue: asyncio.Queue) -> AsyncIterator[dict]:
        try:
            while True:
                yield await queue.get()
        finally:
            subscribers = self._subscribers.get(topic, set())
            subscribers.discard(queue)
            if not subscribers:
                self._subscribers.pop(topic, None)


def topic_for(match_id: str, draft_id: str) -> str:
    return f"community/{match_id}/{draft_id}"


class CommunityService:
    def __init__(
        self,
        bus: MessageBus,
        *,
        persistence: CommunityPersistence | None = None,
        clock: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        rate_limit_s: float = RATE_LIMIT_S,
    ) -> None:
        self._bus = bus
        self._clock = clock
        self._now = now
        self._rate_limit_s = rate_limit_s
        self._persistence = persistence or NullCommunityPersistence()
        self._rooms: dict[str, _Room] = {}
        self._last_post: dict[str, float] = {}

    def _room(self, topic: str) -> _Room:
        if topic not in self._rooms:
            saved = self._persistence.load_room(topic)
            self._rooms[topic] = _Room(
                votes=dict(saved.votes),
                messages=deque(saved.messages, maxlen=MAX_MESSAGES),
            )
        return self._rooms[topic]

    def snapshot(self, topic: str, client_id: str | None = None) -> RoomSnapshot:
        room = self._room(topic)
        vote = room.votes.get(client_id or "")
        return RoomSnapshot(
            topic=topic,
            tally=room.tally(),
            my_vote=vote[0] if vote else None,
            suggestions=[m for m in room.messages if m.kind is MessageKind.SUGGESTION],
            chat=[m for m in room.messages if m.kind is MessageKind.CHAT],
        )

    def tallies(self, topics: list[str]) -> dict[str, Tally]:
        return {topic: self._room(topic).tally() for topic in topics}

    def vote(self, topic: str, client_id: str, author: str, vote: Vote) -> Tally:
        """Un voto por persona y resumen; volver a votar cambia el voto anterior."""
        author = self._check_author(author)
        room = self._room(topic)
        previous = room.votes.get(client_id)
        room.votes[client_id] = (vote, author)
        self._persistence.save_vote(topic, client_id, author, vote)
        tally = room.tally()
        self._bus.publish(
            topic,
            {
                "type": "vote",
                "tally": _tally_dict(tally),
                "author": author,
                "vote": vote.value,
                "changed": previous is not None and previous[0] is not vote,
            },
        )
        return tally

    def post(self, topic: str, client_id: str, author: str, kind: MessageKind, text: str) -> Message:
        author = self._check_author(author)
        result = moderate(text)
        if not result.allowed:
            raise ModerationError(result)
        key = f"{topic}|{client_id}"
        now = self._clock()
        wait = self._rate_limit_s - (now - self._last_post.get(key, float("-inf")))
        if wait > 0:
            raise RateLimitError(round(wait, 1))
        self._last_post[key] = now
        message = Message(
            message_id=f"msg-{uuid.uuid4().hex}",
            kind=kind,
            author=author,
            text=result.text,
            created_at=self._now(),
        )
        self._room(topic).messages.append(message)
        self._persistence.save_message(topic, client_id, message)
        self._bus.publish(topic, {"type": "message", "message": message_dict(message)})
        return message

    def subscribe(self, topic: str) -> AsyncIterator[dict]:
        return self._bus.subscribe(topic)

    @staticmethod
    def _check_author(author: str) -> str:
        cleaned = " ".join(author.split())
        if not cleaned:
            raise CommunityError("Escribe tu nombre para participar.")
        result = moderate(cleaned)
        if not result.allowed:
            raise ModerationError(result)
        return cleaned[:40]


def _tally_dict(tally: Tally) -> dict:
    return {"approve": tally.approve, "reject": tally.reject, "total": tally.total, "approve_pct": tally.approve_pct}


def message_dict(message: Message) -> dict:
    return {
        "message_id": message.message_id,
        "kind": message.kind.value,
        "author": message.author,
        "text": message.text,
        "created_at": message.created_at.isoformat(),
    }


tally_dict = _tally_dict
