"""
AWS Resource Fetchers Package.

This package contains service-specific modules for fetching live AWS resources.
Each module handles resources for a specific AWS service (EC2, S3, IAM, etc.).
"""

from .base import get_live_aws_resources

__all__ = [
    "get_live_aws_resources",
]
