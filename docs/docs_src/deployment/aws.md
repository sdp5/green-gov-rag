# AWS Deployment

> Production deployment using AWS ECS Fargate, RDS, and Qdrant on EC2

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         CloudFront                          │
│                      (CDN + HTTPS)                          │
└──────────────────┬──────────────────────────────────────────┘
                   │
     ┌─────────────┴────────────┐
     │                          │
     ▼                          ▼
┌─────────────┐          ┌─────────────┐
│  S3 Bucket  │          │  API GW     │
│  (Frontend) │          │  HTTP API   │
└─────────────┘          └──────┬──────┘
                                │
                                ▼
                         ┌─────────────┐
                         │ ECS Fargate │
                         │  (Backend)  │
                         └──────┬──────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
              ▼                 ▼                 ▼
       ┌─────────────┐   ┌──────────┐    ┌──────────────┐
       │ RDS Postgres│   │  Qdrant  │    │  DynamoDB    │
       │  (pgvector) │   │ (EC2 t4g)│    │   (Cache)    │
       └─────────────┘   └──────────┘    └──────────────┘
```

## Prerequisites

### 1. AWS Account Setup

- AWS account with billing enabled
- AWS CLI installed and configured:

```bash
aws configure
# Enter Access Key ID, Secret Key, Region (us-east-1), Format (json)
```

### 2. Install AWS CDK

```bash
# Install Node.js 18+ first
npm install -g aws-cdk

# Verify installation
cdk --version
```

### 3. Required IAM Permissions

Your AWS user/role needs permissions for:

- ECS, EC2, VPC, ELB
- RDS, S3, CloudFront, DynamoDB
- IAM, CloudFormation, Systems Manager

Or use `AdministratorAccess` policy (not recommended for production).

### 4. LLM API Key

You need an API key for one of:

- OpenAI API (`sk-...`)
- Azure OpenAI (endpoint + key + deployment name)
- AWS Bedrock (in supported region)

## Deployment Steps

### 1. Clone Repository

```bash
git clone https://github.com/sdp5/green-gov-rag.git
cd green-gov-rag/deploy/aws
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Configure CDK Context

Edit `cdk.json` or set environment variables:

```json
{
  "context": {
    "stack_name": "greengovrag-prod",
    "environment": "production",
    "vpc_cidr": "10.0.0.0/16",
    "database_name": "greengovrag",
    "use_spot_instances": true,
    "enable_cdn": true
  }
}
```

### 4. Set Secrets in SSM Parameter Store

```bash
# OpenAI API Key
aws ssm put-parameter \
  --name "/greengovrag/prod/openai-api-key" \
  --value "sk-your-key-here" \
  --type "SecureString" \
  --description "OpenAI API key for LLM"

# Database Password (auto-generated, or set custom)
aws ssm put-parameter \
  --name "/greengovrag/prod/db-password" \
  --value "$(openssl rand -base64 32)" \
  --type "SecureString"

# Optional: Azure OpenAI
aws ssm put-parameter \
  --name "/greengovrag/prod/azure-openai-key" \
  --value "your-azure-key" \
  --type "SecureString"
```

### 5. Bootstrap CDK (First Time Only)

```bash
cdk bootstrap aws://ACCOUNT-ID/REGION

# Example
cdk bootstrap aws://123456789012/us-east-1
```

### 6. Review Stack

```bash
# See what will be created
cdk diff
```

### 7. Deploy Stack

```bash
# Deploy all resources
cdk deploy

# Or deploy with approval
cdk deploy --require-approval never
```

Deployment takes ~15-20 minutes. You'll see:

- VPC and subnets creation
- RDS PostgreSQL instance
- ECS cluster and service
- EC2 instance for Qdrant
- S3 bucket and CloudFront distribution
- API Gateway

### 8. Get Outputs

```bash
# View stack outputs
aws cloudformation describe-stacks \
  --stack-name greengovrag-prod \
  --query 'Stacks[0].Outputs'
```

**Important outputs**:

- `ApiUrl`: Backend API endpoint
- `FrontendUrl`: CloudFront distribution URL
- `QdrantUrl`: Qdrant service endpoint (internal VPC only)
- `DatabaseEndpoint`: RDS endpoint

### 9. Verify Deployment

```bash
# Health check
API_URL=$(aws cloudformation describe-stacks \
  --stack-name greengovrag-prod \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text)

curl $API_URL/api/health
```

### 10. Run ETL Pipeline

ETL runs automatically via GitHub Actions (scheduled daily at 2 AM UTC).

