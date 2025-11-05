// Azure Bicep template for GreenGovRAG - Hybrid Architecture
// Cost-optimized deployment
//
// Architecture:
// - Container Apps (1 vCPU, 3GB RAM) for backend
// - PostgreSQL Flexible Server B1s with pgvector extension
// - Table Storage for caching (replaces Redis Cache)
// - Spot VM (B1s) for Qdrant vector database with managed disk
// - Static Web App for frontend (free tier)
// - GitHub Secrets for LLM API credentials (passed as parameters)
//
// Cost optimizations:
// - Spot VM for Qdrant (60-90% savings vs regular VM)
// - Burstable PostgreSQL tier (B1s)
// - Table Storage instead of Redis Cache
// - Free tier Static Web App
// - Pay-per-use Container Apps scaling
// - Delta indexing for incremental updates (faster, cheaper)
//
// Recommended usage: 8 hrs/day for cost optimization
//
// Delta Indexing:
// - Monitoring workflow uploads changed_files.json to blob storage
// - ETL job reads it and runs: rag index --changed-files --mode delta
// - Only re-indexes changed documents (5-20 min vs 60 min full reindex)

@description('Project name used for resource naming')
param projectName string = 'greengovrag'

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Environment (dev, staging, prod)')
param environment string = 'prod'

@description('PostgreSQL administrator password')
@secure()
param postgresPassword string

// Azure OpenAI credentials - passed from GitHub Secrets via deployment
// TODO: Review for production - Consider using Azure Key Vault for better secret management
@description('Azure OpenAI API Key')
@secure()
param azureOpenaiApiKey string = 'REPLACE_VIA_GITHUB_SECRETS'

@description('Azure OpenAI Endpoint')
param azureOpenaiEndpoint string = 'REPLACE_VIA_GITHUB_SECRETS'

@description('Azure OpenAI Deployment Name')
param azureOpenaiDeployment string = 'gpt-5-mini'

@description('API Access Key for authentication')
@secure()
param apiAccessKey string = 'REPLACE_VIA_GITHUB_SECRETS'

@description('MapBox Access Token')
@secure()
param mapboxToken string = ''

// Variables
var resourcePrefix = '${projectName}-${environment}'
var storageAccountName = replace('${resourcePrefix}stor', '-', '')
var containerAppEnvName = '${resourcePrefix}-env'
var logAnalyticsName = '${resourcePrefix}-logs'

// =====================================================================
// Storage Account for documents and Table Storage (caching)
// =====================================================================
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

// Blob container for processed data
resource processedContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: '${storageAccount.name}/default/processed'
  properties: {
    publicAccess: 'None'
  }
}

// Table Storage for caching (replaces Redis)
resource tableService 'Microsoft.Storage/storageAccounts/tableServices@2023-01-01' = {
  name: 'default'
  parent: storageAccount
}

resource cacheTable 'Microsoft.Storage/storageAccounts/tableServices/tables@2023-01-01' = {
  name: 'cache'
  parent: tableService
}

// =====================================================================
// PostgreSQL Flexible Server - B1s (cost-optimized)
// =====================================================================
resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: '${resourcePrefix}-postgres'
  location: location
  sku: {
    name: 'Standard_B1s'  // Cost-optimized: 1 vCPU, 1GB RAM
    tier: 'Burstable'
  }
  properties: {
    administratorLogin: 'dbadmin'
    administratorLoginPassword: postgresPassword
    version: '15'
    storage: {
      storageSizeGB: 32  // Minimum allowed
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'  // Cost optimization
    }
    highAvailability: {
      mode: 'Disabled'  // Cost optimization
    }
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

// Enable pgvector extension
resource postgresConfig 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-03-01-preview' = {
  name: 'azure.extensions'
  parent: postgresServer
  properties: {
    value: 'VECTOR,POSTGIS'
    source: 'user-override'
  }
}

// Firewall rule for Azure services
resource postgresFirewallAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-03-01-preview' = {
  name: 'AllowAzureServices'
  parent: postgresServer
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// =====================================================================
// Qdrant - Spot VM with Managed Disk
// =====================================================================
// Network Security Group for Qdrant
resource qdrantNSG 'Microsoft.Network/networkSecurityGroups@2023-05-01' = {
  name: '${resourcePrefix}-qdrant-nsg'
  location: location
  properties: {
    securityRules: [
      {
        name: 'AllowQdrantHTTP'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '6333'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: '*'
        }
      }
      {
        name: 'AllowQdrantGRPC'
        properties: {
          priority: 101
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '6334'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: '*'
        }
      }
    ]
  }
}

