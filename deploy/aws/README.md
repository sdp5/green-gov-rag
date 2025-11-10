### Synthesize and Deploy Stack

```bash
cd deploy/aws
cdk bootstrap
cdk deploy
```

Configuration is loaded from `cdk.json` (project name, region, container port).

### Push Image to ECR Instead of Building in CDK

If you don’t want to build Docker images in CDK, create an ECR repository:

```bash
aws ecr create-repository --repository-name greengovrag
```

Push your image:

```bash
# From repository root
docker build -t greengovrag -f deploy/docker/backend.Dockerfile .
docker tag greengovrag:latest <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/greengovrag:latest
aws ecr get-login-password --region <REGION> | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com
docker push <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/greengovrag:latest
```

Then in CDK:

```bash
container = task_definition.add_container(
    f"{project_name}Container",
    image=ecs.ContainerImage.from_registry(
        "<ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/greengovrag:latest"
    ),
    ...
)
```

After `cdk deploy`, CDK will output the ALB DNS URL for public access to your FastAPI backend.

### Container Port

The backend FastAPI service runs on port **8000** (configured in `cdk.json`).
