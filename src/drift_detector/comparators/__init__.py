"""
AWS Resource Comparators Package.

This package contains service-specific modules for comparing Terraform state resources
with live AWS resources. Each module handles resources for a specific AWS service.
"""

from .base import compare_resources, compare_attributes
from .ec2_comparators import *
from .s3_comparators import *
from .iam_comparators import *
from .lambda_comparators import *
from .events_comparators import *
from .rds_comparators import *
from .dynamodb_comparators import *
from .ecs_comparators import *
from .apigateway_comparators import *
from .cloudwatch_comparators import *

__all__ = [
    "compare_resources",
    "compare_attributes",
] 