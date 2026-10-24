targetScope = 'resourceGroup'

@description('Namespace de Event Hubs existente donde se agregará el canal visual.')
param eventHubNamespaceName string

@description('Nombre del canal separado para observaciones experimentales.')
param visionEventHubName string = 'vision-observations'

resource eventHubNamespace 'Microsoft.EventHub/namespaces@2024-01-01' existing = {
  name: eventHubNamespaceName
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

resource backendConsumerGroup 'Microsoft.EventHub/namespaces/eventhubs/consumerGroups@2024-01-01' = {
  name: 'backend'
  parent: visionObservationsHub
  properties: {
    userMetadata: 'Consume observaciones visuales para validación, fusión y entrega en vivo.'
  }
}

resource diagnosticsConsumerGroup 'Microsoft.EventHub/namespaces/eventhubs/consumerGroups@2024-01-01' = {
  name: 'diagnostics'
  parent: visionObservationsHub
  properties: {
    userMetadata: 'Pruebas aisladas del canal de observaciones visuales.'
  }
}

output visionEventHubName string = visionObservationsHub.name
output backendConsumerGroupName string = backendConsumerGroup.name
output diagnosticsConsumerGroupName string = diagnosticsConsumerGroup.name
