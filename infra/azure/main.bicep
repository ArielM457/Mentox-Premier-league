targetScope = 'resourceGroup'

@description('Prefijo corto, en minúsculas, para distinguir el despliegue de cada integrante.')
@minLength(3)
@maxLength(9)
param projectPrefix string

@description('Entorno lógico usado en nombres y etiquetas.')
@allowed([
  'dev'
  'test'
  'demo'
])
param environmentName string = 'dev'

@description('Región de los recursos. De forma predeterminada usa la región del grupo.')
param location string = resourceGroup().location

var normalizedPrefix = toLower(replace(projectPrefix, '-', ''))
var resourceSuffix = uniqueString(subscription().id, resourceGroup().id, projectPrefix)
var eventHubNamespaceName = 'eh-${toLower(projectPrefix)}-${environmentName}-${resourceSuffix}'
var eventHubName = 'match-events'
var visionEventHubName = 'vision-observations'
var storageAccountName = 'st${normalizedPrefix}${resourceSuffix}'
var commonTags = {
  project: 'mentox-premier-league'
  environment: environmentName
  managedBy: 'bicep'
  workload: 'data-vision'
}

resource eventHubNamespace 'Microsoft.EventHub/namespaces@2024-01-01' = {
  name: eventHubNamespaceName
  location: location
  tags: commonTags
  sku: {
    name: 'Standard'
    tier: 'Standard'
    capacity: 1
  }
  properties: {
    disableLocalAuth: true
    isAutoInflateEnabled: false
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    zoneRedundant: false
  }
}

resource matchEventsHub 'Microsoft.EventHub/namespaces/eventhubs@2024-01-01' = {
  name: eventHubName
  parent: eventHubNamespace
  properties: {
    messageRetentionInDays: 1
    partitionCount: 2
    status: 'Active'
  }
}

resource backendConsumerGroup 'Microsoft.EventHub/namespaces/eventhubs/consumerGroups@2024-01-01' = {
  name: 'backend'
  parent: matchEventsHub
  properties: {
    userMetadata: 'Consumidor del estado y la analítica del partido.'
  }
}

resource diagnosticsConsumerGroup 'Microsoft.EventHub/namespaces/eventhubs/consumerGroups@2024-01-01' = {
  name: 'diagnostics'
  parent: matchEventsHub
  properties: {
    userMetadata: 'Consumidor aislado para pruebas y diagnóstico.'
  }
}

resource visionObservationsHub 'Microsoft.EventHub/namespaces/eventhubs@2024-01-01' = {
  name: visionEventHubName
  parent: eventHubNamespace
  properties: {
    messageRetentionInDays: 1
    partitionCount: 2
    status: 'Active'
  }
}

resource visionBackendConsumerGroup 'Microsoft.EventHub/namespaces/eventhubs/consumerGroups@2024-01-01' = {
  name: 'backend'
  parent: visionObservationsHub
  properties: {
    userMetadata: 'Consume observaciones visuales para validación, fusión y entrega en vivo.'
  }
}

resource visionDiagnosticsConsumerGroup 'Microsoft.EventHub/namespaces/eventhubs/consumerGroups@2024-01-01' = {
  name: 'diagnostics'
  parent: visionObservationsHub
  properties: {
    userMetadata: 'Pruebas aisladas del canal de observaciones visuales.'
  }
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2025-06-01' = {
  name: storageAccountName
  location: location
  tags: commonTags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Enabled'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2025-06-01' = {
  name: 'default'
  parent: storageAccount
  properties: {}
}

resource matchesContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  name: 'matches'
  parent: blobService
  properties: {
    metadata: {
      purpose: 'synthetic-matches'
    }
    publicAccess: 'None'
  }
}

resource authorizedVideosContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  name: 'authorized-videos'
  parent: blobService
  properties: {
    metadata: {
      purpose: 'authorized-video-only'
    }
    publicAccess: 'None'
  }
}

resource observationsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  name: 'observations'
  parent: blobService
  properties: {
    metadata: {
      purpose: 'experimental-observations'
    }
    publicAccess: 'None'
  }
}

output eventHubNamespaceName string = eventHubNamespace.name
output eventHubFullyQualifiedNamespace string = '${eventHubNamespace.name}.servicebus.windows.net'
output eventHubName string = matchEventsHub.name
output visionEventHubName string = visionObservationsHub.name
output eventHubEndpoint string = eventHubNamespace.properties.serviceBusEndpoint
output backendConsumerGroupName string = backendConsumerGroup.name
output diagnosticsConsumerGroupName string = diagnosticsConsumerGroup.name
output visionBackendConsumerGroupName string = visionBackendConsumerGroup.name
output visionDiagnosticsConsumerGroupName string = visionDiagnosticsConsumerGroup.name
output storageAccountName string = storageAccount.name
output blobServiceEndpoint string = storageAccount.properties.primaryEndpoints.blob
output containerNames array = [
  matchesContainer.name
  authorizedVideosContainer.name
  observationsContainer.name
]