// Virtual Network
resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  name: '${resourcePrefix}-vnet'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.0.0.0/16'
      ]
    }
    subnets: [
      {
        name: 'default'
        properties: {
          addressPrefix: '10.0.0.0/24'
          networkSecurityGroup: {
            id: qdrantNSG.id
          }
        }
      }
    ]
  }
}

// Public IP for Qdrant VM
resource qdrantPublicIP 'Microsoft.Network/publicIPAddresses@2023-05-01' = {
  name: '${resourcePrefix}-qdrant-ip'
  location: location
  sku: {
    name: 'Standard'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
  }
}

// Network Interface for Qdrant
resource qdrantNIC 'Microsoft.Network/networkInterfaces@2023-05-01' = {
  name: '${resourcePrefix}-qdrant-nic'
  location: location
  properties: {
    ipConfigurations: [
      {
        name: 'ipconfig1'
        properties: {
          subnet: {
            id: vnet.properties.subnets[0].id
          }
          privateIPAllocationMethod: 'Dynamic'
          publicIPAddress: {
            id: qdrantPublicIP.id
          }
        }
      }
    ]
  }
}

// Managed Disk for Qdrant persistence
resource qdrantDisk 'Microsoft.Compute/disks@2023-04-02' = {
  name: '${resourcePrefix}-qdrant-disk'
  location: location
  sku: {
    name: 'Standard_LRS'  // Standard HDD for cost
  }
  properties: {
    diskSizeGB: 10
    creationData: {
      createOption: 'Empty'
    }
  }
}

// Qdrant Spot VM
resource qdrantVM 'Microsoft.Compute/virtualMachines@2023-09-01' = {
  name: '${resourcePrefix}-qdrant'
  location: location
  properties: {
    hardwareProfile: {
      vmSize: 'Standard_B1s'  // 1 vCPU, 1GB RAM
    }
    priority: 'Spot'  // Spot instance for cost savings
    evictionPolicy: 'Deallocate'  // Don't delete on eviction
    billingProfile: {
      maxPrice: -1  // Pay up to on-demand price
    }
    storageProfile: {
      imageReference: {
        publisher: 'Canonical'
        offer: '0001-com-ubuntu-server-jammy'
        sku: '22_04-lts-gen2'
        version: 'latest'
      }
      osDisk: {
        createOption: 'FromImage'
        managedDisk: {
          storageAccountType: 'Standard_LRS'
        }
      }
      dataDisks: [
        {
          lun: 0
          createOption: 'Attach'
          managedDisk: {
            id: qdrantDisk.id
          }
        }
      ]
    }
    networkProfile: {
      networkInterfaces: [
        {
          id: qdrantNIC.id
        }
      ]
    }
    osProfile: {
      computerName: 'qdrant'
      adminUsername: 'azureuser'
      adminPassword: postgresPassword  // Reuse same password
      customData: base64('''#!/bin/bash
# Install Docker
apt-get update
apt-get install -y docker.io
systemctl start docker
systemctl enable docker

# Format and mount data disk (if not already formatted)
if ! blkid /dev/sdc1; then
  parted /dev/sdc mklabel gpt
  parted /dev/sdc mkpart primary ext4 0% 100%
  mkfs.ext4 /dev/sdc1
fi

mkdir -p /qdrant/storage
mount /dev/sdc1 /qdrant/storage
echo '/dev/sdc1 /qdrant/storage ext4 defaults,nofail 0 2' >> /etc/fstab

# Run Qdrant container
docker run -d \
  --name qdrant \
  --restart unless-stopped \
  -p 6333:6333 \
  -p 6334:6334 \
  -v /qdrant/storage:/qdrant/storage \
  qdrant/qdrant:latest
''')
    }
  }
}

// =====================================================================
// Log Analytics Workspace
// =====================================================================
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// =====================================================================
// Container Apps Environment
// =====================================================================
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

