// Despliegue completo de la analítica (Persona 2) en Azure.
//
// Reutiliza main.bicep (Event Hubs y Storage de Persona 1) y analytics.bicep
// (match-insights y contenedores de la analítica) como módulos, y añade:
// Log Analytics, Azure Container Registry, una identidad administrada con sus
// roles, un entorno de Container Apps y, en la fase 2, las aplicaciones:
//   - api:    API de Persona 4 con la analítica real de Persona 2 (pública).
//   - web:    interfaz de Persona 4 servida por nginx (pública, opcional).
//   - worker: procesador continuo de match-events a match-insights.
//   - replay: trabajo manual que repite un partido de Supabase en match-events.
//
// Fase 1 (deployApps=false): infraestructura y registro, sin imágenes.
// Fase 2 (deployApps=true): las aplicaciones con las imágenes ya publicadas.
targetScope = 'resourceGroup'

@description('Prefijo corto, en minúsculas, para distinguir el despliegue.')
@minLength(3)
@maxLength(9)
param projectPrefix string

@description('Entorno lógico usado en nombres y etiquetas.')
@allowed([
  'dev'
  'test'
  'demo'
])
param environmentName string = 'demo'

@description('Región de los recursos. De forma predeterminada usa la región del grupo.')
param location string = resourceGroup().location

@description('false en la fase 1; true cuando las imágenes ya están en el registro.')
param deployApps bool = false

@description('Imagen del backend, por ejemplo <registro>.azurecr.io/match-intelligence-api:<etiqueta>.')
param apiImage string = ''

@description('Imagen de la interfaz. Vacía para no desplegarla.')
param webImage string = ''

@description('Cadena del Session pooler de Supabase. Vacía: la API usa los generadores sintéticos.')
@secure()
param supabaseDbUrl string = ''

@description('1 mantiene la API encendida (sin arranque en frío); 0 la apaga sin tráfico.')
@minValue(0)
@maxValue(1)
param apiMinReplicas int = 0

@description('1 enciende el procesador continuo; 0 lo deja apagado y sin costo de cómputo.')
@minValue(0)
@maxValue(1)
param workerReplicas int = 0

@description('Partido de Supabase que repite el trabajo replay.')
param replayMatchId string = 'synthetic-analytics-001'

@description('Velocidad de la repetición; 1 es tiempo real.')
param replaySpeed string = '8'

var normalizedPrefix = toLower(replace(projectPrefix, '-', ''))
var resourceSuffix = uniqueString(subscription().id, resourceGroup().id, projectPrefix)
var names = {
  logs: 'log-${normalizedPrefix}-${environmentName}-${substring(resourceSuffix, 0, 6)}'
  registry: 'cr${normalizedPrefix}${resourceSuffix}'
  identity: 'id-${normalizedPrefix}-${environmentName}-analytics'
  environment: 'cae-${normalizedPrefix}-${environmentName}'
  api: 'ca-${normalizedPrefix}-api'
  worker: 'ca-${normalizedPrefix}-worker'
  web: 'ca-${normalizedPrefix}-web'
  replay: 'caj-${normalizedPrefix}-replay'
}
var tags = {
  project: 'mentox-premier-league'
  environment: environmentName
  managedBy: 'bicep'
  workload: 'analytics'
}
var hasDatabase = !empty(supabaseDbUrl)
var deployWeb = deployApps && !empty(webImage)
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

module data 'main.bicep' = {
  name: 'data-vision'
  params: {
    projectPrefix: projectPrefix
    environmentName: environmentName
    location: location
  }
}

module insights 'analytics.bicep' = {
  name: 'analytics-insights'
  params: {
    eventHubNamespaceName: data.outputs.eventHubNamespaceName
    storageAccountName: data.outputs.storageAccountName
  }
}

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: names.logs
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    workspaceCapping: {
      dailyQuotaGb: json('0.1')
    }
  }
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: names.registry
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: names.identity
  location: location
  tags: tags
}

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, identity.id, acrPullRoleId)
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

module dataRoles 'modules/analytics-roles.bicep' = {
  name: 'analytics-roles'
  params: {
    principalId: identity.properties.principalId
    eventHubNamespaceName: data.outputs.eventHubNamespaceName
    storageAccountName: data.outputs.storageAccountName
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: names.environment
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
    zoneRedundant: false
  }
}

