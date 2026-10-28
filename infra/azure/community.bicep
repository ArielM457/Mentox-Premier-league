// Tiempo real de la revisión comunitaria (Persona 4) sobre el namespace de main.bicep.
// La API publica cada voto, sugerencia y mensaje del chat y lee el hub desde el
// último evento para repartirlo a sus conexiones SSE. No guarda puntos de control.
targetScope = 'resourceGroup'

@description('Salida eventHubNamespaceName del despliegue de main.bicep.')
param eventHubNamespaceName string

resource eventHubNamespace 'Microsoft.EventHub/namespaces@2024-01-01' existing = {
  name: eventHubNamespaceName
}

resource communityEventsHub 'Microsoft.EventHub/namespaces/eventhubs@2024-01-01' = {
  name: 'community-events'
  parent: eventHubNamespace
  properties: {
    // Los votos y mensajes viven en la API; el hub solo los transporta.
    messageRetentionInDays: 1
    partitionCount: 2
    status: 'Active'
  }
}

resource apiConsumerGroup 'Microsoft.EventHub/namespaces/eventhubs/consumerGroups@2024-01-01' = {
  name: 'api'
  parent: communityEventsHub
  properties: {
    userMetadata: 'Réplicas de la API que reparten la comunidad en vivo.'
  }
}

output communityEventHubName string = communityEventsHub.name
output communityConsumerGroup string = apiConsumerGroup.name
