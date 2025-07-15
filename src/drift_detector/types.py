"""
Type definitions for the Terraform Drift Detector.

This module contains specific type definitions to replace Any types throughout
the codebase, improving type safety and code clarity.
"""

# AWS Client Types - Using Any for flexibility with boto3 clients
#
# boto3 does not provide static type stubs for service clients, and the methods
# available on each client are dynamically generated at runtime. Using 'Any' here
# allows us to annotate AWS client variables for clarity, while avoiding false
# positives from static type checkers. This is a common and accepted practice in
# Python projects that use boto3.
from typing import Any, Dict, List, Union

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

# Resource data types - More specific than Any
ResourceValue = Union[str, int, float, bool, List, Dict, None]
ResourceAttributes = Dict[str, ResourceValue]
LiveResourceData = Dict[str, ResourceValue]
ResourceData = Dict[str, LiveResourceData]

# Comparator-specific types - More flexible for attribute comparison
ComparatorAttributes = Dict[str, Union[str, int, float, bool, List, Dict, None]]

# Drift detection types - More specific than Any
# Flexible for drift details that can contain various types
DriftDetail = Dict[str, Any]  # Flexible for drift details that can contain various types
DriftReport = Dict[str, Union[bool, List[DriftDetail], Dict[str, Union[int, str]]]]

# Terraform state types
TerraformResource = Dict[str, Union[str, List[Dict[str, Union[str, Dict]]]]]
TerraformState = Dict[str, Union[str, List[TerraformResource], Dict]]

# Configuration types
ConfigDict = Dict[str, Union[str, int, float, bool]]
