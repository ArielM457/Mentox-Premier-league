"""Adaptadores Azure de Persona 2 con clientes simulados (sin red ni credenciales)."""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from azure.eventhub import EventData

from match_intelligence.adapters.messaging.azure_insights import (
    AzureEventHubInsightConsumer,
    AzureEventHubInsightPublisher,
    InsightPublicationError,
)
from match_intelligence.adapters.messaging.insights_configuration import (
    AnalyticsConfigurationError,
    AnalyticsOutput,
    AnalyticsOutputSettings,
    build_analytics_writer,
    build_insight_publisher,
)
from match_intelligence.adapters.messaging.insights_memory import InMemoryInsightPublisher
from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.adapters.storage.analytics_files import InMemoryAnalyticsWriter
from match_intelligence.adapters.storage.azure_analytics import (
    AzureBlobAnalyticsWriter,
    AzureBlobMatchMetadataProvider,
)
from match_intelligence.application.analytics.stream import (
    AnalyticsEnvelope,
    AnalyticsMessageType,
)

UTC = timezone.utc
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class SequenceClock:
    def __init__(self, *values: datetime) -> None:
        self._values = iter(values)

    def __call__(self) -> datetime:
        return next(self._values)


class RecordingProducer:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.batches: list[list[EventData]] = []
        self.partition_keys: list[str | None] = []
        self.closed = False

    async def send_batch(self, event_data_batch, *, partition_key=None) -> None:
        self.batches.append(event_data_batch)
        self.partition_keys.append(partition_key)
        if self.error is not None:
            raise self.error

    async def close(self) -> None:
        self.closed = True


def _envelope(message_type=AnalyticsMessageType.CANDIDATE_PROPOSED) -> AnalyticsEnvelope:
    return AnalyticsEnvelope(
        message_id="msg-1",
        message_type=message_type,
        produced_at=datetime(2026, 10, 9, 18, 0, tzinfo=UTC),
        producer="match-analytics",
        correlation_id="demo-001",
        source_event_id="evt-010",
        payload={"candidate_id": "moment-evt-010", "priority": 95},
    )


def test_insight_publisher_partitions_by_match_and_labels_the_message_type() -> None:
    producer = RecordingProducer()
    start = datetime(2026, 10, 9, 18, 0, tzinfo=UTC)
    publisher = AzureEventHubInsightPublisher(
        producer, clock=SequenceClock(start, start + timedelta(milliseconds=12))
    )

    asyncio.run(publisher.publish(_envelope()))

    data = producer.batches[0][0]
    assert producer.partition_keys == ["demo-001"]
    assert data.properties["message_type"] == "insight_candidate.proposed"
    assert AnalyticsEnvelope.model_validate_json(data.body_as_str()) == _envelope()
    assert publisher.receipts[0].duration_ms == pytest.approx(12)


def test_insight_publication_failure_is_recorded_and_raised() -> None:
    publisher = AzureEventHubInsightPublisher(RecordingProducer(error=RuntimeError("sin red")))

    with pytest.raises(InsightPublicationError):
        asyncio.run(publisher.publish(_envelope()))

    assert publisher.failures[0].error_type == "RuntimeError"
    assert publisher.receipts == ()


def test_insight_consumer_validates_envelopes_and_measures_transport() -> None:
    received_at = datetime(2026, 10, 9, 18, 0, 0, 40_000, tzinfo=UTC)
    consumer = AzureEventHubInsightConsumer(object(), clock=lambda: received_at)  # type: ignore[arg-type]

    ok = consumer.consume_message(EventData(_envelope().model_dump_json()))
    bad = consumer.consume_message(EventData('{"message_version": "1"}'))

    assert ok is not None and ok.transport_latency_ms == pytest.approx(40)
    assert bad is None and len(consumer.rejected) == 1


class RecordingBlob:
    def __init__(self, store: dict, name: str) -> None:
        self.store = store
        self.name = name

    async def upload_blob(self, data, **kwargs) -> None:
        if not kwargs.get("overwrite") and self.name in self.store:
            raise RuntimeError("ya existe")
        self.store[self.name] = (data, kwargs)

    async def download_blob(self):
        content = self.store[self.name][0]

        class Downloader:
            async def readall(self_inner):
                return content

        return Downloader()


class RecordingContainer:
    def __init__(self, store: dict, container: str) -> None:
        self.store = store
        self.container = container

    def list_blobs(self, *, name_starts_with=None):
        names = [
            name.split("/", 1)[1] for name in sorted(self.store)
            if name.startswith(f"{self.container}/") and name.split("/", 1)[1].startswith(name_starts_with or "")
        ]

        class Item:
            def __init__(self, name: str) -> None:
                self.name = name

        async def iterate():
            for name in names:
                yield Item(name)

        return iterate()

    def get_blob_client(self, blob: str) -> RecordingBlob:
        return RecordingBlob(self.store, f"{self.container}/{blob}")


