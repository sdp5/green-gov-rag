# Azure Deployment for GreenGovRAG

## Prerequisites

- Azure CLI
- GitHub Secrets:
    - `AZURE_CREDENTIALS`
    - `DOCKERHUB_USERNAME`
    - `DOCKERHUB_TOKEN`

## To Deploy:

```bash
az login
az group create --name GreenGovRAG --location australiaeast
az deployment group create \
  --resource-group GreenGovRAG \
  --template-file deploy/azure/bicep/main.bicep \
  --parameters appName=green-gov-rag-app
