#!/usr/bin/env python3
import aws_cdk as cdk
from greengovrag.greengovrag_stack import GreenGovRagStack

app = cdk.App()
GreenGovRagStack(app, "GreenGovRagStack")
app.synth()
