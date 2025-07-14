"""
EC2 Instance Resource Fetchers Module.

This module contains functions for fetching EC2 instance-related AWS resources.
"""

from typing import Dict
from ...utils import fetcher_error_handler, setup_logging
from ..types import EC2Client, LiveResourceData, ResourceAttributes

logger = setup_logging()

@fetcher_error_handler
def fetch_ec2_instance_resources(
    ec2_client: EC2Client, resource_key: str, attributes: ResourceAttributes
) -> Dict[str, LiveResourceData]:
    """
    Fetch EC2 instances from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to instance data.
    """
    try:
        response = ec2_client.describe_instances()
        live_resources = {}
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                # Match by instance ID if available in attributes
                if (
                    attributes.get("id")
                    and instance.get("InstanceId") == attributes["id"]
                ):
                    live_resources[resource_key] = instance
                    return live_resources
        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        logger.error(f"Error fetching EC2 instances: {e}")
        return {} 