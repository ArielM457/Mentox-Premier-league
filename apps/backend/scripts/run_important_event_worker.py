"""Consume un lote de ``important-events``; base reproducible del worker."""

from __future__ import annotations

import argparse
import asyncio
import json

from match_intelligence.adapters.messaging.important_event_worker import build_azure_worker
from match_intelligence.application.important_event_worker import (
    DispatchRecordingHandler,
    ImportantEventProcessor,
)


async def run(max_messages: int, wait_seconds: float) -> None:
    processor = ImportantEventProcessor(DispatchRecordingHandler())
    worker, client, credential, renewer = await build_azure_worker(processor)
    try:
        async with client:
            async with worker.receiver:
                counts = await worker.run_once(
                    max_messages=max_messages,
                    max_wait_time=wait_seconds,
                )
        print(json.dumps(counts, indent=2))
    finally:
        await renewer.close()
        await credential.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-messages", type=int, default=10)
    parser.add_argument("--wait-seconds", type=float, default=10)
    args = parser.parse_args()
    asyncio.run(run(args.max_messages, args.wait_seconds))


if __name__ == "__main__":
    main()
