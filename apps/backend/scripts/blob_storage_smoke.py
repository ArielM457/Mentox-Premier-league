"""Prueba real de DV-US-16 con artefactos exclusivamente sintéticos."""

import asyncio
from hashlib import sha256
import json
import os
from typing import Any
from uuid import uuid4

from azure.core.exceptions import ResourceExistsError

from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.adapters.storage.azure_blob import AzureBlobArtifactStore
from match_intelligence.application.artifacts import (
    Artifact,
    ArtifactKind,
    ArtifactLocation,
    ArtifactProvenance,
)


def required_setting(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Falta la variable obligatoria {name}")
    return value


async def store_and_verify(
    store: AzureBlobArtifactStore,
    artifact: Artifact,
) -> tuple[dict[str, Any], ArtifactLocation]:
    location = await store.store(artifact)
    restored = await store.retrieve(location)
    content_matches = restored.content == artifact.content
    result = {
        "container": location.container,
        "blob_name": location.blob_name,
        "match_id": location.match_id,
        "kind": location.kind.value,
        "origin": location.origin,
        "provenance": location.provenance.value,
        "bytes": len(restored.content),
        "sha256": sha256(restored.content).hexdigest(),
        "content_matches": content_matches,
    }
    if not content_matches:
        raise RuntimeError(
            f"El contenido recuperado de {location.container} no coincide"
        )
    return result, location


async def main() -> None:
    account_url = required_setting("AZURE_BLOB_SERVICE_ENDPOINT")
    match_id = f"synthetic-storage-{uuid4()}"
    match = generate_acceptance_match(match_id=match_id)
    match_content = json.dumps(
        {
            "metadata": match.metadata.model_dump(mode="json"),
            "events": [event.model_dump(mode="json") for event in match.events],
        },
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    match_artifact = Artifact(
        artifact_id=f"match-{uuid4()}.json",
        match_id=match_id,
        kind=ArtifactKind.SYNTHETIC_MATCH,
        provenance=ArtifactProvenance.SYNTHETIC,
        origin="dv-us-16-smoke",
        content_type="application/json",
        content=match_content,
    )
    observation_content = json.dumps(
        {
            "match_id": match_id,
            "source": "dv-us-16-smoke",
            "synthetic": True,
            "observations": [
                {
                    "class_name": "ball",
                    "video_time_ms": 1000,
                    "confidence": 0.91,
                    "track_id": "track-ball-001",
                }
            ],
        },
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    observation_artifact = Artifact(
        artifact_id=f"observation-{uuid4()}.json",
        match_id=match_id,
        kind=ArtifactKind.OBSERVATION,
        provenance=ArtifactProvenance.EXPERIMENTAL,
        origin="dv-us-16-smoke",
        content_type="application/json",
        content=observation_content,
    )
    store = AzureBlobArtifactStore.from_default_credential(account_url=account_url)

    try:
        match_result, _ = await store_and_verify(store, match_artifact)
        observation_result, observation_location = await store_and_verify(
            store,
            observation_artifact,
        )

        duplicate_rejected = False
        duplicate_error_type = None
        try:
            await store.store(observation_artifact)
        except ResourceExistsError as error:
            duplicate_rejected = True
            duplicate_error_type = type(error).__name__

        restored_after_collision = await store.retrieve(observation_location)
        original_preserved = (
            restored_after_collision.content == observation_artifact.content
        )
        result = {
            "synthetic_match": match_result,
            "observation": observation_result,
            "duplicate_write": {
                "rejected": duplicate_rejected,
                "error_type": duplicate_error_type,
                "original_content_preserved": original_preserved,
            },
        }
        print(json.dumps(result, indent=2))
        if not duplicate_rejected:
            raise RuntimeError("Azure permitió sobrescribir la observación")
        if not original_preserved:
            raise RuntimeError("La colisión alteró la observación original")
    finally:
        await store.close()


if __name__ == "__main__":
    asyncio.run(main())
