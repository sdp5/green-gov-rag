#!/usr/bin/env python3

import aws_cdk as cdk

from deploy.greengovrag_stack import GreenGovRAGStack

app = cdk.App()
GreenGovRAGStack(
    app, "GreenGovRAGStack",
    env=cdk.Environment(account="YOUR_AWS_ACCOUNT_ID", region="ap-southeast-2")  # Sydney
)
app.synth()