**Manual trigger**:
```bash
# Via GitHub Actions UI: Actions → ETL Scheduled → Run workflow

# Or via GitHub CLI
gh workflow run etl-scheduled.yml
```

## Configuration

### Environment Variables

Set in `deploy/aws/lib/backend-stack.ts`:

```typescript
environment: {
  LLM_PROVIDER: 'openai',
  LLM_MODEL: 'gpt-5-mini',
  VECTOR_STORE_TYPE: 'qdrant',
  QDRANT_URL: qdrant.instancePrivateIp,
  DATABASE_URL: rds.instanceEndpoint.socketAddress,
  CLOUD_PROVIDER: 'aws',
  LOG_LEVEL: 'INFO',
}
```

### Secrets (SSM Parameter Store)

Access in backend via:

```python
import boto3

ssm = boto3.client('ssm', region_name='us-east-1')
api_key = ssm.get_parameter(
    Name='/greengovrag/prod/openai-api-key',
    WithDecryption=True
)['Parameter']['Value']
```

CDK automatically injects as environment variables.

### Scaling Configuration

**ECS Fargate Auto-Scaling**:

Edit `deploy/aws/lib/backend-stack.ts`:

```typescript
const scaling = service.autoScaleTaskCount({
  minCapacity: 1,
  maxCapacity: 10
});

scaling.scaleOnCpuUtilization('CpuScaling', {
  targetUtilizationPercent: 70,
  scaleInCooldown: cdk.Duration.seconds(60),
  scaleOutCooldown: cdk.Duration.seconds(60)
});

scaling.scaleOnMemoryUtilization('MemoryScaling', {
  targetUtilizationPercent: 80
});
```

Redeploy: `cdk deploy`

### Database Scaling

**Upgrade RDS instance**:

Edit `deploy/aws/lib/database-stack.ts`:

```typescript
instanceType: ec2.InstanceType.of(
  ec2.InstanceClass.T4G,
  ec2.InstanceSize.SMALL  // Change from MICRO
)
```

### Qdrant Scaling

**Upgrade EC2 instance**:

Edit `deploy/aws/lib/qdrant-stack.ts`:

```typescript
instanceType: ec2.InstanceType.of(
  ec2.InstanceClass.T4G,
  ec2.InstanceSize.MEDIUM  // Change from MICRO
)
```

## CI/CD Pipeline

### GitHub Actions Setup

#### 1. Configure Secrets

In GitHub repository settings (Settings → Secrets and variables → Actions):

```
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
OPENAI_API_KEY=sk-...
```

#### 2. Workflow Files

**.github/workflows/deploy-aws.yml** (Auto-deploy on push to main):

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ secrets.AWS_REGION }}
      - name: Deploy CDK stack
        run: |
          cd deploy/aws
          npm install
          cdk deploy --require-approval never
```

**.github/workflows/etl-scheduled.yml** (Daily ETL run):

```yaml
name: ETL Scheduled Pipeline

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC

jobs:
  etl:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger ECS task
        run: |
          aws ecs run-task \
            --cluster greengovrag-cluster \
            --task-definition greengovrag-etl \
            --launch-type FARGATE
```

## Monitoring

### CloudWatch Logs

```bash
# View backend logs
aws logs tail /ecs/greengovrag-backend --follow

# View ETL logs
aws logs tail /ecs/greengovrag-etl --follow

# Search for errors
aws logs filter-pattern /ecs/greengovrag-backend --pattern "ERROR"
```

### CloudWatch Metrics

**View in AWS Console**: CloudWatch → Dashboards → greengovrag-dashboard

**Key metrics**:

- ECS CPU/Memory utilization
- RDS CPU/Connections
- API Gateway 4XX/5XX errors
- DynamoDB read/write capacity

### CloudWatch Alarms

Auto-created alarms:

- `HighCPUUtilization`: ECS CPU > 80% for 5 minutes
- `HighMemoryUtilization`: ECS Memory > 90% for 5 minutes
- `DatabaseHighConnections`: RDS connections > 80
- `APIHighErrorRate`: API 5XX errors > 10/minute

**View alarms**:
```bash
aws cloudwatch describe-alarms --state-value ALARM
```

### X-Ray Tracing

Enable X-Ray in `backend-stack.ts`:

```typescript
import * as xray from 'aws-cdk-lib/aws-xray';

