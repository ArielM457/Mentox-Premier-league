"""Selección de salidas de Persona 2: memoria local o Azure.

``ANALYTICS_OUTPUT=memory`` funciona sin cuenta de Azure. ``azure`` publica en
el Event Hub ``match-insights`` y guarda los registros en el contenedor
``analytics``. Solo se configuran nombres y endpoints; la identidad la aporta
``DefaultAzureCredential``.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from match_intelligence.adapters.messaging.azure_event_hubs import ProducerClient
from match_intelligence.adapters.messaging.azure_insights import AzureEventHubInsightPublisher
from match_intelligence.adapters.messaging.insights_memory import InMemoryInsightPublisher
from match_intelligence.adapters.storage.analytics_files import InMemoryAnalyticsWriter
from match_intelligence.adapters.storage.azure_analytics import (
    ANALYTICS_CONTAINER,
    AnalyticsBlobService,
    AzureBlobAnalyticsWriter,
)

DEFAULT_INSIGHTS_HUB = "match-insights"


class AnalyticsOutput(StrEnum):
    MEMORY = "memory"
    AZURE = "azure"


class AnalyticsConfigurationError(ValueError):
    """Configuración ausente o incompatible con la salida elegida."""


@dataclass(frozen=True, slots=True)
class AnalyticsOutputSettings:
    output: AnalyticsOutput = AnalyticsOutput.MEMORY
    fully_qualified_namespace: str | None = None
    insights_eventhub_name: str = DEFAULT_INSIGHTS_HUB
    blob_service_endpoint: str | None = None
    analytics_container: str = ANALYTICS_CONTAINER

    @classmethod
    def from_mapping(cls, values: Mapping[str, str] = os.environ) -> "AnalyticsOutputSettings":
        raw = values.get("ANALYTICS_OUTPUT", AnalyticsOutput.MEMORY.value)
        try:
            output = AnalyticsOutput(raw)
        except ValueError as error:
            allowed = ", ".join(item.value for item in AnalyticsOutput)
            raise AnalyticsConfigurationError(f"ANALYTICS_OUTPUT debe ser uno de: {allowed}") from error
        settings = cls(
            output=output,
            fully_qualified_namespace=values.get("EVENT_HUB_FULLY_QUALIFIED_NAMESPACE"),
            insights_eventhub_name=values.get("INSIGHTS_EVENT_HUB_NAME", DEFAULT_INSIGHTS_HUB),
            blob_service_endpoint=values.get("AZURE_BLOB_SERVICE_ENDPOINT"),
            analytics_container=values.get("ANALYTICS_BLOB_CONTAINER", ANALYTICS_CONTAINER),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.output is AnalyticsOutput.MEMORY:
            return
        required = {
            "EVENT_HUB_FULLY_QUALIFIED_NAMESPACE": self.fully_qualified_namespace,
            "INSIGHTS_EVENT_HUB_NAME": self.insights_eventhub_name,
            "AZURE_BLOB_SERVICE_ENDPOINT": self.blob_service_endpoint,
            "ANALYTICS_BLOB_CONTAINER": self.analytics_container,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise AnalyticsConfigurationError("Faltan variables para azure: " + ", ".join(missing))


InsightPublisherAdapter = InMemoryInsightPublisher | AzureEventHubInsightPublisher
AnalyticsWriterAdapter = InMemoryAnalyticsWriter | AzureBlobAnalyticsWriter


def build_insight_publisher(
    settings: AnalyticsOutputSettings, *, azure_client: ProducerClient | None = None
) -> InsightPublisherAdapter:
    settings.validate()
    if settings.output is AnalyticsOutput.MEMORY:
        return InMemoryInsightPublisher()
    if azure_client is not None:
        return AzureEventHubInsightPublisher(azure_client)
    assert settings.fully_qualified_namespace is not None
    return AzureEventHubInsightPublisher.from_default_credential(
        fully_qualified_namespace=settings.fully_qualified_namespace,
        eventhub_name=settings.insights_eventhub_name,
    )


def build_analytics_writer(
    settings: AnalyticsOutputSettings, *, azure_client: AnalyticsBlobService | None = None
) -> AnalyticsWriterAdapter:
    settings.validate()
    if settings.output is AnalyticsOutput.MEMORY:
        return InMemoryAnalyticsWriter()
    if azure_client is not None:
        return AzureBlobAnalyticsWriter(azure_client, container=settings.analytics_container)
    assert settings.blob_service_endpoint is not None
    return AzureBlobAnalyticsWriter.from_default_credential(
        account_url=settings.blob_service_endpoint, container=settings.analytics_container
    )
