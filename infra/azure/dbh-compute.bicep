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
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('CPU cores for the worker')
param cpu string = '2.0'

@description('Memory for the worker')
param memory string = '4Gi'

@description('Min replicas (0 = scale to zero when idle)')
param minReplicas int = 0

@description('Max replicas')
param maxReplicas int = 1

@description('Optional API key; leave empty to rely on network controls only')
@secure()
param apiKey string = ''

@description('When true, worker only prepares inbox (no PyTorch DBH)')
param prepareOnly bool = true

var unique = uniqueString(resourceGroup().id, namePrefix)
var storageName = take('st${namePrefix}${unique}', 24)
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

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
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
  properties: {
    managedEnvironmentId: cae.id
    configuration: {
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
output storageAccountName string = storage.name
output cloudDbhBaseUrl string = 'https://${dbhApp.properties.configuration.ingress.fqdn}'
output setAppEnvHint string = 'ARBOR3D_CLOUD_DBH_URL=https://${dbhApp.properties.configuration.ingress.fqdn}'
