"""
VPC Resource Fetchers Module.

This module contains functions for fetching VPC-related AWS resources.
"""

from typing import Dict
from ...utils import fetcher_error_handler, setup_logging
from ..types import EC2Client, LiveResourceData, ResourceAttributes
from .base import extract_arn_from_attributes

logger = setup_logging()

@fetcher_error_handler
def fetch_vpc_resources(
    ec2_client: EC2Client, resource_key: str, attributes: ResourceAttributes
) -> Dict[str, LiveResourceData]:
    """
    Fetch VPCs from AWS and map them by resource key for drift comparison.
    Prioritises ARN-based matching but falls back to VPC ID matching.
    Returns a dictionary of resource keys to VPC data.
    """
    try:
        response = ec2_client.describe_vpcs()
        live_resources = {}
        
        # Try ARN-based matching first
        arn = extract_arn_from_attributes(attributes, "aws_vpc")
        if arn:
            for vpc in response["Vpcs"]:
                vpc_id = vpc.get("VpcId")
                # For VPCs, the ARN format is typically:
                # arn:aws:ec2:region:account:vpc/vpc-id
                if arn.endswith(f"/{vpc_id}"):
                    live_resources[resource_key] = vpc
                    return live_resources
        
        # Fallback to VPC ID matching
        vpc_id = attributes.get("id")
        if vpc_id:
            for vpc in response["Vpcs"]:
                if vpc.get("VpcId") == vpc_id:
                    live_resources[resource_key] = vpc
                    return live_resources
                    
        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        logger.error(f"Error fetching VPCs: {e}")
        return {} 