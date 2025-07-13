"""
AWS Resource Fetchers Package.

This package contains service-specific modules for fetching live AWS resources.
Each module handles resources for a specific AWS service (EC2, S3, IAM, etc.).
"""

from .base import get_live_aws_resources
from .ec2_fetchers import *
from .s3_fetchers import *
from .iam_fetchers import *
from .lambda_fetchers import *
from .events_fetchers import *
from .rds_fetchers import *
from .dynamodb_fetchers import *
from .ecs_fetchers import *
from .apigateway_fetchers import *
from .cloudwatch_fetchers import *
from .data_source_fetchers import *

__all__ = [
    "get_live_aws_resources",
] 