var apiFqdn = '${names.api}.${environment.properties.defaultDomain}'
var registries = [
  {
    server: registry.properties.loginServer
    identity: identity.id
  }
]
var databaseSecrets = hasDatabase ? [
  {
    name: 'supabase-db-url'
    value: supabaseDbUrl
  }
] : []
var databaseEnv = hasDatabase ? [
  {
    name: 'SUPABASE_DB_URL'
    secretRef: 'supabase-db-url'
  }
] : []
var azureEnv = [
  {
    name: 'AZURE_CLIENT_ID'
    value: identity.properties.clientId
  }
  {
    name: 'EVENT_HUB_FULLY_QUALIFIED_NAMESPACE'
    value: data.outputs.eventHubFullyQualifiedNamespace
  }
  {
    name: 'EVENT_HUB_NAME'
    value: data.outputs.eventHubName
  }
  {
    name: 'INSIGHTS_EVENT_HUB_NAME'
    value: insights.outputs.insightsEventHubName
  }
  {
    name: 'AZURE_BLOB_SERVICE_ENDPOINT'
    value: data.outputs.blobServiceEndpoint
  }
]

resource api 'Microsoft.App/containerApps@2024-03-01' = if (deployApps) {
  name: names.api
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
  dependsOn: [
    acrPull
  ]
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      registries: registries
      secrets: databaseSecrets
    }
    template: {
      containers: [
        {
          name: 'api'
          image: apiImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: concat([
            {
              name: 'ANALYTICS_ENGINE'
              value: 'persona2'
            }
            {
              name: 'MATCH_SOURCE'
              value: hasDatabase ? 'supabase' : 'synthetic'
            }
            {
              name: 'AZURE_CLIENT_ID'
              value: identity.properties.clientId
            }
          ], databaseEnv)
          probes: [
            {
              // /matches carga los partidos (y su seguimiento) antes de recibir tráfico.
              type: 'Startup'
              httpGet: {
                path: '/api/v1/matches'
                port: 8000
              }
              initialDelaySeconds: 5
              periodSeconds: 10
              timeoutSeconds: 60
              failureThreshold: 10
            }
            {
              type: 'Liveness'
              httpGet: {
                path: '/api/v1/health'
                port: 8000
              }
              periodSeconds: 30
              timeoutSeconds: 5
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        // Una sola réplica: la API guarda en memoria la revisión editorial y los reportes.
        minReplicas: apiMinReplicas
        maxReplicas: 1
      }
    }
  }
}

resource worker 'Microsoft.App/containerApps@2024-03-01' = if (deployApps) {
  name: names.worker
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
  dependsOn: [
    acrPull
    dataRoles
  ]
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      registries: registries
      secrets: databaseSecrets
    }
    template: {
      containers: [
        {
          name: 'worker'
          image: apiImage
          command: [
            'python'
            'scripts/analytics_stream_worker.py'
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: concat(azureEnv, [
            {
              name: 'EVENT_HUB_CONSUMER_GROUP'
              value: 'backend'
            }
            {
              name: 'ANALYTICS_IDLE_SECONDS'
              value: '30'
            }
          ], databaseEnv)
        }
      ]
      scale: {
        minReplicas: workerReplicas
        maxReplicas: 1
      }
    }
  }
}

resource replay 'Microsoft.App/jobs@2024-03-01' = if (deployApps && hasDatabase) {
  name: names.replay
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
  dependsOn: [
    acrPull
    dataRoles
  ]
  properties: {
    environmentId: environment.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 3600
      replicaRetryLimit: 0
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      registries: registries
      secrets: databaseSecrets
    }
    template: {
      containers: [
        {
          name: 'replay'
          image: apiImage
          command: [
            'python'
            'scripts/replay_match_to_event_hubs.py'
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: concat(azureEnv, [
            {
              name: 'REPLAY_MATCH_ID'
              value: replayMatchId
            }
            {
              name: 'REPLAY_SPEED'
              value: replaySpeed
            }
          ], databaseEnv)
        }
      ]
    }
  }
}

resource web 'Microsoft.App/containerApps@2024-03-01' = if (deployWeb) {
  name: names.web
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
  dependsOn: [
    acrPull
  ]
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 80
        transport: 'auto'
        allowInsecure: false
      }
      registries: registries
    }
    template: {
      containers: [
        {
          name: 'web'
          image: webImage
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            {
              name: 'API_UPSTREAM'
              value: 'https://${apiFqdn}'
            }
            {
              name: 'API_HOST'
              value: apiFqdn
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

output registryName string = registry.name
output registryLoginServer string = registry.properties.loginServer
output containerAppsEnvironmentName string = environment.name
output identityClientId string = identity.properties.clientId
output apiAppName string = names.api
output workerAppName string = names.worker
output webAppName string = names.web
output replayJobName string = names.replay
output apiUrl string = 'https://${apiFqdn}'
output webUrl string = deployWeb ? 'https://${names.web}.${environment.properties.defaultDomain}' : ''
output databaseConfigured bool = hasDatabase
output eventHubNamespaceName string = data.outputs.eventHubNamespaceName
output eventHubFullyQualifiedNamespace string = data.outputs.eventHubFullyQualifiedNamespace
output insightsEventHubName string = insights.outputs.insightsEventHubName
output storageAccountName string = data.outputs.storageAccountName
output blobServiceEndpoint string = data.outputs.blobServiceEndpoint
