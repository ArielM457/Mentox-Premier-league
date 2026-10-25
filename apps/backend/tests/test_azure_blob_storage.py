import asyncio
from types import SimpleNamespace

import pytest

from match_intelligence.adapters.storage.azure_blob import (
    ArtifactIntegrityError,
    AzureBlobArtifactStore,
)
from match_intelligence.application.artifacts import (
    Artifact,
    ArtifactKind,
    ArtifactProvenance,
    ArtifactValidationError,
)


class MemoryDownloader:
    def __init__(self, content: bytes) -> None:
        self._content = content

    async def readall(self) -> bytes:
        return self._content


class MemoryBlobClient:
    def __init__(self) -> None:
        self.content: bytes | None = None
        self.metadata: dict[str, str] = {}
        self.content_type: str | None = None
        self.upload_kwargs: dict[str, object] = {}

    async def upload_blob(self, data: bytes, **kwargs: object) -> None:
        if self.content is not None and kwargs.get("overwrite") is False:
            raise FileExistsError("blob already exists")
        self.content = data
        self.metadata = dict(kwargs["metadata"])  # type: ignore[arg-type]
        settings = kwargs["content_settings"]
        self.content_type = settings.content_type  # type: ignore[union-attr]
        self.upload_kwargs = kwargs

    async def download_blob(self) -> MemoryDownloader:
        if self.content is None:
            raise FileNotFoundError
        return MemoryDownloader(self.content)

    async def get_blob_properties(self) -> SimpleNamespace:
        return SimpleNamespace(
            metadata=self.metadata,
            content_settings=SimpleNamespace(content_type=self.content_type),
        )


class MemoryBlobService:
    def __init__(self) -> None:
        self.blobs: dict[tuple[str, str], MemoryBlobClient] = {}
        self.closed = False

    def get_blob_client(self, *, container: str, blob: str) -> MemoryBlobClient:
        return self.blobs.setdefault((container, blob), MemoryBlobClient())

    async def close(self) -> None:
        self.closed = True


class MemoryCredential:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def artifact(kind: ArtifactKind) -> Artifact:
    provenance = {
        ArtifactKind.SYNTHETIC_MATCH: ArtifactProvenance.SYNTHETIC,
        ArtifactKind.AUTHORIZED_VIDEO: ArtifactProvenance.AUTHORIZED,
        ArtifactKind.OBSERVATION: ArtifactProvenance.EXPERIMENTAL,
    }[kind]
    return Artifact(
        artifact_id=f"sample-{kind.value}",
        match_id="synthetic-acceptance-001",
        kind=kind,
        provenance=provenance,
        origin="dv-us-09-test",
        content_type="application/json",
        content=f'{{"fixture":"{kind.value}","synthetic":true}}'.encode(),
    )


@pytest.mark.parametrize(
    ("kind", "expected_container"),
    [
        (ArtifactKind.SYNTHETIC_MATCH, "matches"),
        (ArtifactKind.AUTHORIZED_VIDEO, "authorized-videos"),
        (ArtifactKind.OBSERVATION, "observations"),
    ],
)
def test_each_artifact_kind_uses_its_defined_container(
    kind: ArtifactKind, expected_container: str
) -> None:
    async def scenario() -> None:
        client = MemoryBlobService()
        store = AzureBlobArtifactStore(client)

        location = await store.store(artifact(kind))

        assert location.container == expected_container
        assert (expected_container, location.blob_name) in client.blobs

    asyncio.run(scenario())


def test_blob_name_and_metadata_preserve_match_and_origin() -> None:
    async def scenario() -> None:
        client = MemoryBlobService()
        store = AzureBlobArtifactStore(client)
        sample = artifact(ArtifactKind.SYNTHETIC_MATCH)

        location = await store.store(sample)
        recorded = client.blobs[(location.container, location.blob_name)]

        assert location.blob_name == f"{sample.match_id}/{sample.artifact_id}"
        assert recorded.metadata["match_id"] == sample.match_id
        assert recorded.metadata["origin"] == sample.origin
        assert recorded.metadata["provenance"] == "synthetic"
        assert recorded.metadata["content_sha256"] == sample.content_sha256
        assert recorded.upload_kwargs["overwrite"] is False

    asyncio.run(scenario())


def test_store_rejects_overwriting_an_existing_artifact() -> None:
    async def scenario() -> None:
        client = MemoryBlobService()
        store = AzureBlobArtifactStore(client)
        sample = artifact(ArtifactKind.OBSERVATION)

        location = await store.store(sample)

        with pytest.raises(FileExistsError, match="already exists"):
            await store.store(sample)

        restored = await store.retrieve(location)
        assert restored.content == sample.content

    asyncio.run(scenario())


def test_retrieve_returns_the_exact_same_content() -> None:
    async def scenario() -> None:
        client = MemoryBlobService()
        store = AzureBlobArtifactStore(client)
        sample = artifact(ArtifactKind.OBSERVATION)

        location = await store.store(sample)
        restored = await store.retrieve(location)

        assert restored.content == sample.content
        assert restored.location == location

    asyncio.run(scenario())


def test_retrieve_detects_content_tampering() -> None:
    async def scenario() -> None:
        client = MemoryBlobService()
        store = AzureBlobArtifactStore(client)
        location = await store.store(artifact(ArtifactKind.SYNTHETIC_MATCH))
        client.blobs[(location.container, location.blob_name)].content = b"changed"

        with pytest.raises(ArtifactIntegrityError, match="content_sha256"):
            await store.retrieve(location)

    asyncio.run(scenario())


def test_video_requires_explicit_authorized_provenance() -> None:
    with pytest.raises(ArtifactValidationError, match="authorized"):
        Artifact(
            artifact_id="video-001",
            match_id="synthetic-acceptance-001",
            kind=ArtifactKind.AUTHORIZED_VIDEO,
            provenance=ArtifactProvenance.SYNTHETIC,
            origin="unknown-upload",
            content_type="video/mp4",
            content=b"synthetic-placeholder",
        )


@pytest.mark.parametrize("unsafe_id", ["../escape", "match/other", "", " white"])
def test_identifiers_cannot_escape_the_match_prefix(unsafe_id: str) -> None:
    with pytest.raises(ArtifactValidationError):
        Artifact(
            artifact_id=unsafe_id,
            match_id="synthetic-acceptance-001",
            kind=ArtifactKind.OBSERVATION,
            provenance=ArtifactProvenance.EXPERIMENTAL,
            origin="manual-review",
            content_type="application/json",
            content=b"{}",
        )


def test_close_releases_client_and_credential() -> None:
    async def scenario() -> None:
        client = MemoryBlobService()
        credential = MemoryCredential()
        store = AzureBlobArtifactStore(client, credential=credential)

        await store.close()

        assert client.closed
        assert credential.closed

    asyncio.run(scenario())


def test_delivered_fixtures_are_explicitly_synthetic() -> None:
    sample = artifact(ArtifactKind.SYNTHETIC_MATCH)

    assert sample.provenance is ArtifactProvenance.SYNTHETIC
    assert b'"synthetic":true' in sample.content
    assert b"Premier League" not in sample.content
