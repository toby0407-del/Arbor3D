/*
  Azure Container Apps hosting for Arbor3D Cloud DBH worker.

  Deploys:
    - Storage account (job scratch; optional blob share later)
    - Log Analytics + Container Apps Environment
    - Container App running the cloud_dbh FastAPI (CPU by default)

  GPU: Azure for Students often lacks NC-series quota. Start with CPU +
  ARBOR3D_CLOUD_PREPARE_ONLY=true for smoke, then request GPU quota or
  run full DBH on a Windows GPU machine / paid NC SKU.
*/

@description('Azure region')
param location string = resourceGroup().location

@description('Short name prefix, lowercase alphanumeric, max 10 chars')
@minLength(3)
@maxLength(10)
param namePrefix string = 'arbor3d'

@description('Container image (ACR or public). Build: docker build -f cloud_dbh/Dockerfile …')
param containerImage string

@description('Existing private ACR in this resource group; images are pulled using managed identity')
param registryName string

@description('CPU cores for the worker')
param cpu string = '2.0'

@description('Memory for the worker')
param memory string = '4Gi'

@description('Min replicas (0 = scale to zero when idle)')
param minReplicas int = 1

@description('Max replicas')
param maxReplicas int = 1

@description('Required server-side API key; never place it in frontend configuration')
@secure()
@minLength(32)
param apiKey string

@description('When true, worker only prepares inbox (no PyTorch DBH)')
param prepareOnly bool = false

var unique = uniqueString(resourceGroup().id, namePrefix)
var envName = '${namePrefix}-cae-${unique}'
var appName = '${namePrefix}-dbh-${unique}'
var lawName = '${namePrefix}-law-${unique}'

resource law 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: lawName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: registryName
}

resource workerIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-dbh-pull-${unique}'
  location: location
}

resource pullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, workerIdentity.id, 'AcrPull')
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: workerIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource cae 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: envName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: law.properties.customerId
        sharedKey: law.listKeys().primarySharedKey
      }
    }
  }
}

var baseEnv = [
  {
    name: 'ARBOR3D_CLOUD_WORK_DIR'
    value: '/var/arbor3d/jobs'
  }
  {
    name: 'ARBOR3D_CLOUD_PREPARE_ONLY'
    value: prepareOnly ? 'true' : 'false'
  }
]

var secretEnv = empty(apiKey) ? [] : [
  {
    name: 'ARBOR3D_CLOUD_DBH_API_KEY'
    secretRef: 'dbh-api-key'
  }
]

resource dbhApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${workerIdentity.id}': {}
    }
  }
  dependsOn: [pullRole]
  properties: {
    managedEnvironmentId: cae.id
    configuration: {
      registries: [
        {
          server: registry.properties.loginServer
          identity: workerIdentity.id
        }
      ]
      ingress: {
        external: true
        targetPort: 8080
        transport: 'auto'
        allowInsecure: false
      }
      secrets: empty(apiKey) ? [] : [
        {
          name: 'dbh-api-key'
          value: apiKey
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'cloud-dbh'
          image: containerImage
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: concat(baseEnv, secretEnv)
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8080
              }
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8080
              }
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }
    }
  }
}

output containerAppFqdn string = dbhApp.properties.configuration.ingress.fqdn
output containerAppName string = dbhApp.name
output cloudDbhBaseUrl string = 'https://${dbhApp.properties.configuration.ingress.fqdn}'
output setAppEnvHint string = 'ARBOR3D_CLOUD_DBH_URL=https://${dbhApp.properties.configuration.ingress.fqdn}'
