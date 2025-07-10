### Synthesize and Deploy Stack

```bash
cd deploy
cdk bootstrap
cdk deploy --context project_name=GreenGovRAG --context region=ap-southeast-2
```

### Push Image to ECR Instead of Building in CDK

If you don’t want to build Docker images in CDK, create an ECR repository:

```bash
aws ecr create-repository --repository-name greengovrag
```

Push your image:

```bash
docker build -t greengovrag .
docker tag greengovrag:latest <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/greengovrag:latest
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

After `cdk deploy`, CDK will output the ALB DNS URL for public access to your Streamlit/FastAPI UI.
