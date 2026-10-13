// Recursos de Persona 2 (estado y analítica) sobre el despliegue de main.bicep.
// Reutiliza el namespace de Event Hubs y la cuenta de Storage existentes; no los modifica.
targetScope = 'resourceGroup'

@description('Salida eventHubNamespaceName del despliegue de main.bicep.')
param eventHubNamespaceName string

@description('Salida storageAccountName del despliegue de main.bicep.')
param storageAccountName string

@description('Días de retención de las salidas analíticas.')
@minValue(1)
@maxValue(7)
param insightsRetentionDays int = 1

resource eventHubNamespace 'Microsoft.EventHub/namespaces@2024-01-01' existing = {
  name: eventHubNamespaceName
}

resource matchInsightsHub 'Microsoft.EventHub/namespaces/eventhubs@2024-01-01' = {
  name: 'match-insights'
  parent: eventHubNamespace
  properties: {
    messageRetentionInDays: insightsRetentionDays
    partitionCount: 2
    status: 'Active'
  }
}

resource narrativeConsumerGroup 'Microsoft.EventHub/namespaces/eventhubs/consumerGroups@2024-01-01' = {
  name: 'narrative'
  parent: matchInsightsHub
  properties: {
    userMetadata: 'Agentes de narración (Persona 3).'
  }
}

resource experienceConsumerGroup 'Microsoft.EventHub/namespaces/eventhubs/consumerGroups@2024-01-01' = {
  name: 'experience'
  parent: matchInsightsHub
  properties: {
    userMetadata: 'API y experiencia en directo (Persona 4).'
  }
}

resource insightsDiagnosticsConsumerGroup 'Microsoft.EventHub/namespaces/eventhubs/consumerGroups@2024-01-01' = {
  name: 'diagnostics'
  parent: matchInsightsHub
  properties: {
    userMetadata: 'Pruebas de humo y diagnóstico de la analítica.'
  }
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2025-06-01' existing = {
  name: storageAccountName
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2025-06-01' existing = {
  name: 'default'
  parent: storageAccount
}

resource analyticsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  name: 'analytics'
  parent: blobService
  properties: {
    metadata: {
      purpose: 'analytics-runs'
    }
    publicAccess: 'None'
  }
}

resource modelsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  name: 'models'
  parent: blobService
  properties: {
    metadata: {
      purpose: 'validated-value-models'
    }
    publicAccess: 'None'
  }
}

output insightsEventHubName string = matchInsightsHub.name
output insightsConsumerGroups array = [
  narrativeConsumerGroup.name
  experienceConsumerGroup.name
  insightsDiagnosticsConsumerGroup.name
]
output analyticsContainerName string = analyticsContainer.name
output modelsContainerName string = modelsContainer.name