// =====================================================================
// Container App - Backend API
// =====================================================================
resource apiContainerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${resourcePrefix}-api'
  location: location
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
        allowInsecure: false
      }
      secrets: [
        {
          name: 'api-access-key'
          value: apiAccessKey
        }
        {
          name: 'azure-openai-api-key'
          value: azureOpenaiApiKey
        }
        {
          name: 'azure-openai-endpoint'
          value: azureOpenaiEndpoint
        }
        {
          name: 'postgres-password'
          value: postgresPassword
        }
        {
          name: 'storage-connection-string'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'  // Placeholder
          resources: {
            cpu: json('1.0')  // 1 vCPU for better performance
            memory: '3Gi'     // BGE-large (1.5GB) + app stack (500MB) + headroom (1GB) = 3GB
          }
          env: [
            {
              name: 'DATABASE_URL'
              value: 'postgresql://dbadmin:${postgresPassword}@${postgresServer.properties.fullyQualifiedDomainName}:5432/greengovrag'
            }
            {
              name: 'QDRANT_URL'
              value: 'http://${qdrantNIC.properties.ipConfigurations[0].properties.privateIPAddress}:6333'
            }
            {
              name: 'VECTOR_STORE_TYPE'
              value: 'qdrant'
            }
            {
              name: 'EMBEDDING_MODEL'
              value: 'BAAI/bge-large-en-v1.5'
            }
            {
              name: 'CLOUD_PROVIDER'
              value: 'azure'
            }
            {
              name: 'STORAGE_CONTAINER'
              value: storageAccount.name
            }
            {
              name: 'AZURE_STORAGE_ACCOUNT'
              value: storageAccount.name
            }
            {
              name: 'AZURE_STORAGE_CONNECTION_STRING'
              secretRef: 'storage-connection-string'
            }
            // LLM Configuration - Azure OpenAI
            {
              name: 'LLM_PROVIDER'
              value: 'azure'
            }
            {
              name: 'LLM_MODEL'
              value: 'gpt-5-mini'  // gpt-5-mini (recommended), gpt-5, or gpt-4o
            }
            {
              name: 'AZURE_OPENAI_API_KEY'
              secretRef: 'azure-openai-api-key'
            }
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              secretRef: 'azure-openai-endpoint'
            }
            {
              name: 'AZURE_OPENAI_DEPLOYMENT'
              value: azureOpenaiDeployment
            }
            {
              name: 'AZURE_OPENAI_API_VERSION'
              value: '2024-12-01-preview'
            }
            // API Security
            {
              name: 'API_ACCESS_KEY'
              secretRef: 'api-access-key'
            }
            // Embedding Model - BGE-large for 93% accuracy
            {
              name: 'EMBEDDING_MODEL'
              value: 'BAAI/bge-large-en-v1.5'
            }
            // Cache Settings
            {
              name: 'ENABLE_CACHE'
              value: 'true'
            }
            {
              name: 'ENABLE_REDIS_CACHE'
              value: 'false'
            }
            {
              name: 'REDIS_HOST'
              value: 'localhost'
            }
            {
              name: 'REDIS_PORT'
              value: '6379'
            }
            {
              name: 'CACHE_TTL'
              value: '3600'
            }
            {
              name: 'ENABLE_SEMANTIC_CACHE'
              value: 'true'
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
}

// =====================================================================
// Static Web App - Frontend
// =====================================================================
resource staticWebApp 'Microsoft.Web/staticSites@2023-01-01' = {
  name: '${resourcePrefix}-frontend'
  location: location
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {
    repositoryUrl: ''  // Deployed via GitHub Actions
    branch: ''
    buildProperties: {
      skipGithubActionWorkflowGeneration: true
    }
  }
}

// Static Web App configuration
resource staticWebAppConfig 'Microsoft.Web/staticSites/config@2023-01-01' = {
  name: 'appsettings'
  parent: staticWebApp
  properties: {
    VITE_API_URL: 'https://${apiContainerApp.properties.configuration.ingress.fqdn}/api'
    VITE_MAPBOX_TOKEN: mapboxToken
  }
}

// =====================================================================
// Container App Jobs - ETL Pipeline
// =====================================================================

// ETL Job - Full pipeline (ingest → parse → chunk → index)
resource etlJob 'Microsoft.App/jobs@2023-05-01' = {
  name: '${resourcePrefix}-etl-job'
  location: location
  properties: {
    environmentId: containerAppEnv.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 7200  // 2 hours for full ETL
      replicaRetryLimit: 1
      secrets: [
        {
          name: 'azure-openai-api-key'
          value: azureOpenaiApiKey
        }
        {
          name: 'postgres-password'
          value: postgresPassword
        }
        {
          name: 'storage-connection-string'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'  // Placeholder - updated via GitHub Actions
          resources: {
            cpu: json('2.0')  // 2 vCPU for faster ETL processing
            memory: '4Gi'     // 4GB for large document processing
          }
          command: [
            '/bin/sh'
            '-c'
            'greengovrag-cli etl ingest --config /app/configs/documents_config.yml && greengovrag-cli etl parse --input data/raw --output data/processed && greengovrag-cli etl chunk --input data/processed --output data/chunks --chunk-size 500 --chunk-overlap 100 --mode delta --fast --raw-dir data/raw && greengovrag-cli rag index --chunks data/chunks --vector-store qdrant --collection greengovrag --model $EMBEDDING_MODEL'
          ]
          env: [
            {
              name: 'DATABASE_URL'
              value: 'postgresql://dbadmin:${postgresPassword}@${postgresServer.properties.fullyQualifiedDomainName}:5432/greengovrag'
            }
            {
              name: 'QDRANT_URL'
              value: 'http://${qdrantNIC.properties.ipConfigurations[0].properties.privateIPAddress}:6333'
            }
            {
              name: 'VECTOR_STORE_TYPE'
              value: 'qdrant'
            }
            {
              name: 'EMBEDDING_MODEL'
              value: 'BAAI/bge-large-en-v1.5'
            }
            {
              name: 'CLOUD_PROVIDER'
              value: 'azure'
            }
            {
              name: 'STORAGE_CONTAINER'
              value: storageAccount.name
            }
            {
              name: 'AZURE_STORAGE_ACCOUNT'
              value: storageAccount.name
            }
            {
              name: 'AZURE_STORAGE_CONNECTION_STRING'
              secretRef: 'storage-connection-string'
            }
            {
              name: 'LLM_PROVIDER'
              value: 'azure'
            }
            {
              name: 'LLM_MODEL'
              value: 'gpt-5-mini'
            }
            {
              name: 'AZURE_OPENAI_API_KEY'
              secretRef: 'azure-openai-api-key'
            }
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: azureOpenaiEndpoint
            }
            {
              name: 'AZURE_OPENAI_DEPLOYMENT'
              value: azureOpenaiDeployment
            }
            {
              name: 'AZURE_OPENAI_API_VERSION'
              value: '2024-12-01-preview'
            }
          ]
        }
      ]
    }
  }
}

