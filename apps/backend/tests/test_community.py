"""Revisión comunitaria: moderación, votos, sugerencias y chat en tiempo real."""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from match_intelligence.adapters.http.community_router import get_community_service
from match_intelligence.adapters.http.registry import DEMO_MATCH_ID, _default_registry, get_registry
from match_intelligence.application.community import (
    CommunityError,
    CommunityService,
    InMemoryMessageBus,
    MessageKind,
    ModerationError,
    RateLimitError,
    Vote,
)
from match_intelligence.main import app

BASE = f"/api/v1/matches/{DEMO_MATCH_ID}"
CLIENT = "cliente-prueba-1"


# ----- servicio -------------------------------------------------------------

class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_one_vote_per_person_and_it_can_change() -> None:
    service = CommunityService(InMemoryMessageBus())
    service.vote("t", "ana", "Ana", Vote.APPROVE)
    service.vote("t", "luis", "Luis", Vote.REJECT)
    tally = service.vote("t", "ana", "Ana", Vote.REJECT)
    assert (tally.approve, tally.reject, tally.total, tally.approve_pct) == (0, 2, 2, 0)
    assert service.snapshot("t", "ana").my_vote is Vote.REJECT


def test_messages_are_split_into_suggestions_and_chat() -> None:
    clock = Clock()
    service = CommunityService(InMemoryMessageBus(), clock=clock)
    service.post("t", "ana", "Ana", MessageKind.SUGGESTION, "Nombra al asistente del gol")
    clock.now += 5
    service.post("t", "ana", "Ana", MessageKind.CHAT, "  hola   a todos ")
    room = service.snapshot("t")
    assert [m.text for m in room.suggestions] == ["Nombra al asistente del gol"]
    assert [m.text for m in room.chat] == ["hola a todos"]


def test_rate_limit_per_person() -> None:
    clock = Clock()
    service = CommunityService(InMemoryMessageBus(), clock=clock)
    service.post("t", "ana", "Ana", MessageKind.CHAT, "uno")
    with pytest.raises(RateLimitError):
        service.post("t", "ana", "Ana", MessageKind.CHAT, "dos")
    service.post("t", "luis", "Luis", MessageKind.CHAT, "otro usuario sí puede")
    clock.now += 2.1
    service.post("t", "ana", "Ana", MessageKind.CHAT, "dos")


def test_offensive_text_or_name_is_not_stored() -> None:
    service = CommunityService(InMemoryMessageBus())
    with pytest.raises(ModerationError):
        service.post("t", "ana", "Ana", MessageKind.CHAT, "qué resumen de mierda")
    with pytest.raises(ModerationError):
        service.vote("t", "ana", "Pendejo", Vote.APPROVE)
    with pytest.raises(CommunityError):
        service.vote("t", "ana", "   ", Vote.APPROVE)
    assert service.snapshot("t").chat == [] and service.snapshot("t").tally.total == 0


def test_bus_fans_out_to_every_subscriber() -> None:
    async def scenario() -> list[dict]:
        bus = InMemoryMessageBus()
        first, second = bus.subscribe("t"), bus.subscribe("t")
        pending = [asyncio.ensure_future(anext(first)), asyncio.ensure_future(anext(second))]
        await asyncio.sleep(0)
        bus.publish("t", {"type": "vote"})
        bus.publish("otro", {"type": "ignorado"})
        received = await asyncio.gather(*pending)
        await first.aclose()
        await second.aclose()
        assert bus.subscribers("t") == 0
        return received

    assert asyncio.run(scenario()) == [{"type": "vote"}, {"type": "vote"}]


# ----- HTTP -------------------------------------------------------------------

@pytest.fixture
def client() -> TestClient:
    registry = _default_registry()
    community = CommunityService(InMemoryMessageBus())
    app.dependency_overrides[get_registry] = lambda: registry
    app.dependency_overrides[get_community_service] = lambda: community
    yield TestClient(app)
    app.dependency_overrides.clear()


def summary_id(client: TestClient) -> str:
    return client.get(f"{BASE}/summary").json()["draft"]["draft_id"]


def test_room_requires_existing_summary(client: TestClient) -> None:
    assert client.get(f"{BASE}/community/no-existe").status_code == 404
    room = client.get(f"{BASE}/community/{summary_id(client)}").json()
    assert room["tally"] == {"approve": 0, "reject": 0, "total": 0, "approve_pct": None}


def test_vote_message_and_listing(client: TestClient) -> None:
    draft = summary_id(client)
    url = f"{BASE}/community/{draft}"
    tally = client.post(f"{url}/votes", json={"client_id": CLIENT, "author": "Ana", "vote": "approve"}).json()
    assert tally["approve"] == 1 and tally["approve_pct"] == 100
    sent = client.post(f"{url}/messages", json={"client_id": CLIENT, "author": "Ana", "kind": "suggestion", "text": "Agrega el minuto del gol"})
    assert sent.status_code == 201 and sent.json()["kind"] == "suggestion"
    room = client.get(url, params={"client_id": CLIENT}).json()
    assert room["my_vote"] == "approve" and room["suggestions"][0]["text"] == "Agrega el minuto del gol"
    listing = client.get(f"{BASE}/community").json()
    assert listing == [{"draft_id": draft, "tally": tally}]


def test_moderation_and_rate_limit_over_http(client: TestClient) -> None:
    url = f"{BASE}/community/{summary_id(client)}/messages"
    body = {"client_id": CLIENT, "author": "Ana", "kind": "chat"}
    bad = client.post(url, json={**body, "text": "qué mierda de resumen"})
    assert bad.status_code == 422 and bad.json()["rejection"] == "profanity"
    assert client.post(url, json={**body, "text": "primer mensaje"}).status_code == 201
    fast = client.post(url, json={**body, "text": "segundo mensaje"})
    assert fast.status_code == 429 and int(fast.headers["Retry-After"]) >= 1


class _ConnectedRequest:
    """Petición que sigue conectada hasta que la prueba la cierre."""

    def __init__(self) -> None:
        self.connected = True

    async def is_disconnected(self) -> bool:
        return not self.connected


def test_live_stream_delivers_votes_and_messages() -> None:
    """Un navegador suscrito recibe lo que otro publica, sin recargar.

    Se recorre el generador SSE directamente: el TestClient de Starlette espera
    a que termine la respuesta y un canal en vivo no termina nunca.
    """
    from match_intelligence.adapters.http.community_router import _events

    async def scenario() -> list[tuple[str, dict]]:
        service = CommunityService(InMemoryMessageBus())
        request = _ConnectedRequest()
        stream = _events(request, "t", service)
        frames = [await anext(stream)]
        service.vote("t", "ana", "Ana", Vote.REJECT)
        service.post("t", "ana", "Ana", MessageKind.CHAT, "¡en vivo!")
        frames += [await anext(stream), await anext(stream)]
        request.connected = False
        await stream.aclose()
        parsed = []
        for frame in frames:
            event_line, data_line = frame.strip().split("\n")
            parsed.append((event_line[7:], json.loads(data_line[6:])))
        return parsed

    received = asyncio.run(scenario())
    assert received[0][0] == "ready"
    assert received[1][0] == "vote" and received[1][1]["tally"]["reject"] == 1
    assert received[2][0] == "message" and received[2][1]["message"]["text"] == "¡en vivo!"


def test_stream_route_rejects_unknown_summary(client: TestClient) -> None:
    response = client.get(f"{BASE}/community/no-existe/stream")
    assert response.status_code == 404 and response.headers["content-type"].startswith("application/json")
