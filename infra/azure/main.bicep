@description('Globally unique Azure Cosmos DB account name')
param cosmosAccountName string

@description('Azure region; keep the app and Cosmos DB in the same region')
param location string = resourceGroup().location

@description('Cosmos DB for NoSQL database name')
param databaseName string = 'Arbor3D'

@description('Container for field measurements; partition key is /scanId')
param containerName string = 'FieldMeasures'

@description('Managed Identity object ID used by the Arbor3D server; leave empty to assign later')
param appPrincipalId string = ''

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' = {
  name: cosmosAccountName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    publicNetworkAccess: 'Enabled'
    minimalTlsVersion: 'Tls12'
    disableLocalAuth: true
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-11-15' = {
  parent: cosmos
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

resource fieldMeasures 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-11-15' = {
  parent: database
  name: containerName
  properties: {
    resource: {
      id: containerName
      partitionKey: {
        paths: [
          '/scanId'
        ]
        kind: 'Hash'
        version: 2
      }
      indexingPolicy: {
        automatic: true
        indexingMode: 'consistent'
        includedPaths: [
          { path: '/scanId/?' }
          { path: '/type/?' }
          { path: '/updatedAt/?' }
        ]
        excludedPaths: [
          { path: '/*' }
        ]
      }
    }
  }
}

var dataContributorRoleId = '00000000-0000-0000-0000-000000000002'

resource appDataRole 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-11-15' = if (!empty(appPrincipalId)) {
  parent: cosmos
  name: guid(cosmos.id, appPrincipalId, dataContributorRoleId)
  properties: {
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/${dataContributorRoleId}'
    principalId: appPrincipalId
    scope: cosmos.id
  }
}

output cosmosEndpoint string = cosmos.properties.documentEndpoint
output database string = databaseName
output container string = containerName
output partitionKey string = '/scanId'
