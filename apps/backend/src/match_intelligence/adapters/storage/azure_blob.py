from typing import Any, Protocol

from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob import ContentSettings
from azure.storage.blob.aio import BlobServiceClient

from match_intelligence.application.artifacts import (
    Artifact,
    ArtifactLocation,
    RetrievedArtifact,
)


class AsyncCredential(Protocol):
    async def close(self) -> None: ...


class BlobClient(Protocol):
    async def upload_blob(self, data: bytes, **kwargs: Any) -> Any: ...

    async def download_blob(self) -> Any: ...

    async def get_blob_properties(self) -> Any: ...


class BlobService(Protocol):
    def get_blob_client(self, *, container: str, blob: str) -> BlobClient: ...

    async def close(self) -> None: ...


class ArtifactIntegrityError(RuntimeError):
    """El contenido o los metadatos recuperados no coinciden con la referencia."""


class AzureBlobArtifactStore:
    """Guarda artefactos trazables en los contenedores privados de DV-US-09."""

    def __init__(
        self,
        client: BlobService,
        *,
        credential: AsyncCredential | None = None,
    ) -> None:
        self._client = client
        self._credential = credential

    @classmethod
    def from_default_credential(cls, *, account_url: str) -> "AzureBlobArtifactStore":
        credential = DefaultAzureCredential()
        client = BlobServiceClient(account_url=account_url, credential=credential)
        return cls(client, credential=credential)

    async def store(self, artifact: Artifact) -> ArtifactLocation:
        location = ArtifactLocation(
            container=artifact.container,
            blob_name=artifact.blob_name,
            artifact_id=artifact.artifact_id,
            match_id=artifact.match_id,
            kind=artifact.kind,
            provenance=artifact.provenance,
            origin=artifact.origin,
            content_type=artifact.content_type,
            content_sha256=artifact.content_sha256,
        )
        blob = self._client.get_blob_client(
            container=location.container,
            blob=location.blob_name,
        )
        await blob.upload_blob(
            artifact.content,
            overwrite=False,
            metadata=self._metadata(location),
            content_settings=ContentSettings(content_type=artifact.content_type),
        )
        return location

    async def retrieve(self, location: ArtifactLocation) -> RetrievedArtifact:
        blob = self._client.get_blob_client(
            container=location.container,
            blob=location.blob_name,
        )
        properties = await blob.get_blob_properties()
        downloader = await blob.download_blob()
        content = await downloader.readall()

        expected_metadata = self._metadata(location)
        actual_metadata = dict(properties.metadata or {})
        mismatches = [
            key
            for key, expected_value in expected_metadata.items()
            if actual_metadata.get(key) != expected_value
        ]
        actual_content_type = properties.content_settings.content_type
        if actual_content_type != location.content_type:
            mismatches.append("content_type")
        if Artifact(
            artifact_id=location.artifact_id,
            match_id=location.match_id,
            kind=location.kind,
            provenance=location.provenance,
            origin=location.origin,
            content_type=location.content_type,
            content=content,
        ).content_sha256 != location.content_sha256:
            mismatches.append("content_sha256")

        if mismatches:
            raise ArtifactIntegrityError(
                "El artefacto recuperado no coincide en: " + ", ".join(mismatches)
            )
        return RetrievedArtifact(location=location, content=content)

    async def close(self) -> None:
        try:
            await self._client.close()
        finally:
            if self._credential is not None:
                await self._credential.close()

    @staticmethod
    def _metadata(location: ArtifactLocation) -> dict[str, str]:
        return {
            "artifact_id": location.artifact_id,
            "match_id": location.match_id,
            "kind": location.kind.value,
            "provenance": location.provenance.value,
            "origin": location.origin,
            "content_sha256": location.content_sha256,
        }
