"""Persistencia de Persona 2 en Azure Blob Storage.

* ``analytics``: registros de cada ejecución (snapshot final, momentos,
  decisiones de atención, revisiones y manifiesto con hashes).
* ``matches``: lectura de los partidos sintéticos guardados por Persona 1
  (``{"metadata": ..., "events": [...]}``) para obtener sus metadatos.

Usa ``DefaultAzureCredential`` y nunca sobrescribe un registro existente.
"""

import json
import re
from hashlib import sha256
from typing import Any, Protocol

from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob import ContentSettings
from azure.storage.blob.aio import BlobServiceClient

from match_intelligence.adapters.storage.azure_blob import AsyncCredential, BlobClient
from match_intelligence.domain.analytics.models import ENGINE_VERSION
from match_intelligence.domain.contracts import MatchMetadata

ANALYTICS_CONTAINER = "analytics"
MATCHES_CONTAINER = "matches"
_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class ContainerClient(Protocol):
    def list_blobs(self, *, name_starts_with: str | None = None) -> Any: ...

    def get_blob_client(self, blob: str) -> BlobClient: ...


class AnalyticsBlobService(Protocol):
    def get_blob_client(self, *, container: str, blob: str) -> BlobClient: ...

    def get_container_client(self, container: str) -> ContainerClient: ...

    async def close(self) -> None: ...


def _check_segment(name: str, value: str) -> None:
    if not _SAFE_SEGMENT.fullmatch(value):
        raise ValueError(f"{name} debe ser un identificador seguro de 1 a 128 caracteres")


class AzureBlobAnalyticsWriter:
    def __init__(
        self,
        client: AnalyticsBlobService,
        *,
        container: str = ANALYTICS_CONTAINER,
        credential: AsyncCredential | None = None,
    ) -> None:
        self._client = client
        self._container = container
        self._credential = credential

    @classmethod
    def from_default_credential(
        cls, *, account_url: str, container: str = ANALYTICS_CONTAINER
    ) -> "AzureBlobAnalyticsWriter":
        credential = DefaultAzureCredential()
        client = BlobServiceClient(account_url=account_url, credential=credential)
        return cls(client, container=container, credential=credential)

    async def write(
        self, *, match_id: str, run_id: str, name: str, content: bytes, content_type: str
    ) -> str:
        for field_name, value in (("match_id", match_id), ("run_id", run_id), ("name", name)):
            _check_segment(field_name, value)
        blob_name = f"{match_id}/{run_id}/{name}"
        blob = self._client.get_blob_client(container=self._container, blob=blob_name)
        await blob.upload_blob(
            content,
            overwrite=False,
            metadata={
                "match_id": match_id,
                "run_id": run_id,
                "engine_version": ENGINE_VERSION.replace("@", "-"),
                "content_sha256": sha256(content).hexdigest(),
            },
            content_settings=ContentSettings(content_type=content_type),
        )
        return f"{self._container}/{blob_name}"

    async def close(self) -> None:
        try:
            await self._client.close()
        finally:
            if self._credential is not None:
                await self._credential.close()


class AzureBlobMatchMetadataProvider:
    """Busca el primer JSON con metadatos bajo ``matches/<match_id>/``."""

    def __init__(
        self,
        client: AnalyticsBlobService,
        *,
        container: str = MATCHES_CONTAINER,
        credential: AsyncCredential | None = None,
    ) -> None:
        self._client = client
        self._container = container
        self._credential = credential
        self._cache: dict[str, MatchMetadata] = {}

    @classmethod
    def from_default_credential(
        cls, *, account_url: str, container: str = MATCHES_CONTAINER
    ) -> "AzureBlobMatchMetadataProvider":
        credential = DefaultAzureCredential()
        client = BlobServiceClient(account_url=account_url, credential=credential)
        return cls(client, container=container, credential=credential)

    async def get(self, match_id: str) -> MatchMetadata | None:
        if match_id in self._cache:
            return self._cache[match_id]
        container = self._client.get_container_client(self._container)
        async for item in container.list_blobs(name_starts_with=f"{match_id}/"):
            downloader = await container.get_blob_client(item.name).download_blob()
            try:
                document = json.loads(await downloader.readall())
                metadata = MatchMetadata.model_validate(document["metadata"])
            except (ValueError, KeyError, TypeError):
                continue
            if metadata.match_id == match_id:
                self._cache[match_id] = metadata
                return metadata
        return None

    async def close(self) -> None:
        try:
            await self._client.close()
        finally:
            if self._credential is not None:
                await self._credential.close()
