from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
AZURE_DIRECTORY = REPOSITORY_ROOT / "infra" / "azure"
TEMPLATE = AZURE_DIRECTORY / "main.bicep"
PARAMETERS = AZURE_DIRECTORY / "dev.bicepparam.example"
DOCUMENTATION = AZURE_DIRECTORY / "README.md"


def _template_text() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def test_azure_infrastructure_files_are_present() -> None:
    assert TEMPLATE.is_file()
    assert PARAMETERS.is_file()
    assert DOCUMENTATION.is_file()


def test_template_declares_required_event_hubs_resources() -> None:
    template = _template_text()

    assert "Microsoft.EventHub/namespaces@2024-01-01" in template
    assert "Microsoft.EventHub/namespaces/eventhubs@2024-01-01" in template
    assert template.count("namespaces/eventhubs@2024-01-01") == 3
    assert template.count("namespaces/eventhubs/consumerGroups@2024-01-01") == 5
    assert "match-metrics" in template
    assert "vision-observations" in template
    assert "name: 'backend'" in template
    assert "name: 'diagnostics'" in template


def test_template_declares_private_storage_and_required_containers() -> None:
    template = _template_text()

    assert "Microsoft.Storage/storageAccounts@2025-06-01" in template
    assert template.count("blobServices/containers@2025-06-01") == 3
    assert "name: 'matches'" in template
    assert "name: 'authorized-videos'" in template
    assert "name: 'observations'" in template
    assert template.count("publicAccess: 'None'") == 3


def test_names_are_derived_from_prefix_and_deterministic_suffix() -> None:
    template = _template_text()

    assert "param projectPrefix string" in template
    assert "uniqueString(subscription().id, resourceGroup().id, projectPrefix)" in template
    assert "eventHubNamespaceName" in template
    assert "storageAccountName" in template
    assert "subscriptionId" not in PARAMETERS.read_text(encoding="utf-8")


def test_template_does_not_emit_or_enable_shared_secrets() -> None:
    template = _template_text()
    lowered = template.lower()

    assert "disableLocalAuth: true" in template
    assert "allowSharedKeyAccess: false" in template
    assert "listkeys" not in lowered
    assert "connectionstring" not in lowered
    assert "accountkey" not in lowered


def test_template_exposes_names_and_endpoints_without_secrets() -> None:
    template = _template_text()

    for output_name in (
        "eventHubNamespaceName",
        "eventHubFullyQualifiedNamespace",
        "eventHubName",
        "visionEventHubName",
        "eventHubEndpoint",
        "storageAccountName",
        "blobServiceEndpoint",
        "containerNames",
        "visionBackendConsumerGroupName",
    ):
        assert f"output {output_name}" in template


def test_documentation_requires_validate_what_if_and_explicit_subscription() -> None:
    documentation = DOCUMENTATION.read_text(encoding="utf-8")

    assert "az account set --subscription" in documentation
    assert "az deployment group validate" in documentation
    assert "az deployment group what-if" in documentation
    assert "az deployment group create" in documentation
    assert "az group delete" in documentation
