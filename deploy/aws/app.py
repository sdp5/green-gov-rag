#!/usr/bin/env python3
"""AWS CDK app entry point for GreenGovRAG deployment.

Usage:
    # Set AWS account and region via environment variables
    export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    export CDK_DEFAULT_REGION=ap-southeast-2

    # Deploy
    cdk deploy

    # Or specify via context
    cdk deploy --context project_name=GreenGovRAG --context environment=prod
"""

import os

import aws_cdk as cdk

from greengovrag_stack import GreenGovRAGStack

app = cdk.App()

# Get account and region from environment or use defaults
account = os.environ.get("CDK_DEFAULT_ACCOUNT")
region = os.environ.get("CDK_DEFAULT_REGION", "ap-southeast-2")

if not account:
    raise ValueError(
        "CDK_DEFAULT_ACCOUNT environment variable must be set. "
        "Run: export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)"
    )

GreenGovRAGStack(
    app,
    "GreenGovRAGStack",
    env=cdk.Environment(account=account, region=region),
    description="GreenGovRAG infrastructure stack - FastAPI backend, React frontend, PostgreSQL with pgvector, Redis cache",
)

app.synth()
