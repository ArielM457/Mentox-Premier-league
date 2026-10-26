targetScope = 'resourceGroup'

@description('Prefijo corto usado para conservar los nombres deterministas del entorno.')
@minLength(3)
@maxLength(9)
param projectPrefix string

@allowed([
  'dev'
  'test'
  'demo'
])
param environmentName string = 'dev'

param location string = resourceGroup().location

var resourceSuffix = uniqueString(subscription().id, resourceGroup().id, projectPrefix)
var eventHubNamespaceName = 'eh-${toLower(projectPrefix)}-${environmentName}-${resourceSuffix}'
var serviceBusNamespaceName = 'sb-${toLower(projectPrefix)}-${environmentName}-${resourceSuffix}'
var commonTags = {
  project: 'mentox-premier-league'
  product: 'the-prime-moment'
  environment: environmentName
  managedBy: 'bicep'
  workload: 'event-routing'
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

resource matchEvents 'Microsoft.EventHub/namespaces/eventhubs@2024-01-01' = {
  name: 'match-events'
  parent: eventHubNamespace
  properties: {
    messageRetentionInDays: 1
    partitionCount: 2
    status: 'Active'
  }
}

resource visionObservations 'Microsoft.EventHub/namespaces/eventhubs@2024-01-01' = {
  name: 'vision-observations'
  parent: eventHubNamespace
  properties: {
    messageRetentionInDays: 1
    partitionCount: 2
    status: 'Active'
  }
}

resource matchMetrics 'Microsoft.EventHub/namespaces/eventhubs@2024-01-01' = {
  name: 'match-metrics'
  parent: eventHubNamespace
  properties: {
    messageRetentionInDays: 1
    partitionCount: 2
    status: 'Active'
  }
}

resource matchBackend 'Microsoft.EventHub/namespaces/eventhubs/consumerGroups@2024-01-01' = {
  name: 'backend'
  parent: matchEvents
  properties: {
    userMetadata: 'Procesamiento principal de eventos confirmados.'
  }
}

resource matchDiagnostics 'Microsoft.EventHub/namespaces/eventhubs/consumerGroups@2024-01-01' = {
  name: 'diagnostics'
  parent: matchEvents
  properties: {
    userMetadata: 'Pruebas sin competir con el consumidor principal.'
  }
}

resource visionBackend 'Microsoft.EventHub/namespaces/eventhubs/consumerGroups@2024-01-01' = {
  name: 'backend'
  parent: visionObservations
  properties: {
    userMetadata: 'Validación y fusión de observaciones visuales.'
  }
}

resource visionDiagnostics 'Microsoft.EventHub/namespaces/eventhubs/consumerGroups@2024-01-01' = {
  name: 'diagnostics'
  parent: visionObservations
  properties: {
    userMetadata: 'Diagnóstico aislado de observaciones visuales.'
  }
}

resource metricsDiagnostics 'Microsoft.EventHub/namespaces/eventhubs/consumerGroups@2024-01-01' = {
  name: 'diagnostics'
  parent: matchMetrics
  properties: {
    userMetadata: 'Métricas reconstruibles y tolerantes a pérdida.'
  }
}

resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2024-01-01' = {
  name: serviceBusNamespaceName
  location: location
  tags: commonTags
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  properties: {
    disableLocalAuth: true
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    zoneRedundant: false
  }
}

resource importantEvents 'Microsoft.ServiceBus/namespaces/queues@2024-01-01' = {
  name: 'important-events'
  parent: serviceBusNamespace
  properties: {
    deadLetteringOnMessageExpiration: true
    defaultMessageTimeToLive: 'P1D'
    enableBatchedOperations: true
    lockDuration: 'PT1M'
    maxDeliveryCount: 10
    maxSizeInMegabytes: 1024
    requiresDuplicateDetection: false
    requiresSession: false
  }
}

output eventHubFullyQualifiedNamespace string = '${eventHubNamespace.name}.servicebus.windows.net'
output eventHubNamespaceName string = eventHubNamespace.name
output matchEventsName string = matchEvents.name
output visionObservationsName string = visionObservations.name
output matchMetricsName string = matchMetrics.name
output serviceBusFullyQualifiedNamespace string = '${serviceBusNamespace.name}.servicebus.windows.net'
output serviceBusNamespaceName string = serviceBusNamespace.name
output importantEventsQueueName string = importantEvents.name
