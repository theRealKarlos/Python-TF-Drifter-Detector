"""
Type definitions for the Terraform Drift Detector.

This module contains specific type definitions to replace Any types throughout
the codebase, improving type safety and code clarity.
"""

from typing import Dict, List, Union

# AWS Client Types - Using Any for flexibility with boto3 clients
#
# boto3 does not provide static type stubs for service clients, and the methods
# available on each client are dynamically generated at runtime. Using 'Any' here
# allows us to annotate AWS client variables for clarity, while avoiding false
# positives from static type checkers. This is a common and accepted practice in
# Python projects that use boto3.
from typing import Any

# Specific AWS client types
EC2Client = Any
S3Client = Any
RDSClient = Any
DynamoDBClient = Any
LambdaClient = Any
IAMClient = Any
STSClient = Any
EventsClient = Any
ECSClient = Any
APIGatewayClient = Any
CloudWatchClient = Any
SQSClient = Any

# Resource data types
ResourceAttributes = Dict[str, Union[str, int, float, bool, List, Dict, None]]
LiveResourceData = Dict[str, Union[str, int, float, bool, List, Dict, None]]
ResourceData = Dict[str, LiveResourceData]

# Drift detection types
DriftDetail = Dict[str, Union[str, List[str]]]
DriftReport = Dict[str, Union[bool, List[DriftDetail], Dict[str, Union[int, str]]]]

# Terraform state types
TerraformResource = Dict[str, Union[str, List[Dict[str, Union[str, Dict]]]]]
TerraformState = Dict[str, Union[str, List[TerraformResource], Dict]]

# Configuration types
ConfigDict = Dict[str, Union[str, int, float, bool]]
