"""Lambda function for Qdrant EC2 Spot instance auto-recovery.

Triggered by:
1. EC2 Spot Interruption Warning (EventBridge)
2. Manual invocation for testing

Handles:
- Creating EBS snapshot before termination
- Launching replacement spot instance
- Attaching persistent EBS volume
- Updating service discovery
"""

import json
import logging
import os
import time
from typing import Any

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2_client = boto3.client("ec2")
ecs_client = boto3.client("ecs")


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle spot instance interruption and recovery.

    Args:
        event: EventBridge event or manual trigger
        context: Lambda context

    Returns:
        Response with status and recovery details
    """
    logger.info(f"Received event: {json.dumps(event)}")

    # Get environment variables
    instance_id = os.environ["INSTANCE_ID"]
    volume_id = os.environ["VOLUME_ID"]
    subnet_id = os.environ["SUBNET_ID"]
    security_group_id = os.environ["SECURITY_GROUP_ID"]

    try:
        # Step 1: Create snapshot of EBS volume for backup
        logger.info(f"Creating snapshot of volume {volume_id}")
        snapshot_response = ec2_client.create_snapshot(
            VolumeId=volume_id,
            Description=f"Qdrant backup before spot interruption - {time.strftime('%Y-%m-%d %H:%M:%S')}",
            TagSpecifications=[
                {
                    "ResourceType": "snapshot",
                    "Tags": [
                        {"Key": "Name", "Value": "qdrant-spot-recovery-backup"},
                        {"Key": "AutoRecovery", "Value": "true"},
                    ],
                }
            ],
        )
        snapshot_id = snapshot_response["SnapshotId"]
        logger.info(f"Created snapshot: {snapshot_id}")

        # Step 2: Detach volume from current instance (if attached)
        try:
            logger.info(f"Detaching volume {volume_id} from instance {instance_id}")
            ec2_client.detach_volume(
                VolumeId=volume_id,
                InstanceId=instance_id,
                Force=True,
            )

            # Wait for detachment
            waiter = ec2_client.get_waiter("volume_available")
            waiter.wait(VolumeIds=[volume_id], WaiterConfig={"Delay": 5, "MaxAttempts": 60})
            logger.info(f"Volume {volume_id} detached successfully")
        except Exception as e:
            logger.warning(f"Could not detach volume (may already be detached): {e}")

        # Step 3: Launch new spot instance
        logger.info("Launching replacement spot instance")

        # Get latest Amazon Linux 2023 ARM AMI
        ami_response = ec2_client.describe_images(
            Owners=["amazon"],
            Filters=[
                {"Name": "name", "Values": ["al2023-ami-*-arm64"]},
                {"Name": "state", "Values": ["available"]},
            ],
            MaxResults=1,
        )
        ami_id = ami_response["Images"][0]["ImageId"]

        # User data script
        user_data_script = """#!/bin/bash
yum update -y
yum install -y docker
systemctl start docker
systemctl enable docker

# Wait for EBS volume attachment
while [ ! -e /dev/xvdf ]; do sleep 1; done

# Mount EBS volume
mkdir -p /qdrant/storage
mount /dev/xvdf /qdrant/storage

# Run Qdrant container
docker run -d \\
  --name qdrant \\
  --restart unless-stopped \\
  -p 6333:6333 \\
  -p 6334:6334 \\
  -v /qdrant/storage:/qdrant/storage \\
  qdrant/qdrant:latest
"""

        # Launch spot instance
        run_response = ec2_client.run_instances(
            ImageId=ami_id,
            InstanceType="t4g.micro",
            MinCount=1,
            MaxCount=1,
            SubnetId=subnet_id,
            SecurityGroupIds=[security_group_id],
            UserData=user_data_script,
            InstanceMarketOptions={
                "MarketType": "spot",
                "SpotOptions": {
                    "SpotInstanceType": "persistent",
                    "InstanceInterruptionBehavior": "stop",
                },
            },
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": "Name", "Value": "GreenGovRAG-Qdrant"},
                        {"Key": "AutoRecovered", "Value": "true"},
                    ],
                }
            ],
        )

        new_instance_id = run_response["Instances"][0]["InstanceId"]
        logger.info(f"Launched new instance: {new_instance_id}")

        # Step 4: Wait for instance to be running
        logger.info(f"Waiting for instance {new_instance_id} to be running")
        waiter = ec2_client.get_waiter("instance_running")
        waiter.wait(InstanceIds=[new_instance_id], WaiterConfig={"Delay": 10, "MaxAttempts": 30})
        logger.info(f"Instance {new_instance_id} is running")

        # Step 5: Attach EBS volume to new instance
        logger.info(f"Attaching volume {volume_id} to instance {new_instance_id}")
        ec2_client.attach_volume(
            VolumeId=volume_id,
            InstanceId=new_instance_id,
            Device="/dev/xvdf",
        )

        # Wait for attachment
        waiter = ec2_client.get_waiter("volume_in_use")
        waiter.wait(VolumeIds=[volume_id], WaiterConfig={"Delay": 5, "MaxAttempts": 60})
        logger.info(f"Volume {volume_id} attached to {new_instance_id}")

        # Step 6: Update environment variable for new instance ID
        # Note: This requires updating the Lambda environment via CloudFormation
        # For now, log the new instance ID
        logger.info(f"IMPORTANT: Update INSTANCE_ID environment variable to {new_instance_id}")

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Qdrant spot instance recovered successfully",
                    "old_instance_id": instance_id,
                    "new_instance_id": new_instance_id,
                    "volume_id": volume_id,
                    "snapshot_id": snapshot_id,
                }
            ),
        }

    except Exception as e:
        logger.error(f"Error during recovery: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
