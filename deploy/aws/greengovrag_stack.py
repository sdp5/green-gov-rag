"""AWS CDK Stack for GreenGovRAG deployment.

Deploys:
- VPC with public/private subnets
- ECS Fargate cluster with backend and frontend containers
- RDS PostgreSQL with pgvector extension
- ElastiCache Redis for caching
- S3 bucket for document storage
- Secrets Manager for sensitive configuration
- Application Load Balancer with path-based routing
"""

from aws_cdk import (
    CfnOutput,
    Duration,
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
    aws_elasticache as elasticache,
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
    """CloudFormation stack for GreenGovRAG infrastructure."""

    def __init__(self, scope: Construct, id: str, **kwargs):
        """Initialize the GreenGovRAG stack.

        Args:
            scope: CDK app scope
            id: Stack identifier
            **kwargs: Additional stack arguments including env with account and region
        """
        super().__init__(scope, id, **kwargs)

        # Get context values with defaults
        project_name = self.node.try_get_context("project_name") or "GreenGovRAG"
        environment = self.node.try_get_context("environment") or "prod"

        # =====================================================================
        # VPC - Create isolated network for resources
        # =====================================================================
        vpc = ec2.Vpc(
            self, f"{project_name}Vpc",
            max_azs=2,
            nat_gateways=1,  # Cost optimization: use 1 NAT gateway
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
            ],
        )

        # =====================================================================
        # Security Groups
        # =====================================================================

        # Redis security group
        redis_sg = ec2.SecurityGroup(
            self, f"{project_name}RedisSG",
            vpc=vpc,
            description="Security group for Redis cache",
            allow_all_outbound=True,
        )

        # RDS security group
        rds_sg = ec2.SecurityGroup(
            self, f"{project_name}RdsSG",
            vpc=vpc,
            description="Security group for PostgreSQL database",
            allow_all_outbound=True,
        )

        # ECS security group
        ecs_sg = ec2.SecurityGroup(
            self, f"{project_name}EcsSG",
            vpc=vpc,
            description="Security group for ECS tasks",
            allow_all_outbound=True,
        )

        # Allow ECS to access Redis
        redis_sg.add_ingress_rule(
            peer=ecs_sg,
            connection=ec2.Port.tcp(6379),
            description="Allow ECS tasks to access Redis",
        )

        # Allow ECS to access RDS
        rds_sg.add_ingress_rule(
            peer=ecs_sg,
            connection=ec2.Port.tcp(5432),
            description="Allow ECS tasks to access PostgreSQL",
        )

        # =====================================================================
        # S3 Bucket for Documents
        # =====================================================================
        bucket = s3.Bucket(
            self, f"{project_name}Documents",
            versioned=True,
            public_read_access=False,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldVersions",
                    noncurrent_version_expiration=Duration.days(30),
                    enabled=True,
                )
            ],
        )

        # =====================================================================
        # ElastiCache Redis - For caching and session management
        # =====================================================================
        redis_subnet_group = elasticache.CfnSubnetGroup(
            self, f"{project_name}RedisSubnetGroup",
            description=f"Subnet group for {project_name} Redis",
            subnet_ids=vpc.select_subnets(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ).subnet_ids,
        )

        redis_cluster = elasticache.CfnCacheCluster(
            self, f"{project_name}Redis",
            cache_node_type="cache.t3.micro",  # Cost-effective tier
            engine="redis",
            num_cache_nodes=1,
            cache_subnet_group_name=redis_subnet_group.ref,
            vpc_security_group_ids=[redis_sg.security_group_id],
            engine_version="7.0",
        )
        redis_cluster.add_dependency(redis_subnet_group)

        # =====================================================================
        # RDS PostgreSQL with pgvector - Database + Vector Store
        # =====================================================================

        # Create parameter group for pgvector extension
        parameter_group = rds.ParameterGroup(
            self, f"{project_name}PostgresParams",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15_4
            ),
            description=f"Parameter group for {project_name} with pgvector support",
            parameters={
                "shared_preload_libraries": "vector",
            },
        )

        db_instance = rds.DatabaseInstance(
            self, f"{project_name}Postgres",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15_4
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[rds_sg],
            allocated_storage=20,
            max_allocated_storage=100,
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.SMALL
            ),
            credentials=rds.Credentials.from_generated_secret(
                "dbadmin",
                secret_name=f"{project_name}DbSecret",
            ),
            database_name="greengovrag",
            parameter_group=parameter_group,
            backup_retention=Duration.days(7),
            removal_policy=RemovalPolicy.SNAPSHOT,  # Create snapshot before deletion
            deletion_protection=False,
            publicly_accessible=False,
            multi_az=False,  # Set to True for production HA
        )

        # =====================================================================
        # Secrets Manager - Store sensitive configuration
        # =====================================================================

        # OpenAI API Key secret (must be created manually or via CLI)
        openai_key = secretsmanager.Secret.from_secret_name_v2(
            self, "OpenAIKeySecret",
            secret_name="greengovrag/openai-api-key",
        )

        # MapBox Token secret (must be created manually or via CLI)
        mapbox_token = secretsmanager.Secret.from_secret_name_v2(
            self, "MapBoxTokenSecret",
            secret_name="greengovrag/mapbox-token",
        )

        # =====================================================================
        # CloudWatch Logs
        # =====================================================================
        log_group = logs.LogGroup(
            self, f"{project_name}Logs",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # =====================================================================
        # ECS Cluster
        # =====================================================================
        cluster = ecs.Cluster(
            self, f"{project_name}Cluster",
            vpc=vpc,
            container_insights=True,  # Enable CloudWatch Container Insights
        )

        # =====================================================================
        # Backend API Task Definition (FastAPI)
        # =====================================================================
        backend_task = ecs.FargateTaskDefinition(
            self, f"{project_name}BackendTask",
            cpu=512,
            memory_limit_mib=1024,
        )

        # Common environment variables
        backend_env = {
            "APP_ENV": environment,
            "CLOUD_PROVIDER": "aws",
            "CLOUD_REGION": self.region,
            "S3_BUCKET": bucket.bucket_name,
            "REDIS_URL": f"redis://{redis_cluster.attr_redis_endpoint_address}:{redis_cluster.attr_redis_endpoint_port}",
            "VECTOR_STORE_TYPE": "faiss",  # Can be changed to pgvector after extension setup
            "ENABLE_REDIS_CACHE": "true",
            "CORS_ORIGINS": "https://*",  # Update with your domain
        }

        backend_container = backend_task.add_container(
            "backend",
            image=ecs.ContainerImage.from_asset(
                directory="../../",
                file="deploy/docker/backend.Dockerfile",
            ),
            environment=backend_env,
            secrets={
                "OPENAI_API_KEY": ecs.Secret.from_secrets_manager(openai_key),
                "DATABASE_URL": ecs.Secret.from_secrets_manager(
                    db_instance.secret,
                    field="connectionString",
                ),
            },
            logging=ecs.LogDriver.aws_logs(
                stream_prefix="backend",
                log_group=log_group,
            ),
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "curl -f http://localhost:8000/api/health || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
                start_period=Duration.seconds(60),
            ),
        )
        backend_container.add_port_mappings(
            ecs.PortMapping(container_port=8000, protocol=ecs.Protocol.TCP)
        )

        # Grant backend access to S3 bucket
        bucket.grant_read_write(backend_task.task_role)

        # =====================================================================
        # Frontend Task Definition (React + Nginx)
        # =====================================================================
        frontend_task = ecs.FargateTaskDefinition(
            self, f"{project_name}FrontendTask",
            cpu=256,
            memory_limit_mib=512,
        )

        frontend_container = frontend_task.add_container(
            "frontend",
            image=ecs.ContainerImage.from_asset(
                directory="../../",
                file="deploy/docker/frontend.Dockerfile",
            ),
            environment={
                # Note: MapBox token injected at build time via arg
                # For runtime injection, use entrypoint script
            },
            secrets={
                "VITE_MAPBOX_TOKEN": ecs.Secret.from_secrets_manager(mapbox_token),
            },
            logging=ecs.LogDriver.aws_logs(
                stream_prefix="frontend",
                log_group=log_group,
            ),
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "curl -f http://localhost:80/ || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
                start_period=Duration.seconds(30),
            ),
        )
        frontend_container.add_port_mappings(
            ecs.PortMapping(container_port=80, protocol=ecs.Protocol.TCP)
        )

        # =====================================================================
        # Backend ECS Service with ALB
        # =====================================================================
        backend_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, f"{project_name}BackendService",
            cluster=cluster,
            task_definition=backend_task,
            public_load_balancer=True,
            listener_port=80,
            desired_count=1,
            min_healthy_percent=50,
            max_healthy_percent=200,
            health_check_grace_period=Duration.seconds(60),
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            security_groups=[ecs_sg],
            task_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
        )

        # Configure health check on target group
        backend_service.target_group.configure_health_check(
            path="/api/health",
            interval=Duration.seconds(30),
            timeout=Duration.seconds(5),
            healthy_threshold_count=2,
            unhealthy_threshold_count=3,
        )

        # Add path-based routing for /api/*
        backend_service.listener.add_targets(
            "BackendTarget",
            port=8000,
            targets=[backend_service.service],
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "curl -f http://localhost:8000/api/health || exit 1"],
                interval=Duration.seconds(30),
            ),
            priority=1,
            conditions=[
                ecs_patterns.ListenerCondition.path_patterns(["/api/*"]),
            ],
        )

        # =====================================================================
        # Frontend ECS Service (same ALB, different path)
        # =====================================================================
        frontend_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, f"{project_name}FrontendService",
            cluster=cluster,
            task_definition=frontend_task,
            public_load_balancer=False,  # Use existing ALB
            listener_port=80,
            desired_count=1,
            min_healthy_percent=50,
            max_healthy_percent=200,
            health_check_grace_period=Duration.seconds(30),
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            security_groups=[ecs_sg],
            task_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
        )

        # Configure frontend health check
        frontend_service.target_group.configure_health_check(
            path="/",
            interval=Duration.seconds(30),
            timeout=Duration.seconds(5),
            healthy_threshold_count=2,
            unhealthy_threshold_count=3,
        )

        # Add default routing for /* (frontend)
        backend_service.listener.add_targets(
            "FrontendTarget",
            port=80,
            targets=[frontend_service.service],
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "curl -f http://localhost:80/ || exit 1"],
                interval=Duration.seconds(30),
            ),
            priority=2,
            conditions=[
                ecs_patterns.ListenerCondition.path_patterns(["/*"]),
            ],
        )

        # =====================================================================
        # Outputs - Important endpoints and connection details
        # =====================================================================
        CfnOutput(
            self, "LoadBalancerDNS",
            value=backend_service.load_balancer.load_balancer_dns_name,
            description="Application Load Balancer DNS",
            export_name=f"{project_name}-alb-dns",
        )

        CfnOutput(
            self, "ApplicationURL",
            value=f"http://{backend_service.load_balancer.load_balancer_dns_name}",
            description="Application URL (frontend)",
        )

        CfnOutput(
            self, "ApiURL",
            value=f"http://{backend_service.load_balancer.load_balancer_dns_name}/api",
            description="Backend API URL",
        )

        CfnOutput(
            self, "DatabaseHost",
            value=db_instance.db_instance_endpoint_address,
            description="PostgreSQL database host",
        )

        CfnOutput(
            self, "DatabaseSecretArn",
            value=db_instance.secret.secret_arn,
            description="Database credentials secret ARN",
        )

        CfnOutput(
            self, "RedisEndpoint",
            value=f"{redis_cluster.attr_redis_endpoint_address}:{redis_cluster.attr_redis_endpoint_port}",
            description="Redis endpoint",
        )

        CfnOutput(
            self, "S3BucketName",
            value=bucket.bucket_name,
            description="S3 bucket for documents",
        )

        CfnOutput(
            self, "VpcId",
            value=vpc.vpc_id,
            description="VPC ID",
        )
