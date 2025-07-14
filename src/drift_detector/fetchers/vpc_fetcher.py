"""
VPC Resource Fetchers Module.

This module contains functions for fetching VPC-related AWS resources.
"""

from typing import Dict
from ...utils import fetcher_error_handler, setup_logging
from ..types import EC2Client, LiveResourceData, ResourceAttributes

logger = setup_logging()

@fetcher_error_handler
def fetch_vpc_resources(
    ec2_client: EC2Client, resource_key: str, attributes: ResourceAttributes
) -> Dict[str, LiveResourceData]:
    """
    Fetch VPCs from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to VPC data.
    """
    try:
        response = ec2_client.describe_vpcs()
        live_resources = {}
        vpc_id = attributes.get("id")
        for vpc in response["Vpcs"]:
            if vpc_id and vpc["VpcId"] == vpc_id:
                live_resources[resource_key] = vpc
                return live_resources
        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        logger.error(f"Error fetching VPCs: {e}")
        return {} 