// Monitoring Job - Check for document changes
resource monitoringJob 'Microsoft.App/jobs@2023-05-01' = {
  name: '${resourcePrefix}-monitoring-job'
  location: location
  properties: {
    environmentId: containerAppEnv.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 1800  // 30 minutes for monitoring
      replicaRetryLimit: 1
      secrets: [
        {
          name: 'storage-connection-string'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'  // Placeholder - updated via GitHub Actions
          resources: {
            cpu: json('0.5')  // 0.5 vCPU for lightweight monitoring
            memory: '1Gi'
          }
          command: [
            'python'
            '-m'
            'green_gov_rag.cli'
            'etl'
            'monitor'
            '--format'
            'json'
          ]
          env: [
            {
              name: 'CLOUD_PROVIDER'
              value: 'azure'
            }
            {
              name: 'STORAGE_CONTAINER'
              value: storageAccount.name
            }
            {
              name: 'AZURE_STORAGE_ACCOUNT'
              value: storageAccount.name
            }
            {
              name: 'AZURE_STORAGE_CONNECTION_STRING'
              secretRef: 'storage-connection-string'
            }
          ]
        }
      ]
    }
  }
}

// =====================================================================
// Outputs
// =====================================================================
output storageAccountName string = storageAccount.name
output storageConnectionString string = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
output postgresHost string = postgresServer.properties.fullyQualifiedDomainName
output postgresDatabaseName string = postgresDatabase.name
output apiUrl string = 'https://${apiContainerApp.properties.configuration.ingress.fqdn}'
output frontendUrl string = 'https://${staticWebApp.properties.defaultHostname}'
output staticWebAppName string = staticWebApp.name
output qdrantPrivateIP string = qdrantNIC.properties.ipConfigurations[0].properties.privateIPAddress
output qdrantPublicIP string = qdrantPublicIP.properties.ipAddress
output qdrantVMName string = qdrantVM.name
output logAnalyticsWorkspaceId string = logAnalytics.id
output containerAppEnvironmentId string = containerAppEnv.id
output etlJobName string = etlJob.name
output monitoringJobName string = monitoringJob.name
