"""Prueba manual de carga y descarga para DV-US-09 con datos sintéticos."""

import asyncio
from hashlib import sha256
import json
import os
from uuid import uuid4

from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.adapters.storage.azure_blob import AzureBlobArtifactStore
from match_intelligence.application.artifacts import (
    Artifact,
    ArtifactKind,
    ArtifactProvenance,
)


def required_setting(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Falta la variable obligatoria {name}")
    return value


async def main() -> None:
    account_url = required_setting("AZURE_BLOB_SERVICE_ENDPOINT")
    match_id = f"synthetic-storage-{uuid4()}"
    match = generate_acceptance_match(match_id=match_id)
    content = json.dumps(
        {
            "metadata": match.metadata.model_dump(mode="json"),
            "events": [event.model_dump(mode="json") for event in match.events],
        },
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    artifact = Artifact(
        artifact_id=f"match-{uuid4()}.json",
        match_id=match_id,
        kind=ArtifactKind.SYNTHETIC_MATCH,
        provenance=ArtifactProvenance.SYNTHETIC,
        origin="dv-us-09-smoke",
        content_type="application/json",
        content=content,
    )
    store = AzureBlobArtifactStore.from_default_credential(account_url=account_url)

    try:
        location = await store.store(artifact)
        restored = await store.retrieve(location)
        result = {
            "container": location.container,
            "blob_name": location.blob_name,
            "match_id": location.match_id,
            "origin": location.origin,
            "provenance": location.provenance.value,
            "bytes": len(restored.content),
            "sha256": sha256(restored.content).hexdigest(),
            "content_matches": restored.content == content,
        }
        print(json.dumps(result, indent=2))
        if not result["content_matches"]:
            raise RuntimeError("El contenido recuperado no coincide")
    finally:
        await store.close()


if __name__ == "__main__":
    asyncio.run(main())
