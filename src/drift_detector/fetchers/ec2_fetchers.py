"""
EC2 Resource Fetchers Module.

This module contains functions for fetching EC2-related AWS resources.
"""

from typing import Dict

from ..types import EC2Client, ResourceAttributes, LiveResourceData
from ...utils import setup_logging

logger = setup_logging()


def fetch_ec2_resources(
    ec2_client: EC2Client,
    resource_key: str,
    attributes: ResourceAttributes,
    resource_type: str = "",
) -> Dict[str, LiveResourceData]:
    """
    Fetch EC2 resources from AWS based on resource type.

    Args:
        ec2_client: Boto3 EC2 client
        resource_key: Resource key for mapping
        attributes: Resource attributes from Terraform state
        resource_type: Type of EC2 resource (optional, for routing)

    Returns:
        Dictionary mapping resource keys to live AWS resource data
    """
    if resource_type and resource_type.startswith("aws_vpc"):
        return _fetch_vpcs(ec2_client, resource_key, attributes)
    else:
        return _fetch_ec2_instances(ec2_client, resource_key, attributes)


def _fetch_ec2_instances(
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


def _fetch_vpcs(
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
