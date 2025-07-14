"""
EC2 Instance Resource Fetchers Module.

This module contains functions for fetching EC2 instance-related AWS resources.
"""

from typing import Dict
from ...utils import fetcher_error_handler, setup_logging
from ..types import EC2Client, LiveResourceData, ResourceAttributes
from .base import extract_arn_from_attributes

logger = setup_logging()

@fetcher_error_handler
def fetch_ec2_instance_resources(
    ec2_client: EC2Client, resource_key: str, attributes: ResourceAttributes
) -> Dict[str, LiveResourceData]:
    """
    Fetch EC2 instances from AWS and map them by resource key for drift comparison.
    Prioritises ARN-based matching but falls back to instance ID matching.
    Returns a dictionary of resource keys to instance data.
    """
    try:
        response = ec2_client.describe_instances()
        live_resources = {}
        
        # Try ARN-based matching first
        arn = extract_arn_from_attributes(attributes, "aws_instance")
        if arn:
            for reservation in response["Reservations"]:
                for instance in reservation["Instances"]:
                    instance_id = instance.get("InstanceId")
                    # For EC2 instances, the ARN format is typically:
                    # arn:aws:ec2:region:account:instance/instance-id
                    if arn.endswith(f"/{instance_id}"):
                        live_resources[resource_key] = instance
                        return live_resources
        
        # Fallback to instance ID matching
        instance_id = attributes.get("id")
        if instance_id:
            for reservation in response["Reservations"]:
                for instance in reservation["Instances"]:
                    if instance.get("InstanceId") == instance_id:
                        live_resources[resource_key] = instance
                        return live_resources
                        
        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        logger.error(f"Error fetching EC2 instances: {e}")
        return {} 