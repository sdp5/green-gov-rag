from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_ecr_assets as ecr_assets,
)
from constructs import Construct

class GreenGovRagStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        vpc = ec2.Vpc(self, "GreenGovVpc", max_azs=2)

        cluster = ecs.Cluster(self, "GreenGovCluster", vpc=vpc)

        db = rds.DatabaseInstance(
            self, "GreenGovRDS",
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_13),
            instance_type=ec2.InstanceType("t3.micro"),
            vpc=vpc,
            multi_az=False,
            allocated_storage=20,
            publicly_accessible=False,
        )

        image = ecr_assets.DockerImageAsset(self, "AppImage", directory="../")

        ecs.FargateService(self, "GreenGovService",
                           cluster=cluster,
                           task_definition=ecs.FargateTaskDefinition(
                               self, "GreenGovTask",
                               memory_limit_mib=512,
                               cpu=256,
                               container_definitions=[
                                   ecs.ContainerDefinitionOptions(
                                       image=ecs.ContainerImage.from_docker_image_asset(image),
                                       environment={"DB_HOST": db.db_instance_endpoint_address}
                                   )
                               ]
                           )
                           )
