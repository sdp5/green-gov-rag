"""AWS CDK Stack for GreenGovRAG - Hybrid Architecture.

Cost-optimized deployment with:
- VPC with public subnets only (no NAT Gateway)
- ECS Fargate backend (1 vCPU, 3GB ARM64)
- RDS PostgreSQL t4g.micro with pgvector (30% utilization for 8 hrs/day)
- DynamoDB for caching (replaces ElastiCache)
- EC2 Spot instance (t4g.micro) for Qdrant with auto-recovery
- CloudFront + S3 for frontend (global CDN)
- API Gateway HTTP API (direct integration, no VPC Link)
- GitHub Secrets for LLM API keys (no SSM endpoint needed)
- S3 Gateway Endpoint (free)

Architecture optimizations:
- No NAT Gateway (saves $40-50/mo)
- No VPC Link (saves $20/mo)
- No SSM endpoint (saves $10/mo)
- Spot instances for non-critical workloads (84% discount)
- ARM64/Graviton processors (20% cost reduction)
- Pay-per-request DynamoDB (vs provisioned ElastiCache)
- Direct API Gateway → ECS integration via Cloud Map DNS

Estimated usage: 8 hrs/day for cost optimization
"""

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    Size,
    Tags,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_integrations as apigw_integrations,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_dynamodb as dynamodb,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_rds as rds,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_servicediscovery as servicediscovery,
    aws_ssm as ssm,
)
from constructs import Construct


