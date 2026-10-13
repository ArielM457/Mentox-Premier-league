"""Carga de modelos validados desde una carpeta local o desde Azure Blob Storage.

Cada modelo es un documento JSON (``xt.json``, ``xg.json``) con procedencia,
licencia, datos de entrenamiento y validación. En Azure se guardan en el
contenedor ``models`` como ``<nombre>/current.json``. Si un documento falta o
no supera la validación, el registro lo marca desactivado con el motivo.
"""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from azure.core.exceptions import ResourceNotFoundError
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient

from match_intelligence.application.analytics.value_models import (
    ActionValueModel,
    ValueModelRegistry,
)

from .expected_goals import LogisticExpectedGoalsModel
from .expected_threat import ExpectedThreatModel
from .vaep import VaepFeasibilityModel

MODELS_CONTAINER = "models"


def registry_from_documents(documents: Mapping[str, Mapping[str, Any] | None]) -> ValueModelRegistry:
    models: list[ActionValueModel] = [VaepFeasibilityModel()]
    if documents.get("xt") is not None:
        models.append(ExpectedThreatModel.from_document(documents["xt"]))  # type: ignore[arg-type]
    if documents.get("xg") is not None:
        models.append(LogisticExpectedGoalsModel.from_document(documents["xg"]))  # type: ignore[arg-type]
    return ValueModelRegistry(models)


def registry_from_directory(directory: Path) -> ValueModelRegistry:
    documents: dict[str, Mapping[str, Any] | None] = {}
    for name in ("xt", "xg"):
        path = directory / f"{name}.json"
        documents[name] = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    return registry_from_documents(documents)


async def registry_from_blob(
    account_url: str, *, container: str = MODELS_CONTAINER
) -> ValueModelRegistry:
    credential = DefaultAzureCredential()
    client = BlobServiceClient(account_url=account_url, credential=credential)
    documents: dict[str, Mapping[str, Any] | None] = {}
    try:
        for name in ("xt", "xg"):
            blob = client.get_blob_client(container=container, blob=f"{name}/current.json")
            try:
                downloader = await blob.download_blob()
                documents[name] = json.loads(await downloader.readall())
            except ResourceNotFoundError:
                documents[name] = None
    finally:
        await client.close()
        await credential.close()
    return registry_from_documents(documents)
