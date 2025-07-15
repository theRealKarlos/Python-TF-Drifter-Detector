"""
EC2 Resource Fetchers Module (Router).

This module routes EC2-related resource types to their specific fetchers.
"""

from typing import Dict

from ...utils import setup_logging
from ..types import EC2Client, LiveResourceData, ResourceAttributes
from .base import extract_arn_from_attributes
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

    Args:
        ec2_client: Boto3 EC2 client
        resource_key: Resource key for mapping
        attributes: Resource attributes from Terraform state
        resource_type: Type of EC2 resource (optional, for routing)

    Returns:
        Dictionary mapping resource keys to live AWS resource data
    """
    if resource_type and resource_type.startswith("aws_vpc"):
        return fetch_vpc_resources(ec2_client, resource_key, attributes)
    elif resource_type and resource_type.startswith("aws_security_group"):
        return _fetch_security_groups(ec2_client, resource_key, attributes)
    elif resource_type and resource_type.startswith("aws_subnet"):
        return _fetch_subnets(ec2_client, resource_key, attributes)
    elif resource_type and resource_type.startswith("aws_internet_gateway"):
        return _fetch_internet_gateways(ec2_client, resource_key, attributes)
    elif resource_type and resource_type.startswith("aws_route_table"):
        return _fetch_route_tables(ec2_client, resource_key, attributes)
    elif resource_type and resource_type.startswith("aws_route_table_association"):
        return _fetch_route_table_associations(ec2_client, resource_key, attributes)
    else:
        return fetch_ec2_instance_resources(ec2_client, resource_key, attributes)


def _fetch_security_groups(
    ec2_client: EC2Client,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch security groups from AWS and map them by resource key for drift comparison.
    Uses ARN-based matching exclusively as ARNs are always present in Terraform
    state files for AWS managed resources.
    Returns a dictionary of resource keys to security group data.
    """
    try:
        response = ec2_client.describe_security_groups()
        live_resources: Dict[str, LiveResourceData] = {}

        # Use ARN-based matching exclusively
        arn = extract_arn_from_attributes(attributes, "aws_security_group")

        for sg in response.get("SecurityGroups", []):
            sg_id = sg.get("GroupId")
            # For security groups, the ARN format is typically:
            # arn:aws:ec2:region:account:security-group/sg-id
            if sg_id and arn.endswith(f"/{sg_id}"):
                live_resources[resource_key] = sg
                return live_resources

        # If no exact match, return empty dict
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        logger.error(f"Error fetching security groups: {e}")
        return {}


def _fetch_subnets(
    ec2_client: EC2Client,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch subnets from AWS and map them by resource key for drift comparison.
    Uses ARN-based matching exclusively as ARNs are always present in Terraform
    state files for AWS managed resources.
    Returns a dictionary of resource keys to subnet data.
    """
    try:
        response = ec2_client.describe_subnets()
        live_resources: Dict[str, LiveResourceData] = {}

        # Use ARN-based matching exclusively
        arn = extract_arn_from_attributes(attributes, "aws_subnet")

        for subnet in response.get("Subnets", []):
            subnet_id = subnet.get("SubnetId")
            # For subnets, the ARN format is typically:
            # arn:aws:ec2:region:account:subnet/subnet-id
            if subnet_id and arn.endswith(f"/{subnet_id}"):
                live_resources[resource_key] = subnet
                return live_resources

        # If no exact match, return empty dict
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        logger.error(f"Error fetching subnets: {e}")
        return {}


def _fetch_internet_gateways(
    ec2_client: EC2Client,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch internet gateways from AWS and map them by resource key for drift comparison.
    Uses ARN-based matching exclusively as ARNs are always present in Terraform
    state files for AWS managed resources.
    Returns a dictionary of resource keys to internet gateway data.
    """
    try:
        response = ec2_client.describe_internet_gateways()
        live_resources: Dict[str, LiveResourceData] = {}

        # Use ARN-based matching exclusively
        arn = extract_arn_from_attributes(attributes, "aws_internet_gateway")

        for igw in response.get("InternetGateways", []):
            igw_id = igw.get("InternetGatewayId")
            # For internet gateways, the ARN format is typically:
            # arn:aws:ec2:region:account:internet-gateway/igw-id
            if igw_id and arn.endswith(f"/{igw_id}"):
                live_resources[resource_key] = igw
                return live_resources

        # If no exact match, return empty dict
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        logger.error(f"Error fetching internet gateways: {e}")
        return {}


def _fetch_route_tables(
    ec2_client: EC2Client,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch route tables from AWS and map them by resource key for drift comparison.
    Route tables don't have ARNs in the same way as other resources, so we use ID-based matching.
    Returns a dictionary of resource keys to route table data.
    """
    try:
        response = ec2_client.describe_route_tables()
        live_resources: Dict[str, LiveResourceData] = {}

        # Route tables don't have ARNs, so we use ID-based matching
        route_table_id = attributes.get("id") or attributes.get("route_table_id")

        if not route_table_id:
            logger.debug(f"No route table ID found for {resource_key}")
            return live_resources

        for rt in response.get("RouteTables", []):
            if rt.get("RouteTableId") == route_table_id:
                live_resources[resource_key] = rt
                return live_resources

        # If no exact match, return empty dict
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        logger.error(f"Error fetching route tables: {e}")
        return {}


def _fetch_route_table_associations(
    ec2_client: EC2Client,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch route table associations from AWS and map them by resource key for drift comparison.
    Route table associations are relationships between route tables and subnets/gateways,
    so they may not have ARNs in the same way as other resources.
    Returns a dictionary of resource keys to route table association data.
    """
    try:
        live_resources: Dict[str, LiveResourceData] = {}

        # Route table associations may not have ARNs, so we use ID-based matching
        # Get the route table ID and subnet ID
        route_table_id = attributes.get("route_table_id")
        subnet_id = attributes.get("subnet_id")

        if not route_table_id:
            logger.debug(f"No route_table_id found for {resource_key}")
            return live_resources

        # Get route table details
        response = ec2_client.describe_route_tables(RouteTableIds=[route_table_id])

        if response.get("RouteTables"):
            route_table = response["RouteTables"][0]

            # Look for the specific association
            for association in route_table.get("Associations", []):
                if subnet_id and association.get("SubnetId") == subnet_id:
                    live_resources[resource_key] = association
                    return live_resources

                # If no specific subnet, return the first association
                if not subnet_id and association.get("Main") is False:
                    live_resources[resource_key] = association
                    return live_resources

        return live_resources
    except Exception as e:
        logger.error(f"Error fetching route table associations: {e}")
        return {}
