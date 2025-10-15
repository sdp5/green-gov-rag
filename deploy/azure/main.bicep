// Azure Bicep template for GreenGovRAG deployment
// Deploys: Container Apps, Blob Storage, PostgreSQL, Key Vault

@description('Project name used for resource naming')
param projectName string = 'greengovrag'

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Environment (dev, staging, prod)')
param environment string = 'dev'

@description('PostgreSQL administrator password')
@secure()
param postgresPassword string

@description('OpenAI API Key')
@secure()
param openaiApiKey string

@description('MapBox Access Token')
@secure()
param mapboxToken string

// Variables
var resourcePrefix = '${projectName}-${environment}'
var storageAccountName = replace('${resourcePrefix}storage', '-', '')
var containerRegistryName = replace('${resourcePrefix}acr', '-', '')
var containerAppEnvName = '${resourcePrefix}-env'
var keyVaultName = '${resourcePrefix}-kv'
var logAnalyticsName = '${resourcePrefix}-logs'

// Storage Account for documents
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
}

// Blob container for documents
resource documentsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: '${storageAccount.name}/default/documents'
  properties: {
    publicAccess: 'None'
  }
}

// Blob container for embeddings
resource embeddingsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: '${storageAccount.name}/default/embeddings'
  properties: {
    publicAccess: 'None'
  }
}

// Azure Cache for Redis
resource redisCache 'Microsoft.Cache/redis@2023-08-01' = {
  name: '${resourcePrefix}-redis'
  location: location
  properties: {
    sku: {
      name: 'Basic'
      family: 'C'
      capacity: 0
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    redisConfiguration: {
      'maxmemory-policy': 'allkeys-lru'
    }
  }
}

// Azure Database for PostgreSQL (with pgvector support)
resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: '${resourcePrefix}-postgres'
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    administratorLogin: 'dbadmin'
    administratorLoginPassword: postgresPassword
    version: '15'
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

// Enable pgvector extension
resource postgresConfig 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-03-01-preview' = {
  name: 'azure.extensions'
  parent: postgresServer
  properties: {
    value: 'VECTOR,POSTGIS'
    source: 'user-override'
  }
}

// PostgreSQL database
resource postgresDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-03-01-preview' = {
  name: 'greengovrag'
  parent: postgresServer
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// PostgreSQL firewall rule (allow Azure services)
resource postgresFirewall 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-03-01-preview' = {
  name: 'AllowAzureServices'
  parent: postgresServer
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// Key Vault for secrets
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
}

// Store OpenAI API key in Key Vault
resource openaiSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'OpenAIKey'
  parent: keyVault
  properties: {
    value: openaiApiKey
  }
}

// Store database connection string in Key Vault
resource dbConnectionSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'DatabaseConnection'
  parent: keyVault
  properties: {
    value: 'postgresql://dbadmin:${postgresPassword}@${postgresServer.properties.fullyQualifiedDomainName}:5432/greengovrag'
  }
}

// Store storage connection string in Key Vault
resource storageConnectionSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'StorageConnection'
  parent: keyVault
  properties: {
    value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=${az.environment().suffixes.storage}'
  }
}

// Store MapBox token in Key Vault
resource mapboxSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'MapBoxToken'
  parent: keyVault
  properties: {
    value: mapboxToken
  }
}

// Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// Container Apps Environment
resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: containerAppEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// Container Registry
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: containerRegistryName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// User Assigned Managed Identity for Container Apps
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${resourcePrefix}-identity'
  location: location
}

// Grant managed identity access to Key Vault
resource keyVaultRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, managedIdentity.id, 'KeyVaultSecretsUser')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // Key Vault Secrets User
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Grant managed identity access to Storage Account
resource storageRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, managedIdentity.id, 'StorageBlobDataContributor')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') // Storage Blob Data Contributor
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Grant managed identity access to Container Registry
resource acrRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, managedIdentity.id, 'AcrPull')
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Container App - API
resource apiContainerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${resourcePrefix}-api'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
        allowInsecure: false
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: managedIdentity.id
        }
      ]
      secrets: [
        {
          name: 'openai-key'
          keyVaultUrl: openaiSecret.properties.secretUri
          identity: managedIdentity.id
        }
        {
          name: 'db-connection'
          keyVaultUrl: dbConnectionSecret.properties.secretUri
          identity: managedIdentity.id
        }
        {
          name: 'storage-connection'
          keyVaultUrl: storageConnectionSecret.properties.secretUri
          identity: managedIdentity.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: '${containerRegistry.properties.loginServer}/greengovrag-api:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'CLOUD_PROVIDER'
              value: 'azure'
            }
            {
              name: 'CLOUD_REGION'
              value: location
            }
            {
              name: 'STORAGE_CONTAINER'
              value: 'documents'
            }
            {
              name: 'AZURE_STORAGE_CONNECTION_STRING'
              secretRef: 'storage-connection'
            }
            {
              name: 'OPENAI_API_KEY'
              secretRef: 'openai-key'
            }
            {
              name: 'DATABASE_URL'
              secretRef: 'db-connection'
            }
            {
              name: 'REDIS_URL'
              value: 'rediss://:${redisCache.listKeys().primaryKey}@${redisCache.properties.hostName}:${redisCache.properties.sslPort}/0'
            }
            {
              name: 'ENABLE_REDIS_CACHE'
              value: 'true'
            }
            {
              name: 'VECTOR_STORE_TYPE'
              value: 'faiss'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
  dependsOn: [
    keyVaultRoleAssignment
    storageRoleAssignment
    acrRoleAssignment
  ]
}

// Container App - React Frontend (Nginx)
resource uiContainerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${resourcePrefix}-frontend'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 80
        transport: 'http'
        allowInsecure: false
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: managedIdentity.id
        }
      ]
      secrets: [
        {
          name: 'mapbox-token'
          keyVaultUrl: mapboxSecret.properties.secretUri
          identity: managedIdentity.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: '${containerRegistry.properties.loginServer}/greengovrag-frontend:latest'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            {
              name: 'VITE_API_URL'
              value: 'https://${apiContainerApp.properties.configuration.ingress.fqdn}/api'
            }
            {
              name: 'VITE_MAPBOX_TOKEN'
              secretRef: 'mapbox-token'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
  dependsOn: [
    keyVaultRoleAssignment
    acrRoleAssignment
    apiContainerApp
  ]
}

// Outputs
output storageAccountName string = storageAccount.name
output storageConnectionString string = storageAccount.listKeys().keys[0].value
output postgresHost string = postgresServer.properties.fullyQualifiedDomainName
output containerRegistryLoginServer string = containerRegistry.properties.loginServer
output apiUrl string = 'https://${apiContainerApp.properties.configuration.ingress.fqdn}'
output frontendUrl string = 'https://${uiContainerApp.properties.configuration.ingress.fqdn}'
output keyVaultName string = keyVault.name
output redisHost string = redisCache.properties.hostName
output redisSslPort int = redisCache.properties.sslPort
