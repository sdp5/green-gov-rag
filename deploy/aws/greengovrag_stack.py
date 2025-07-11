from aws_cdk import (
    RemovalPolicy,
    Stack,
)
from aws_cdk import (
    aws_ec2 as ec2,
)
from aws_cdk import (
    aws_ecs as ecs,
)
from aws_cdk import (
    aws_ecs_patterns as ecs_patterns,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_logs as logs,
)
from aws_cdk import (
    aws_rds as rds,
)
from aws_cdk import (
    aws_s3 as s3,
)
from aws_cdk import (
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct


class GreenGovRAGStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        project_name = self.node.try_get_context("project_name") or "GreenGovRAG"
        region = self.node.try_get_context("region") or "ap-southeast-2"
        docker_path = self.node.try_get_context("docker_image_path") or "../"

        # VPC
        vpc = ec2.Vpc(self, f"{project_name}Vpc", max_azs=2)

        # ECS Cluster
        cluster = ecs.Cluster(self, f"{project_name}Cluster", vpc=vpc)

        # S3 Bucket for Documents
        bucket = s3.Bucket(
            self, f"{project_name}Documents",
            versioned=True,
            public_read_access=False,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.RETAIN
        )

        # RDS PostgreSQL (PostGIS-compatible)
        db_instance = rds.DatabaseInstance(
            self, f"{project_name}Postgres",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_13_7
            ),
            vpc=vpc,
            allocated_storage=20,
            max_allocated_storage=100,
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE2, ec2.InstanceSize.SMALL
            ),
            credentials=rds.Credentials.from_generated_secret("dbadmin"),
            database_name="greengovrag",
            removal_policy=RemovalPolicy.DESTROY,
            deletion_protection=False,
            publicly_accessible=False
        )

        # CloudWatch Logs
        log_group = logs.LogGroup(
            self, f"{project_name}Logs",
            retention=logs.RetentionDays.ONE_WEEK
        )

        # Fargate Task Definition (Multi-container)
        task_definition = ecs.FargateTaskDefinition(
            self, f"{project_name}TaskDef",
            cpu=1024,
            memory_limit_mib=2048
        )

        # Secrets and Env Vars
        openai_key = secretsmanager.Secret.from_secret_name_v2(
            self, "OpenAIKeySecret", "OpenAIKey"
        )

        common_env = {
            "ENV": "prod",
            "REGION": region,
            "S3_BUCKET": bucket.bucket_name
        }

        # Streamlit Container
        streamlit_container = task_definition.add_container(
            f"{project_name}StreamlitContainer",
            image=ecs.ContainerImage.from_asset(docker_path + "/docker/streamlit"),
            environment=common_env,
            secrets={
                "OPENAI_API_KEY": ecs.Secret.from_secrets_manager(openai_key)
            },
            logging=ecs.LogDriver.aws_logs(
                stream_prefix=f"{project_name}Streamlit",
                log_group=log_group
            )
        )
        streamlit_container.add_port_mappings(
            ecs.PortMapping(container_port=8501)
        )

        # FastAPI Container
        api_container = task_definition.add_container(
            f"{project_name}ApiContainer",
            image=ecs.ContainerImage.from_asset(docker_path + "/docker/api"),
            environment=common_env,
            secrets={
                "OPENAI_API_KEY": ecs.Secret.from_secrets_manager(openai_key)
            },
            logging=ecs.LogDriver.aws_logs(
                stream_prefix=f"{project_name}API",
                log_group=log_group
            )
        )
        api_container.add_port_mappings(
            ecs.PortMapping(container_port=8000)
        )

        # Grant S3 Access
        bucket.grant_read_write(task_definition.task_role)

        # Application Load Balanced Fargate Service (for Streamlit)
        ecs_patterns.ApplicationLoadBalancedFargateService(
            self, f"{project_name}Service",
            cluster=cluster,
            task_definition=task_definition,
            public_load_balancer=True,
            listener_port=80,
            task_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            assign_public_ip=True,
            desired_count=1,
            platform_version=ecs.FargatePlatformVersion.LATEST,
            container_name=streamlit_container.container_name,
            container_port=8501
        )
