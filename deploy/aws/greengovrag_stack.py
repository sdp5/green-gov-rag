"""AWS CDK Stack for GreenGovRAG - Hybrid Architecture.

Cost-optimized deployment with:
- VPC with public subnets only (no NAT Gateway)
- ECS Fargate Spot backend with fallback (1-3 tasks, auto-scaling)
- RDS PostgreSQL t4g.micro with pgvector
- DynamoDB for caching (replaces ElastiCache)
- EC2 on-demand t4g.micro for Qdrant vector database
- Application Load Balancer ($16/mo)
- CloudFront + S3 for frontend (global CDN)
- GitHub Secrets for LLM API keys (no SSM endpoint needed)
- S3 Gateway Endpoint (free)

Architecture flow:
CloudFront → ALB → ECS Fargate Spot → RDS PostgreSQL + Qdrant

Cost optimizations:
- No NAT Gateway (saves $40-50/mo)
- No VPC Link (saves $20/mo)
- No SSM endpoint (saves $10/mo)
- ARM64/Graviton processors (20% cost reduction)
- Fargate Spot with on-demand fallback (70% discount)
- ECS auto-scaling (saves when idle, scales 1-3 tasks)
- Pay-per-request DynamoDB (vs provisioned ElastiCache)
- On-demand EC2 for stateful Qdrant (reliability over savings)
"""

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_dynamodb as dynamodb,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_rds as rds,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_servicediscovery as servicediscovery,
    SecretValue,
)
from constructs import Construct


