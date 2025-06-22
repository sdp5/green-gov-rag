param location string = 'australiaeast'
param appName string = 'greengovragapp'
param planName string = 'greengovrag-plan'
param storageName string = 'greengovragstorage'

resource plan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: planName
  location: location
  sku: {
    name: 'B1'
    tier: 'Basic'
  }
}

resource webApp 'Microsoft.Web/sites@2022-03-01' = {
  name: appName
  location: location
  properties: {
    serverFarmId: plan.id
    siteConfig: {
      linuxFxVersion: 'DOCKER|sdp5/green-gov-rag:latest'  // Replace with your Docker Hub / ACR image
      appSettings: [
        {
          name: 'OPENAI_API_KEY'
          value: 'your-key-here'
        }
      ]
    }
  }
}
