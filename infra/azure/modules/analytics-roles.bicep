// Roles de la identidad de la analítica sobre Event Hubs y Blob Storage.
// Va en un módulo porque los nombres llegan como salidas de main.bicep.
targetScope = 'resourceGroup'

@description('principalId de la identidad administrada de las Container Apps.')
param principalId string

@description('Namespace de Event Hubs creado por main.bicep.')
param eventHubNamespaceName string

@description('Cuenta de Storage creada por main.bicep.')
param storageAccountName string

var roleIds = {
  eventHubsDataSender: '2b629674-e913-4c01-ae53-ef4638d8f975'
  eventHubsDataReceiver: 'a638d3c7-ab3a-418d-83e6-5f17a39d4fde'
  storageBlobDataContributor: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
}

resource eventHubNamespace 'Microsoft.EventHub/namespaces@2024-01-01' existing = {
  name: eventHubNamespaceName
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2025-06-01' existing = {
  name: storageAccountName
}

resource eventHubsSender 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(eventHubNamespace.id, principalId, roleIds.eventHubsDataSender)
  scope: eventHubNamespace
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.eventHubsDataSender)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}

resource eventHubsReceiver 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(eventHubNamespace.id, principalId, roleIds.eventHubsDataReceiver)
  scope: eventHubNamespace
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.eventHubsDataReceiver)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}

resource blobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, principalId, roleIds.storageBlobDataContributor)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.storageBlobDataContributor)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