class GreenGovRAGStack(Stack):
    """Hybrid architecture stack with managed services and on-demand EC2."""

    def __init__(self, scope: Construct, id: str, **kwargs):
        """Initialize the GreenGovRAG hybrid stack.

        Args:
            scope: CDK app scope
            id: Stack identifier
            **kwargs: Additional stack arguments including env with account and region
        """
        super().__init__(scope, id, **kwargs)

        # Get context values with defaults
        project_name = self.node.try_get_context("project_name") or "GreenGovRAG"
        app_env = self.node.try_get_context("app_env") or "production"

        # Secrets - Retrieved from context (passed via GitHub Actions or CLI)
        api_access_key = self.node.try_get_context("api_access_key") or "REPLACE_VIA_GITHUB_SECRETS"
        azure_openai_api_key = self.node.try_get_context("azure_openai_api_key") or "REPLACE_VIA_GITHUB_SECRETS"
        azure_openai_endpoint = self.node.try_get_context("azure_openai_endpoint") or "REPLACE_VIA_GITHUB_SECRETS"
        qdrant_api_key = self.node.try_get_context("qdrant_api_key") or "REPLACE_VIA_GITHUB_SECRETS"
        sql_db_password = self.node.try_get_context("sql_db_password") or "REPLACE_VIA_GITHUB_SECRETS"

        # Configurable settings - Retrieved from context with sensible defaults
        cloud_provider = self.node.try_get_context("cloud_provider") or "aws"
        llm_provider = self.node.try_get_context("llm_provider") or "azure"
        llm_model = self.node.try_get_context("llm_model") or "gpt-5-mini"
        azure_openai_deployment = self.node.try_get_context("azure_openai_deployment") or llm_model
        azure_openai_api_version = self.node.try_get_context("azure_openai_api_version") or "2024-12-01-preview"
        bedrock_model_id = self.node.try_get_context("bedrock_model_id") or "amazon.nova-pro-v1:0"
        embedding_model = self.node.try_get_context("embedding_model") or "BAAI/bge-large-en-v1.5"
        vector_store_type = self.node.try_get_context("vector_store_type") or "qdrant"
        enable_cache = self.node.try_get_context("enable_cache") or "true"
        enable_redis_cache = self.node.try_get_context("enable_redis_cache") or "false"
        cache_ttl = self.node.try_get_context("cache_ttl") or "3600"
        enable_semantic_cache = self.node.try_get_context("enable_semantic_cache") or "true"
        cors_origins = self.node.try_get_context("cors_origins") or "https://greengovrag.sundeep.id.au,https://greengovrag.au"

        # Docker image tag - defaults to 'latest' for local development
        image_tag = self.node.try_get_context("image_tag") or "latest"

        # =====================================================================
        # VPC - Public Subnets Only (No NAT Gateway)
        # =====================================================================
        vpc = ec2.Vpc(
            self,
            f"{project_name}Vpc",
            max_azs=2,
            nat_gateways=0,  # Cost savings: $40-45/month
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                )
            ],
        )

        # =====================================================================
        # VPC Endpoints - Cost Optimized (1 AZ only)
        # =====================================================================
        # S3 Gateway Endpoint (Free)
        s3_endpoint = vpc.add_gateway_endpoint(
            f"{project_name}S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )

        # SSM Interface Endpoint (for secrets) - $10/month for 1 AZ
        # COMMENTED OUT: Using GitHub Secrets injected as env vars to save SSM costs
        # TODO: Review later - SSM provides better security, audit logs, and rotation
        # Uncomment below for production deployment with proper secret management
        # ssm_endpoint = vpc.add_interface_endpoint(
        #     f"{project_name}SSMEndpoint",
        #     service=ec2.InterfaceVpcEndpointAwsService.SSM,
        #     subnets=ec2.SubnetSelection(
        #         subnet_type=ec2.SubnetType.PUBLIC,
        #         availability_zones=[vpc.availability_zones[0]],  # 1 AZ only
        #     ),
        #     private_dns_enabled=True,
        # )

        # =====================================================================
        # Security Groups
        # =====================================================================
        # ECS Backend security group
        ecs_sg = ec2.SecurityGroup(
            self,
            f"{project_name}EcsSG",
            vpc=vpc,
            description="Security group for ECS backend tasks",
            allow_all_outbound=True,
        )

        # RDS security group
        rds_sg = ec2.SecurityGroup(
            self,
            f"{project_name}RdsSG",
            vpc=vpc,
            description="Security group for PostgreSQL database",
            allow_all_outbound=False,
        )
        rds_sg.add_ingress_rule(
            peer=ecs_sg,
            connection=ec2.Port.tcp(5432),
            description="Allow ECS tasks to access PostgreSQL",
        )

        # Qdrant security group
        qdrant_sg = ec2.SecurityGroup(
            self,
            f"{project_name}QdrantSG",
            vpc=vpc,
            description="Security group for Qdrant vector database",
            allow_all_outbound=True,  # Need internet for Docker Hub, yum, SSM
        )
        qdrant_sg.add_ingress_rule(
            peer=ecs_sg,
            connection=ec2.Port.tcp(6333),
            description="Allow ECS tasks to access Qdrant",
        )

        # Optional: Debug access (comment out in production)
        # Uncomment below for ping/SSH access during development
        # qdrant_sg.add_ingress_rule(
        #     peer=ec2.Peer.any_ipv4(),
        #     connection=ec2.Port.all_icmp(),
        #     description="Allow ping for debugging",
        # )
        # qdrant_sg.add_ingress_rule(
        #     peer=ec2.Peer.ipv4("YOUR_IP/32"),  # Replace with your IP
        #     connection=ec2.Port.tcp(22),
        #     description="SSH access for debugging"
        # )

        # =====================================================================
        # S3 Bucket for Documents and Frontend
        # =====================================================================
        # Documents bucket
        docs_bucket = s3.Bucket(
            self,
            f"{project_name}Documents",
            versioned=False,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INTELLIGENT_TIERING,
                            transition_after=Duration.days(30),
                        )
                    ]
                )
            ],
        )

        # Frontend bucket
        frontend_bucket = s3.Bucket(
            self,
            f"{project_name}Frontend",
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )

        # =====================================================================
        # DynamoDB for Caching (replaces ElastiCache Redis)
        # =====================================================================
        cache_table = dynamodb.Table(
            self,
            f"{project_name}Cache",
            partition_key=dynamodb.Attribute(
                name="cache_key", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=False,  # Cost optimization
        )

        # =====================================================================
        # RDS PostgreSQL - ARM64 for cost efficiency
        # =====================================================================
        db_instance = rds.DatabaseInstance(
            self,
            f"{project_name}PostgreSQL",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_17
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T4G,  # ARM Graviton
                ec2.InstanceSize.MICRO,
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_groups=[rds_sg],
            allocated_storage=20,
            storage_type=rds.StorageType.GP3,
            storage_encrypted=True,
            multi_az=False,
            publicly_accessible=False,
            backup_retention=Duration.days(7),
            deletion_protection=False,
            removal_policy=RemovalPolicy.SNAPSHOT,
            database_name="greengovrag",
            credentials=rds.Credentials.from_password(
                username="postgres",
                password=SecretValue.unsafe_plain_text(sql_db_password),  # From GitHub Secrets
            ),
        )

        # =====================================================================
        # Lambda - PostgreSQL pgvector initialization
        # =====================================================================
        pgvector_init_lambda = lambda_.Function(
            self,
            f"{project_name}PgvectorInit",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="pgvector_init.handler",
            code=lambda_.Code.from_asset("lambda"),
            timeout=Duration.minutes(5),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            allow_public_subnet=True,  # Lambda in public subnet (no NAT Gateway for cost savings)
            security_groups=[ec2.SecurityGroup(
                self,
                f"{project_name}LambdaInitSG",
                vpc=vpc,
                allow_all_outbound=True,
            )],
            environment={
                "DB_HOST": db_instance.db_instance_endpoint_address,
                "DB_USER": "postgres",
                "DB_PASSWORD": sql_db_password,
                "DB_NAME": "greengovrag",
            },
        )

        # Allow Lambda to connect to RDS
        rds_sg.add_ingress_rule(
            peer=ec2.Peer.security_group_id(pgvector_init_lambda.connections.security_groups[0].security_group_id),
            connection=ec2.Port.tcp(5432),
            description="Allow Lambda to initialize pgvector",
        )

        # =====================================================================
        # ECR Repository - Reference existing (created separately)
        # =====================================================================
        # Using from_repository_name instead of creating to avoid conflicts
        # ECR repository should be created separately via AWS CLI or console
        # This allows the repo to persist across stack deletions/updates
        backend_repo = ecr.Repository.from_repository_name(
            self,
            f"{project_name}BackendRepo",
            repository_name=f"{project_name.lower()}-backend",
        )

        # =====================================================================
        # ECS Cluster with Service Discovery
        # =====================================================================
        cluster = ecs.Cluster(
            self,
            f"{project_name}Cluster",
            vpc=vpc,
            container_insights_v2=None,  # Cost optimization - disabled
        )

        # Cloud Map namespace for service discovery
        namespace = servicediscovery.PrivateDnsNamespace(
            self,
            f"{project_name}Namespace",
            name="greengovrag.local",
            vpc=vpc,
        )

        # =====================================================================
        # EC2 On-Demand Instance for Qdrant
        # =====================================================================
        # NOTE: Keeping Qdrant on-demand (not Spot) because:
        # - Stateful service storing vector embeddings
        # - Spot interruptions would cause data loss and service disruption
        # - EBS volume reattachment complexity with ASG across AZs

        # IAM role for Qdrant EC2 instance
        qdrant_role = iam.Role(
            self,
            f"{project_name}QdrantRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
            ],
        )

        # Qdrant user data script
        qdrant_user_data = ec2.UserData.for_linux()
        qdrant_user_data.add_commands(
            "#!/bin/bash",
            "set -x  # Enable debug logging",
            "exec > >(tee /var/log/qdrant-startup.log)",
            "exec 2>&1",
            "",
            "echo '[INFO] Starting Qdrant EC2 instance setup...'",
            "yum update -y",
            "yum install -y docker",
            "systemctl start docker",
            "systemctl enable docker",
            "",
            "# Wait for EBS volume attachment",
            "echo '[INFO] Waiting for EBS volume attachment...'",
            "while [ ! -e /dev/xvdf ]; do sleep 1; done",
            "echo '[INFO] EBS volume attached'",
            "",
            "# Format and mount EBS volume (if not formatted)",
            "if ! blkid /dev/xvdf; then",
            "  echo '[INFO] Formatting EBS volume...'",
            "  mkfs -t ext4 /dev/xvdf",
            "fi",
            "mkdir -p /qdrant/storage",
            "mount /dev/xvdf /qdrant/storage",
            "echo '[INFO] EBS volume mounted'",
            "",
            "# Add to fstab for auto-mount",
            "echo '/dev/xvdf /qdrant/storage ext4 defaults,nofail 0 2' >> /etc/fstab",
            "",
            "# Run Qdrant container",
            "echo '[INFO] Pulling Qdrant Docker image...'",
            "docker pull qdrant/qdrant:latest",
            "echo '[INFO] Starting Qdrant container...'",
            "docker run -d \\",
            "  --name qdrant \\",
            "  --restart unless-stopped \\",
            "  -p 6333:6333 \\",
            "  -p 6334:6334 \\",
            f"  -e QDRANT__SERVICE__API_KEY={qdrant_api_key} \\",
            "  -v /qdrant/storage:/qdrant/storage \\",
            "  qdrant/qdrant:latest",
            "",
            "# Wait for Qdrant to be ready",
            "echo '[INFO] Waiting for Qdrant to become ready...'",
            "MAX_WAIT=60",
            "COUNT=0",
            "while [ $COUNT -lt $MAX_WAIT ]; do",
            "  if curl -sf http://localhost:6333/ > /dev/null 2>&1; then",
            "    echo '[SUCCESS] Qdrant is ready and accepting connections!'",
            "    exit 0",
            "  fi",
            "  COUNT=$((COUNT + 1))",
            "  sleep 2",
            "done",
            "echo '[ERROR] Qdrant failed to start within 120 seconds'",
            "docker logs qdrant",
        )

        # Qdrant EC2 instance (on-demand for reliability)
        qdrant_instance = ec2.Instance(
            self,
            f"{project_name}QdrantInstance",
            instance_type=ec2.InstanceType("t4g.micro"),
            machine_image=ec2.MachineImage.latest_amazon_linux2023(
                cpu_type=ec2.AmazonLinuxCpuType.ARM_64
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_group=qdrant_sg,
            role=qdrant_role,
            user_data=qdrant_user_data,
            require_imdsv2=True,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvdf",
                    volume=ec2.BlockDeviceVolume.ebs(
                        volume_size=10,
                        volume_type=ec2.EbsDeviceVolumeType.GP3,
                        encrypted=True,
                        delete_on_termination=False,  # Persist data
                    ),
                )
            ],
        )

        # Register Qdrant instance with service discovery
        qdrant_service = namespace.create_service(
            f"{project_name}QdrantService",
            name="qdrant",
            dns_record_type=servicediscovery.DnsRecordType.A,
            dns_ttl=Duration.seconds(30),
        )

        # Add instance to service discovery
        qdrant_service.register_ip_instance(
            f"{project_name}QdrantInstanceRegistration",
            ipv4=qdrant_instance.instance_private_ip,
        )

        # =====================================================================
        # ECS Backend Task Definition - ARM64
        # =====================================================================
        # CPU: 1 vCPU for better performance
        # Memory: 3GB to support BGE-large embeddings with headroom
        # BGE-large (1.5GB) + FastAPI/LangChain (500MB) + buffer (1GB) = 3GB
        backend_task = ecs.FargateTaskDefinition(
            self,
            f"{project_name}BackendTask",
            cpu=1024,  # 1 vCPU for better performance
            memory_limit_mib=3072,  # 3 GB (safe for BAAI/bge-large-en-v1.5 + app stack)
            ephemeral_storage_gib=30,  # 30 GB for model cache and temporary files
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.ARM64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
            ),
        )

        # Grant task access to S3 and DynamoDB
        docs_bucket.grant_read_write(backend_task.task_role)
        cache_table.grant_read_write_data(backend_task.task_role)

        # Backend container
        backend_container = backend_task.add_container(
            "backend",
            image=ecs.ContainerImage.from_ecr_repository(backend_repo, image_tag),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="backend",
                log_retention=logs.RetentionDays.ONE_WEEK,
            ),
            environment={
                "DATABASE_URL": f"postgresql://postgres:{sql_db_password}@{db_instance.db_instance_endpoint_address}:5432/greengovrag",
                "QDRANT_URL": f"http://{qdrant_instance.instance_private_ip}:6333",
                "QDRANT_API_KEY": qdrant_api_key,
                "VECTOR_STORE_TYPE": vector_store_type,
                "EMBEDDING_MODEL": embedding_model,
                "STORAGE_CONTAINER": docs_bucket.bucket_name,
                "DYNAMODB_CACHE_TABLE": cache_table.table_name,
                "CLOUD_PROVIDER": cloud_provider,
                "CLOUD_REGION": self.region,
                # LLM Configuration - Supports Azure OpenAI, AWS Bedrock, or OpenAI
                # Azure: AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT
                # AWS Bedrock: BEDROCK_MODEL_ID
                # OpenAI: OPENAI_API_KEY
                "LLM_PROVIDER": llm_provider,
                "LLM_MODEL": llm_model,
                "AZURE_OPENAI_API_VERSION": azure_openai_api_version,
                "AZURE_OPENAI_API_KEY": azure_openai_api_key,
                "AZURE_OPENAI_ENDPOINT": azure_openai_endpoint,
                "AZURE_OPENAI_DEPLOYMENT": azure_openai_deployment,
                "BEDROCK_MODEL_ID": bedrock_model_id,
                # Cache Settings
                "ENABLE_CACHE": enable_cache,
                "ENABLE_REDIS_CACHE": enable_redis_cache,  # Using DynamoDB instead
                "CACHE_TTL": cache_ttl,
                "ENABLE_SEMANTIC_CACHE": enable_semantic_cache,
                # API Security - Access key for all API endpoints
                "API_ACCESS_KEY": api_access_key,
                "APP_ENV": app_env,
                # CORS - Allow CloudFront and custom domains
                "CORS_ORIGINS": cors_origins,
            },
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "curl -f http://localhost:8000/api/health || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
            ),
        )

        backend_container.add_port_mappings(ecs.PortMapping(container_port=8000))

        # =====================================================================
        # ECS Backend Service with Service Discovery
        # =====================================================================
        backend_service = ecs.FargateService(
            self,
            f"{project_name}BackendService",
            cluster=cluster,
            task_definition=backend_task,
            desired_count=1,
            assign_public_ip=True,
            security_groups=[ecs_sg],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            cloud_map_options=ecs.CloudMapOptions(
                cloud_map_namespace=namespace,
                name="backend",
                dns_record_type=servicediscovery.DnsRecordType.A,
            ),
            capacity_provider_strategies=[
                ecs.CapacityProviderStrategy(
                    capacity_provider="FARGATE_SPOT",
                    weight=2,  # Prefer Spot (70% cheaper)
                    base=0,
                ),
                ecs.CapacityProviderStrategy(
                    capacity_provider="FARGATE",
                    weight=1,  # Fallback to on-demand if Spot unavailable
                ),
            ],
        )

        # Auto-scaling for cost efficiency
        scaling = backend_service.auto_scale_task_count(min_capacity=1, max_capacity=3)
        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=70,
            scale_in_cooldown=Duration.seconds(180),
            scale_out_cooldown=Duration.seconds(60),
        )

        # =====================================================================
        # Application Load Balancer
        # =====================================================================
        # ALB security group
        alb_sg = ec2.SecurityGroup(
            self,
            f"{project_name}AlbSG",
            vpc=vpc,
            description="Security group for Application Load Balancer",
            allow_all_outbound=True,
        )
        alb_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP from anywhere",
        )

        # Allow ALB to reach ECS tasks
        ecs_sg.add_ingress_rule(
            peer=alb_sg,
            connection=ec2.Port.tcp(8000),
            description="Allow ALB to access ECS tasks",
        )

        # Application Load Balancer
        alb = elbv2.ApplicationLoadBalancer(
            self,
            f"{project_name}ALB",
            vpc=vpc,
            internet_facing=True,
            security_group=alb_sg,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        )

        # Target group for ECS service
        target_group = elbv2.ApplicationTargetGroup(
            self,
            f"{project_name}TargetGroup",
            vpc=vpc,
            port=8000,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/api/health",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                healthy_threshold_count=2,
                unhealthy_threshold_count=3,
            ),
            deregistration_delay=Duration.seconds(30),
        )

        # HTTP listener
        listener = alb.add_listener(
            f"{project_name}Listener",
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            default_target_groups=[target_group],
        )

        # Attach ECS service to target group
        backend_service.attach_to_application_target_group(target_group)

        # =====================================================================
        # CloudFront Distribution
        # =====================================================================
        # Origin Access Identity for S3
        oai = cloudfront.OriginAccessIdentity(
            self, f"{project_name}OAI", comment="OAI for GreenGovRAG frontend"
        )
        frontend_bucket.grant_read(oai)

        # CloudFront Function to inject API access key for /api/* requests
        api_auth_function = cloudfront.Function(
            self,
            f"{project_name}ApiAuthFunction",
            comment="Inject X-API-Key header for backend authentication",
            code=cloudfront.FunctionCode.from_inline(f"""
function handler(event) {{
    var request = event.request;
    // Inject API key from CDK context (provided via GitHub Secrets)
    request.headers['x-api-key'] = {{value: '{api_access_key}'}};
    return request;
}}
            """.strip()),
        )

        # CloudFront distribution
        distribution = cloudfront.Distribution(
            self,
            f"{project_name}Distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(frontend_bucket, origin_access_identity=oai),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                compress=True,
            ),
            additional_behaviors={
                "/api/*": cloudfront.BehaviorOptions(
                    origin=origins.HttpOrigin(
                        alb.load_balancer_dns_name,
                        protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
                    ),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    function_associations=[
                        cloudfront.FunctionAssociation(
                            function=api_auth_function,
                            event_type=cloudfront.FunctionEventType.VIEWER_REQUEST,
                        )
                    ],
                )
            },
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_page_path="/index.html",
                    response_http_status=200,
                    ttl=Duration.minutes(5),
                ),
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_page_path="/index.html",
                    response_http_status=200,
                    ttl=Duration.minutes(5),
                ),
            ],
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
            comment=f"{project_name} Frontend Distribution",
        )

        # S3 deployment (optional, can be done via GitHub Actions)
        # s3deploy.BucketDeployment(
        #     self,
        #     f"{project_name}FrontendDeployment",
        #     sources=[s3deploy.Source.asset("../../frontend/dist")],
        #     destination_bucket=frontend_bucket,
        #     distribution=distribution,
        #     distribution_paths=["/*"],
        # )

        # =====================================================================
        # Outputs
        # =====================================================================
        # Essential outputs for GitHub Actions deployment workflow
        CfnOutput(
            self,
            "ClusterName",
            value=cluster.cluster_name,
            description="ECS Cluster Name",
        )

        CfnOutput(
            self,
            "BackendServiceName",
            value=backend_service.service_name,
            description="ECS Backend Service Name",
        )

        CfnOutput(
            self,
            "LoadBalancerDNS",
            value=f"http://{alb.load_balancer_dns_name}",
            description="Application Load Balancer DNS name",
        )

        CfnOutput(
            self,
            "CloudFrontURL",
            value=f"https://{distribution.distribution_domain_name}",
            description="CloudFront distribution URL",
        )

        CfnOutput(
            self,
            "FrontendBucket",
            value=frontend_bucket.bucket_name,
            description="Frontend S3 bucket name",
        )

        CfnOutput(
            self,
            "CloudFrontDistributionId",
            value=distribution.distribution_id,
            description="CloudFront distribution ID",
        )

        CfnOutput(
            self,
            "DocumentsBucket",
            value=docs_bucket.bucket_name,
            description="Documents S3 bucket name",
        )

        CfnOutput(
            self,
            "EcsSecurityGroupId",
            value=ecs_sg.security_group_id,
            description="ECS Security Group ID",
        )

        CfnOutput(
            self,
            "PublicSubnetIds",
            value=",".join([subnet.subnet_id for subnet in vpc.public_subnets]),
            description="Public Subnet IDs (comma-separated)",
        )

        CfnOutput(
            self,
            "QdrantUrl",
            value=f"http://{qdrant_instance.instance_private_ip}:6333",
            description="Qdrant vector database URL (private IP)",
        )

        CfnOutput(
            self,
            "QdrantInstanceId",
            value=qdrant_instance.instance_id,
            description="Qdrant EC2 instance ID",
        )

        # Note: QdrantVolumeId must be discovered dynamically via AWS CLI
        # The volume is created inline with the instance, so we can't reference it directly
        # Use: aws ec2 describe-volumes --filters "Name=attachment.instance-id,Values=<instance-id>"

        CfnOutput(
            self,
            "ApiGatewayURL",
            value=f"http://{alb.load_balancer_dns_name}",
            description="API Gateway URL (ALB endpoint)",
        )

        CfnOutput(
            self,
            "DatabaseEndpoint",
            value=db_instance.db_instance_endpoint_address,
            description="RDS database endpoint",
        )
