"""
S3 Resource Fetchers Module.

This module contains functions for fetching S3-related AWS resources.
"""

from typing import Any, Dict

from src.utils import fetcher_error_handler

from ...utils import setup_logging
from ..types import S3Client

logger = setup_logging()


@fetcher_error_handler
def fetch_s3_resources(s3_client: S3Client, resource_key: str, attributes: Dict) -> Dict[str, Any]:
    """
    Fetch S3 resources from AWS.

    Args:
        s3_client: Boto3 S3 client
        resource_key: Resource key for mapping
        attributes: Resource attributes from Terraform state

    Returns:
        Dictionary mapping resource keys to live AWS resource data
    """
    return _fetch_s3_buckets(s3_client, resource_key, attributes)


def _fetch_s3_buckets(s3_client: S3Client, resource_key: str, attributes: Dict) -> Dict[str, Any]:
    """
    Fetch S3 buckets from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to bucket data.
    """
    try:
        response = s3_client.list_buckets()
        live_resources = {}
        bucket_name = attributes.get("bucket") or attributes.get("id")

        for bucket in response["Buckets"]:
            if bucket_name and bucket["Name"] == bucket_name:
                live_resources[resource_key] = bucket
                return live_resources

        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        logger.error(f"[S3] Error fetching S3 buckets: {e}")
        return {}
