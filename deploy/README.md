## DEPLOYMENT OPTIONS

| Component            | AWS Option                               | Azure Option                                   |
| -------------------- | ---------------------------------------- | ---------------------------------------------- |
| App hosting (API/UI) | ECS Fargate or Lambda + API Gateway      | Azure App Service or Azure Functions           |
| Vector DB            | Self-host FAISS in ECS/EKS or EC2        | Self-host FAISS in Azure Container Apps or VM  |
| RDBMS (metadata)     | Amazon RDS (PostgreSQL)                  | Azure Database for PostgreSQL                  |
| LLM Provider         | AWS Bedrock (Claude/Titan) or OpenAI API | Azure OpenAI Service (GPT-4, GPT-3.5)          |
| File storage (PDFs)  | S3                                       | Azure Blob Storage                             |
| Scheduler (ETL)      | EventBridge + Lambda or ECS + Celery     | Azure Logic Apps + Function App or Azure Batch |
| Monitoring/CI        | CloudWatch + CodePipeline                | Azure Monitor + GitHub Actions                 |

### DEPLOYMENT ON AWS

#### 1. Option A – Serverless + API Gateway + Lambda

Ideal for lightweight, low-traffic MVPs

- API: FastAPI app → Zipped + deployed to Lambda via API Gateway
- LLM calls: Via OpenAI API or AWS Bedrock
- Document uploads: Stored in S3
- Vector DB: Use FAISS in Lambda (limited) or host via ECS
- ETL Preprocessing: Run periodically via Lambda triggered by S3 upload or EventBridge
- Storage:
  - Metadata DB: Amazon RDS (PostgreSQL)
  - Embeddings: FAISS persisted on EFS or ECS volume

🛠️ Tools
- AWS CDK or CloudFormation
- Docker (for ECS)
- boto3 for integrations
- Optional: Bedrock + Claude for internal LLM

#### 2. Option B – ECS + Docker + RDS

Ideal for scalable, production-ready version
- FastAPI/Streamlit backend: Docker container deployed via ECS Fargate
- Task runners (ETL): Use Celery in another container (or AWS Batch)
- Vector DB (FAISS): Container with persistent EBS volume
- PostgreSQL DB: Amazon RDS
- LLM Access: OpenAI or Bedrock (Claude/Titan)
- Storage: AWS S3 (PDFs), with tagging for metadata

### DEPLOYMENT ON AZURE

#### 1. Option A – Azure App Service + Blob + PostgreSQL + Azure OpenAI

Faster time to deploy, less container orchestration
- App hosting: Deploy FastAPI via GitHub Actions to Azure App Service
- Blob storage: Upload PDFs to Azure Blob
- PostgreSQL DB: Azure Database for PostgreSQL
- Vector DB: Run FAISS in App Service or offload to Azure Container App
- LLM: Use Azure OpenAI Service (GPT-4, gpt-35-turbo)
- ETL pipeline: Azure Functions triggered on Blob upload or Logic Apps for scheduled runs

##### Tools
- Azure CLI, GitHub Actions
- Azure Resource Manager (ARM) templates
- LangChain Azure integrations

#### 2. Option B – Containerized with Azure Container Apps or Azure Kubernetes Service (AKS)

More control, suited to your Docker + Kubernetes experience

- App and RAG service: Docker images deployed on Azure Container Apps or AKS
- Vector DB: FAISS or Qdrant container with persistent volume
- LLM Access: Azure OpenAI endpoint or REST API
- ETL: Celery worker container or Azure Functions
- Metadata DB: Azure PostgreSQL

Extras:
- Use Azure Key Vault for secret management
- Azure DevOps or GitHub Actions for CI/CD
- Azure Monitor for logs

### CI/CD

| Platform | Tools                                                              |
| -------- | ------------------------------------------------------------------ |
| AWS      | GitHub Actions + ECR + ECS + CloudFormation/CDK                    |
| Azure    | GitHub Actions + Azure CLI + App Service Deploy or Bicep Templates |