class GreenGovRAGStack(Stack):
    """Hybrid architecture stack with managed services and spot instances."""

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
        environment = self.node.try_get_context("environment") or "prod"

        # Secrets - Retrieved from context (passed via GitHub Actions or CLI)
        api_access_key = self.node.try_get_context("api_access_key") or "REPLACE_VIA_GITHUB_SECRETS"
        azure_openai_api_key = self.node.try_get_context("azure_openai_api_key") or "REPLACE_VIA_GITHUB_SECRETS"
        azure_openai_endpoint = self.node.try_get_context("azure_openai_endpoint") or "REPLACE_VIA_GITHUB_SECRETS"
        qdrant_api_key = self.node.try_get_context("qdrant_api_key") or "REPLACE_VIA_GITHUB_SECRETS"

        # Configurable settings - Retrieved from context with sensible defaults
        llm_provider = self.node.try_get_context("llm_provider") or "azure"
        llm_model = self.node.try_get_context("llm_model") or "gpt-5-mini"
        azure_openai_deployment = self.node.try_get_context("azure_openai_deployment") or llm_model
        azure_openai_api_version = self.node.try_get_context("azure_openai_api_version") or "2024-12-01-preview"
        embedding_model = self.node.try_get_context("embedding_model") or "BAAI/bge-large-en-v1.5"
        vector_store_type = self.node.try_get_context("vector_store_type") or "qdrant"

        # =====================================================================
        # VPC - Public Subnets Only (No NAT Gateway)
        # =====================================================================
        vpc = ec2.Vpc(
            self,
            f"{project_name}Vpc",
            max_azs=2,
            nat_gateways=0,  # Cost savings: $32-45/month
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
            allow_all_outbound=False,
        )
        qdrant_sg.add_ingress_rule(
            peer=ecs_sg,
            connection=ec2.Port.tcp(6333),
            description="Allow ECS tasks to access Qdrant",
        )

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
            credentials=rds.Credentials.from_generated_secret("postgres"),
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
            security_groups=[ec2.SecurityGroup(
                self,
                f"{project_name}LambdaInitSG",
                vpc=vpc,
                allow_all_outbound=True,
            )],
            environment={
                "DB_SECRET_ARN": db_instance.secret.secret_arn,
                "DB_HOST": db_instance.db_instance_endpoint_address,
            },
        )

        # Grant Lambda access to DB secret
        db_instance.secret.grant_read(pgvector_init_lambda)

        # Allow Lambda to connect to RDS
        rds_sg.add_ingress_rule(
            peer=ec2.Peer.security_group_id(pgvector_init_lambda.connections.security_groups[0].security_group_id),
            connection=ec2.Port.tcp(5432),
            description="Allow Lambda to initialize pgvector",
        )

        # =====================================================================
        # ECR Repository
        # =====================================================================
        backend_repo = ecr.Repository(
            self,
            f"{project_name}BackendRepo",
            repository_name=f"{project_name.lower()}-backend",
            removal_policy=RemovalPolicy.DESTROY,
            lifecycle_rules=[
                ecr.LifecycleRule(max_image_count=5)  # Keep last 5 images
            ],
        )

        # =====================================================================
        # ECS Cluster with Service Discovery
        # =====================================================================
        cluster = ecs.Cluster(
            self,
            f"{project_name}Cluster",
            vpc=vpc,
            container_insights=False,  # Cost optimization
        )

        # Cloud Map namespace for service discovery
        namespace = servicediscovery.PrivateDnsNamespace(
            self,
            f"{project_name}Namespace",
            name="greengovrag.local",
            vpc=vpc,
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
            image=ecs.ContainerImage.from_ecr_repository(backend_repo, "latest"),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="backend",
                log_retention=logs.RetentionDays.ONE_WEEK,
            ),
            environment={
                "DATABASE_URL": f"postgresql://postgres:PASSWORD@{db_instance.db_instance_endpoint_address}:5432/greengovrag",
                "QDRANT_URL": "http://qdrant.greengovrag.local:6333",
                "QDRANT_API_KEY": qdrant_api_key,
                "VECTOR_STORE_TYPE": vector_store_type,
                "EMBEDDING_MODEL": embedding_model,
                "S3_BUCKET": docs_bucket.bucket_name,
                "DYNAMODB_CACHE_TABLE": cache_table.table_name,
                "CLOUD_PROVIDER": "aws",
                "STORAGE_CONTAINER": docs_bucket.bucket_name,
                # LLM Configuration - Supports Azure OpenAI, AWS Bedrock, or OpenAI
                # Azure: AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT
                # AWS Bedrock: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY (use IAM role instead)
                # OpenAI: OPENAI_API_KEY
                "LLM_PROVIDER": llm_provider,
                "LLM_MODEL": llm_model,
                "AZURE_OPENAI_API_VERSION": azure_openai_api_version,
                "AZURE_OPENAI_API_KEY": azure_openai_api_key,
                "AZURE_OPENAI_ENDPOINT": azure_openai_endpoint,
                "AZURE_OPENAI_DEPLOYMENT": azure_openai_deployment,
                # Cache Settings
                "ENABLE_CACHE": "true",
                "ENABLE_REDIS_CACHE": "false",  # Using DynamoDB instead
                "CACHE_TTL": "3600",
                "ENABLE_SEMANTIC_CACHE": "true",
                # API Security - Access key for all API endpoints
                "API_ACCESS_KEY": api_access_key,
            },
            secrets={
                # Database password still uses Secrets Manager (auto-generated by RDS, no extra cost)
                "DATABASE_PASSWORD": ecs.Secret.from_secrets_manager(db_instance.secret, "password"),
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
        )

        # =====================================================================
        # EC2 Spot Instance for Qdrant
        # =====================================================================
        # Qdrant user data script
        qdrant_user_data = ec2.UserData.for_linux()
        qdrant_user_data.add_commands(
            "#!/bin/bash",
            "yum update -y",
            "yum install -y docker",
            "systemctl start docker",
            "systemctl enable docker",
            "",
            "# Wait for EBS volume attachment (done by Lambda)",
            "while [ ! -e /dev/xvdf ]; do sleep 1; done",
            "",
            "# Format and mount EBS volume (if not formatted)",
            "if ! blkid /dev/xvdf; then",
            "  mkfs -t ext4 /dev/xvdf",
            "fi",
            "mkdir -p /qdrant/storage",
            "mount /dev/xvdf /qdrant/storage",
            "",
            "# Add to fstab for auto-mount",
            "echo '/dev/xvdf /qdrant/storage ext4 defaults,nofail 0 2' >> /etc/fstab",
            "",
            "# Run Qdrant container",
            "docker run -d \\",
            "  --name qdrant \\",
            "  --restart unless-stopped \\",
            "  -p 6333:6333 \\",
            "  -p 6334:6334 \\",
            f"  -e QDRANT__SERVICE__API_KEY={qdrant_api_key} \\",
            "  -v /qdrant/storage:/qdrant/storage \\",
            "  qdrant/qdrant:latest",
        )

        # Launch template for spot instance
        qdrant_launch_template = ec2.LaunchTemplate(
            self,
            f"{project_name}QdrantLaunchTemplate",
            instance_type=ec2.InstanceType("t4g.micro"),
            machine_image=ec2.MachineImage.latest_amazon_linux2023(
                cpu_type=ec2.AmazonLinuxCpuType.ARM_64
            ),
            security_group=qdrant_sg,
            user_data=qdrant_user_data,
            role=iam.Role(
                self,
                f"{project_name}QdrantRole",
                assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
                managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
                ],
            ),
            require_imdsv2=True,
        )

        # EBS volume for Qdrant persistence
        qdrant_volume = ec2.Volume(
            self,
            f"{project_name}QdrantVolume",
            availability_zone=vpc.availability_zones[0],
            size=Size.gibibytes(10),
            volume_type=ec2.EbsDeviceVolumeType.GP3,
            encrypted=True,
            removal_policy=RemovalPolicy.SNAPSHOT,
        )

        # Spot instance (created via CloudFormation, managed by auto-recovery Lambda)
        # Note: CDK doesn't have native spot instance construct, using CfnInstance
        qdrant_spot_instance = ec2.CfnInstance(
            self,
            f"{project_name}QdrantSpot",
            image_id=ec2.MachineImage.latest_amazon_linux2023(
                cpu_type=ec2.AmazonLinuxCpuType.ARM_64
            ).get_image(self).image_id,
            instance_type="t4g.micro",
            subnet_id=vpc.public_subnets[0].subnet_id,
            security_group_ids=[qdrant_sg.security_group_id],
            iam_instance_profile=qdrant_launch_template.role.role_name,
            user_data=qdrant_user_data.render(),
            instance_market_options=ec2.CfnInstance.InstanceMarketOptionsProperty(
                market_type="spot",
                spot_options=ec2.CfnInstance.SpotOptionsProperty(
                    spot_instance_type="persistent",
                    instance_interruption_behavior="stop",
                ),
            ),
            tags=[{"key": "Name", "value": f"{project_name}-Qdrant"}],
        )

        # =====================================================================
        # Lambda - Qdrant Spot Instance Recovery
        # =====================================================================
        qdrant_recovery_lambda = lambda_.Function(
            self,
            f"{project_name}QdrantRecovery",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="qdrant_spot_recovery.handler",
            code=lambda_.Code.from_asset("lambda"),
            timeout=Duration.minutes(5),
            environment={
                "INSTANCE_ID": qdrant_spot_instance.ref,
                "VOLUME_ID": qdrant_volume.volume_id,
                "SUBNET_ID": vpc.public_subnets[0].subnet_id,
                "SECURITY_GROUP_ID": qdrant_sg.security_group_id,
            },
        )

        # Grant permissions to manage EC2 instances and volumes
        qdrant_recovery_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "ec2:DescribeInstances",
                    "ec2:RunInstances",
                    "ec2:TerminateInstances",
                    "ec2:AttachVolume",
                    "ec2:DetachVolume",
                    "ec2:CreateSnapshot",
                    "ec2:DescribeVolumes",
                    "ec2:DescribeSnapshots",
                ],
                resources=["*"],
            )
        )

        # EventBridge rule for spot interruption warning
        events.Rule(
            self,
            f"{project_name}SpotInterruptionRule",
            event_pattern=events.EventPattern(
                source=["aws.ec2"],
                detail_type=["EC2 Spot Instance Interruption Warning"],
            ),
            targets=[targets.LambdaFunction(qdrant_recovery_lambda)],
        )

        # =====================================================================
        # API Gateway HTTP API (replaces ALB)
        # =====================================================================
        # HTTP API - Direct integration to ECS public endpoint (no VPC Link needed)
        # ECS tasks have public IPs and are accessible via service discovery
        http_api = apigw.HttpApi(
            self,
            f"{project_name}ApiGateway",
            api_name=f"{project_name}-API",
            cors_preflight=apigw.CorsPreflightOptions(
                allow_origins=["https://greengovrag.sundeep.id.au", "https://greengovrag.au"],
                allow_methods=[apigw.CorsHttpMethod.ANY],
                allow_headers=["*"],
            ),
        )

        # Direct HTTP integration to ECS service via Cloud Map DNS
        # Uses public endpoint - saves VPC Link costs
        backend_integration = apigw_integrations.HttpUrlIntegration(
            f"{project_name}BackendIntegration",
            f"http://backend.greengovrag.local:8000/{{proxy}}",
        )

        http_api.add_routes(
            path="/api/{proxy+}",
            methods=[apigw.HttpMethod.ANY],
            integration=backend_integration,
        )

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
                        f"{http_api.api_id}.execute-api.{self.region}.amazonaws.com"
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
        CfnOutput(
            self,
            "VpcId",
            value=vpc.vpc_id,
            description="VPC ID",
        )

        CfnOutput(
            self,
            "BackendServiceName",
            value=backend_service.service_name,
            description="ECS Backend Service Name",
        )

        CfnOutput(
            self,
            "DatabaseEndpoint",
            value=db_instance.db_instance_endpoint_address,
            description="RDS PostgreSQL endpoint",
        )

        CfnOutput(
            self,
            "DatabaseSecretArn",
            value=db_instance.secret.secret_arn,
            description="RDS credentials secret ARN",
        )

        CfnOutput(
            self,
            "DocumentsBucket",
            value=docs_bucket.bucket_name,
            description="S3 bucket for documents",
        )

        CfnOutput(
            self,
            "FrontendBucket",
            value=frontend_bucket.bucket_name,
            description="S3 bucket for frontend",
        )

        CfnOutput(
            self,
            "CloudFrontURL",
            value=f"https://{distribution.distribution_domain_name}",
            description="CloudFront distribution URL",
        )

        CfnOutput(
            self,
            "ApiGatewayURL",
            value=http_api.url,
            description="API Gateway endpoint URL",
        )

        CfnOutput(
            self,
            "CacheTableName",
            value=cache_table.table_name,
            description="DynamoDB cache table name",
        )

        CfnOutput(
            self,
            "QdrantInstanceId",
            value=qdrant_spot_instance.ref,
            description="Qdrant EC2 spot instance ID",
        )

        CfnOutput(
            self,
            "QdrantVolumeId",
            value=qdrant_volume.volume_id,
            description="Qdrant EBS volume ID",
        )

        CfnOutput(
            self,
            "BackendECRRepository",
            value=backend_repo.repository_uri,
            description="ECR repository for backend images",
        )