class RecordingBlobService:
    def __init__(self) -> None:
        self.store: dict[str, tuple[bytes, dict]] = {}
        self.closed = False

    def get_blob_client(self, *, container: str, blob: str) -> RecordingBlob:
        return RecordingBlob(self.store, f"{container}/{blob}")

    def get_container_client(self, container: str) -> RecordingContainer:
        return RecordingContainer(self.store, container)

    async def close(self) -> None:
        self.closed = True


def test_blob_writer_stores_runs_without_overwriting_and_with_hash_metadata() -> None:
    service = RecordingBlobService()
    writer = AzureBlobAnalyticsWriter(service)

    location = asyncio.run(writer.write(
        match_id="demo-001", run_id="run-1", name="run.json", content=b"{}", content_type="application/json",
    ))

    assert location == "analytics/demo-001/run-1/run.json"
    content, kwargs = service.store[location]
    assert kwargs["overwrite"] is False
    assert kwargs["metadata"]["match_id"] == "demo-001"
    assert len(kwargs["metadata"]["content_sha256"]) == 64
    with pytest.raises(RuntimeError):
        asyncio.run(writer.write(
            match_id="demo-001", run_id="run-1", name="run.json", content=b"{}", content_type="application/json",
        ))
    with pytest.raises(ValueError):
        asyncio.run(writer.write(
            match_id="../x", run_id="run-1", name="a.json", content=b"{}", content_type="application/json",
        ))


def test_metadata_provider_reads_matches_stored_by_persona_1() -> None:
    match = generate_acceptance_match()
    service = RecordingBlobService()
    document = {"metadata": match.metadata.model_dump(mode="json"), "events": []}
    service.store[f"matches/{match.metadata.match_id}/broken.json"] = (b"no es json", {})
    service.store[f"matches/{match.metadata.match_id}/match.json"] = (json.dumps(document).encode(), {})
    provider = AzureBlobMatchMetadataProvider(service)

    assert asyncio.run(provider.get(match.metadata.match_id)) == match.metadata
    assert asyncio.run(provider.get("otro-partido")) is None


def test_output_configuration_selects_memory_or_azure() -> None:
    memory = AnalyticsOutputSettings.from_mapping({})
    assert memory.output is AnalyticsOutput.MEMORY
    assert isinstance(build_insight_publisher(memory), InMemoryInsightPublisher)
    assert isinstance(build_analytics_writer(memory), InMemoryAnalyticsWriter)

    azure = AnalyticsOutputSettings.from_mapping({
        "ANALYTICS_OUTPUT": "azure",
        "EVENT_HUB_FULLY_QUALIFIED_NAMESPACE": "ns.servicebus.windows.net",
        "AZURE_BLOB_SERVICE_ENDPOINT": "https://cuenta.blob.core.windows.net",
    })
    assert azure.insights_eventhub_name == "match-insights"
    assert azure.analytics_container == "analytics"
    assert isinstance(build_insight_publisher(azure, azure_client=RecordingProducer()), AzureEventHubInsightPublisher)
    assert isinstance(build_analytics_writer(azure, azure_client=RecordingBlobService()), AzureBlobAnalyticsWriter)


def test_output_configuration_reports_missing_azure_settings() -> None:
    with pytest.raises(AnalyticsConfigurationError, match="EVENT_HUB_FULLY_QUALIFIED_NAMESPACE"):
        AnalyticsOutputSettings.from_mapping({"ANALYTICS_OUTPUT": "azure"})
    with pytest.raises(AnalyticsConfigurationError, match="ANALYTICS_OUTPUT"):
        AnalyticsOutputSettings.from_mapping({"ANALYTICS_OUTPUT": "kafka"})


def test_analytics_bicep_adds_insights_hub_and_containers_without_touching_main() -> None:
    template = (REPOSITORY_ROOT / "infra" / "azure" / "analytics.bicep").read_text(encoding="utf-8")
    example = REPOSITORY_ROOT / "infra" / "azure" / "analytics.bicepparam.example"

    assert example.is_file()
    assert template.count("existing = {") == 3  # namespace, cuenta y servicio de blobs existentes
    assert "name: 'match-insights'" in template
    assert template.count("namespaces/eventhubs/consumerGroups@2024-01-01") == 3
    for name in ("narrative", "experience", "diagnostics", "analytics", "models"):
        assert f"name: '{name}'" in template
    assert template.count("publicAccess: 'None'") == 2
    for forbidden in ("listKeys", "connectionString", "AccountKey", "SharedAccessKey"):
        assert forbidden not in template
