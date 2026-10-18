"""Repite un partido de Supabase en ``match-events`` al ritmo del vídeo (Persona 2).

Simula la transmisión en directo para el procesador continuo: lee el partido
de Supabase, lo guarda como un partido nuevo (``<match_id>-live-<hora>``) para
que el procesador tenga sus metadatos y no lo confunda con una repetición
anterior, y publica sus eventos respetando ``video_time_ms`` dividido por la
velocidad. Variables (la cadena de Supabase es secreta y no se imprime)::

    EVENT_HUB_FULLY_QUALIFIED_NAMESPACE=<namespace>.servicebus.windows.net
    EVENT_HUB_NAME=match-events
    SUPABASE_DB_URL=<secreto>
    REPLAY_MATCH_ID=synthetic-analytics-001   # opcional
    REPLAY_SPEED=8                            # opcional; 1 = tiempo real

Desde la raíz del repositorio::

    python apps/backend/scripts/replay_match_to_event_hubs.py
"""

import asyncio
import json
import os
from datetime import UTC, datetime
from time import monotonic

from match_intelligence.adapters.messaging.azure_event_hubs import AzureEventHubPublisher
from match_intelligence.adapters.storage.supabase_store import (
    REPLAY_SCENARIO,
    CatalogEntry,
    SupabaseMatchStore,
    with_match_id,
)


def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Falta la variable obligatoria {name}")
    return value


async def main() -> None:
    namespace = required("EVENT_HUB_FULLY_QUALIFIED_NAMESPACE")
    store = SupabaseMatchStore.from_env()
    if store is None:
        raise RuntimeError("Falta la variable obligatoria SUPABASE_DB_URL")
    source_id = os.getenv("REPLAY_MATCH_ID", "synthetic-analytics-001")
    speed = float(os.getenv("REPLAY_SPEED", "8"))
    if speed <= 0:
        raise RuntimeError("REPLAY_SPEED debe ser mayor que 0")

    source = await asyncio.to_thread(store.load_match, source_id)
    if source is None:
        raise RuntimeError(f"No existe el partido {source_id} en Supabase")
    stamp = datetime.now(UTC)
    live_id = f"{source_id}-live-{stamp:%Y%m%d%H%M%S}"
    match = with_match_id(source, live_id)
    goalkeepers = frozenset(p.player_id for p in match.metadata.players if p.shirt_number == 1)
    await asyncio.to_thread(
        store.replace_match, match,
        CatalogEntry(title=f"Repetición en directo de {source_id}", scenario=REPLAY_SCENARIO, kickoff_at=stamp),
        goalkeeper_player_ids=goalkeepers,
    )
    print(json.dumps({"replay": live_id, "source": source_id, "events": len(match.events), "speed": speed}))

    publisher = AzureEventHubPublisher.from_default_credential(
        fully_qualified_namespace=namespace,
        eventhub_name=os.getenv("EVENT_HUB_NAME", "match-events"),
        producer="supabase-replay",
    )
    started = monotonic()
    first_video_ms = next((e.video_time_ms for e in match.events if e.video_time_ms is not None), 0)
    try:
        for event in match.events:
            if event.video_time_ms is not None:
                due = (event.video_time_ms - first_video_ms) / 1000 / speed
                await asyncio.sleep(max(0.0, due - (monotonic() - started)))
            await publisher.publish(event)
            print(json.dumps({
                "match_id": live_id, "event_id": event.event_id, "type": event.type.value,
                "video_time_ms": event.video_time_ms,
            }))
    finally:
        await publisher.close()
    print(json.dumps({
        "replay": live_id, "published": len(publisher.receipts), "failed": len(publisher.failures),
        "seconds": round(monotonic() - started, 1),
    }))


if __name__ == "__main__":
    asyncio.run(main())