// Add X-Ray daemon as sidecar
taskDefinition.addContainer('xray-daemon', {
  image: ecs.ContainerImage.fromRegistry('amazon/aws-xray-daemon'),
  // ... config
});
```

## Backup and Recovery

### RDS Automated Backups

Configured in `database-stack.ts`:

```typescript
new rds.DatabaseInstance(this, 'Database', {
  backupRetention: cdk.Duration.days(7),
  deleteAutomatedBackups: false,
  preferredBackupWindow: '02:00-03:00',  // 2-3 AM UTC
});
```

**Manual snapshot**:
```bash
aws rds create-db-snapshot \
  --db-instance-identifier greengovrag-db \
  --db-snapshot-identifier greengovrag-manual-$(date +%Y%m%d)
```

**Restore from snapshot**:
```bash
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier greengovrag-db-restored \
  --db-snapshot-identifier greengovrag-manual-20251115
```

### Qdrant Backups

**Snapshot creation** (runs weekly via EventBridge):

```bash
# Manual snapshot
ssh ec2-user@qdrant-instance
curl -X POST 'http://localhost:6333/collections/greengovrag/snapshots'

# Download snapshot
scp ec2-user@qdrant-instance:/var/lib/qdrant/snapshots/*.snapshot ./
```

**Restore**:
```bash
# Upload snapshot
scp snapshot.tar ec2-user@qdrant-instance:/tmp/

# Restore
curl -X PUT 'http://localhost:6333/collections/greengovrag/snapshots/upload' \
  --data-binary @/tmp/snapshot.tar
```

### DynamoDB Backups

Enable point-in-time recovery:

```typescript
new dynamodb.Table(this, 'CacheTable', {
  pointInTimeRecovery: true,
});
```

## Troubleshooting

### Issue: CDK Deploy Fails

**Error**: `Stack greengovrag-prod failed: CREATE_FAILED`

**Solution**: Check CloudFormation events:

```bash
aws cloudformation describe-stack-events \
  --stack-name greengovrag-prod \
  --max-items 10
```

Common causes:

- Insufficient IAM permissions
- Parameter Store secrets missing
- Resource limits exceeded (VPC, EIP, etc.)

### Issue: ECS Task Fails to Start

**Error**: `Task stopped: Essential container exited`

**Solution**: Check ECS task logs:

```bash
# Get task ARN
aws ecs list-tasks --cluster greengovrag-cluster

# View stopped task reason
aws ecs describe-tasks \
  --cluster greengovrag-cluster \
  --tasks <task-arn>
```

### Issue: RDS Connection Timeout

**Error**: `could not connect to server: Connection timed out`

**Solution**: Check security group rules:

```bash
# Ensure backend SG can access RDS SG on port 5432
aws ec2 describe-security-groups \
  --filters "Name=tag:Name,Values=greengovrag-*"
```

### Issue: High Costs

**Solution**: Optimize resources:

1. Use Spot instances for Qdrant (already default)
2. Reduce RDS instance size (t4g.micro → t4g.nano if low traffic)
3. Enable S3 Intelligent-Tiering
4. Set DynamoDB to on-demand pricing
5. Enable CloudFront compression

## Updating Deployment

### Update Backend Code

Push to `main` branch → GitHub Actions auto-deploys:

```bash
git add .
git commit -m "Update backend logic"
git push origin main
```

### Update Infrastructure

Edit CDK code, then:

```bash
cd deploy/aws
cdk diff  # Review changes
cdk deploy
```

### Update Environment Variables

```bash
# Update SSM parameter
aws ssm put-parameter \
  --name "/greengovrag/prod/openai-api-key" \
  --value "sk-new-key" \
  --type "SecureString" \
  --overwrite

# Restart ECS service to pick up new value
aws ecs update-service \
  --cluster greengovrag-cluster \
  --service greengovrag-service \
  --force-new-deployment
```

## Teardown

### Delete Stack

```bash
# Delete all resources
cdk destroy

# Confirm deletion
# This will delete: ECS, RDS, EC2, S3, CloudFront, API Gateway, VPC
```

**Note**: Some resources may have deletion protection:

- RDS instance (if `deletionProtection: true`)
- S3 bucket (if not empty)

**Force delete**:

```bash
# Empty S3 bucket
aws s3 rm s3://greengovrag-frontend-bucket --recursive

# Disable RDS deletion protection
aws rds modify-db-instance \
  --db-instance-identifier greengovrag-db \
  --no-deletion-protection

# Then retry cdk destroy
cdk destroy
```

## Next Steps

- [Production Checklist](production-checklist.md) - Pre-launch verification
- [Monitoring Guide](monitoring.md) - Detailed monitoring setup
- [Cloud Comparison](cloud-comparison.md) - AWS vs Azure comparison

---

**Last Updated**: 2025-11-22
