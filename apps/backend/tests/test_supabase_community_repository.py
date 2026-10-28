from datetime import UTC, datetime
from types import SimpleNamespace

from match_intelligence.adapters.storage.supabase_community import SupabaseCommunityRepository
from match_intelligence.application.community import Message, MessageKind, Vote


class FakeQuery:
    def __init__(self, client, table: str) -> None:
        self.client = client
        self.table = table
        self.operation = "select"
        self.value = None

    def select(self, _fields):
        return self

    def eq(self, _field, _value):
        return self

    def order(self, _field):
        return self

    def upsert(self, value):
        self.operation = "upsert"
        self.value = value
        return self

    def insert(self, value):
        self.operation = "insert"
        self.value = value
        return self

    def execute(self):
        if self.operation != "select":
            self.client.writes.append((self.table, self.operation, self.value))
        return SimpleNamespace(data=self.client.rows.get(self.table, []))


class FakeClient:
    def __init__(self) -> None:
        self.writes = []
        self.rows = {
            "community_votes": [{"client_id": "client-001", "author": "Ana", "vote": "approve"}],
            "community_messages": [{
                "message_id": "msg-saved",
                "kind": "suggestion",
                "author": "Ana",
                "text": "Explica mejor la presión",
                "created_at": "2026-10-26T12:00:00+00:00",
            }],
        }

    def table(self, name: str):
        return FakeQuery(self, name)


def test_room_is_loaded_and_new_participation_is_persisted() -> None:
    client = FakeClient()
    repository = SupabaseCommunityRepository(client)
    topic = "community/match-1/draft-1"

    room = repository.load_room(topic)
    assert room.votes["client-001"][0] is Vote.APPROVE
    assert room.messages[0].text == "Explica mejor la presión"

    repository.save_vote(topic, "client-002", "Luis", Vote.REJECT)
    repository.save_message(topic, "client-002", Message(
        message_id="msg-new",
        kind=MessageKind.CHAT,
        author="Luis",
        text="Coincido con la sugerencia",
        created_at=datetime.now(UTC),
    ))

    assert [write[0] for write in client.writes] == ["community_votes", "community_messages"]
    assert client.writes[0][2]["vote"] == "reject"
    assert client.writes[1][2]["draft_id"] == "draft-1"
