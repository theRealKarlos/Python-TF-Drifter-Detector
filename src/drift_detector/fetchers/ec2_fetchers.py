"""
EC2 Resource Fetchers Module (Router).

This module routes EC2-related resource types to their specific fetchers.
"""

from typing import Dict
from ...utils import setup_logging
from ..types import EC2Client, LiveResourceData, ResourceAttributes
from .ec2_instances_fetcher import fetch_ec2_instance_resources
from .vpc_fetcher import fetch_vpc_resources

logger = setup_logging()

def fetch_ec2_resources(
    ec2_client: EC2Client,
    resource_key: str,
    attributes: ResourceAttributes,
    resource_type: str = "",
) -> Dict[str, LiveResourceData]:
    """
    Route EC2-related resource types to their specific fetchers.
    """
    if resource_type and resource_type.startswith("aws_vpc"):
        return fetch_vpc_resources(ec2_client, resource_key, attributes)
    else:
        return fetch_ec2_instance_resources(ec2_client, resource_key, attributes)
