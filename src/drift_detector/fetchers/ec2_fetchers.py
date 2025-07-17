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

print("DEBUG: LOADED ec2_fetchers.py")


def fetch_ec2_resources(
    ec2_client: EC2Client,
    resource_key: str,
    attributes: ResourceAttributes,
    resource_type: str = "",
) -> Dict[str, LiveResourceData]:
    print(f"DEBUG: Entered fetch_ec2_resources with resource_type={resource_type}, resource_key={resource_key}")
    if resource_type and resource_type.startswith("aws_vpc"):
        return fetch_vpc_resources(ec2_client, resource_key, attributes)
    elif resource_type and resource_type.startswith("aws_security_group"):
        return _fetch_security_groups(ec2_client, resource_key, attributes)
    elif resource_type and resource_type.startswith("aws_subnet"):
        return _fetch_subnets(ec2_client, resource_key, attributes)
    elif resource_type and resource_type.startswith("aws_internet_gateway"):
        return _fetch_internet_gateways(ec2_client, resource_key, attributes)
    elif resource_type and resource_type.startswith("aws_route_table_association"):
        print(f"DEBUG: About to call _fetch_route_table_associations with key={resource_key}")
        result = _fetch_route_table_associations(ec2_client, resource_key, attributes)
        print(f"DEBUG: _fetch_route_table_associations returned keys: {list(result.keys())}")
        return result
    elif resource_type and resource_type.startswith("aws_route_table"):
        return _fetch_route_tables(ec2_client, resource_key, attributes)
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
    Fetch route tables from AWS and map them by ARN-based resource key for drift comparison.
    Constructs ARN keys that match the format used in core.py for consistent resource matching.
    Returns a dictionary of ARN keys to route table data.
    """
    try:
        import boto3
        
        # Get region and account information for ARN construction
        region = getattr(ec2_client.meta, "region_name", "unknown")
        try:
            sts = boto3.client("sts", region_name=region)
            account_id = sts.get_caller_identity().get("Account", "unknown")
        except Exception as e:
            account_id = f"error: {e}"
            logger.debug(f"Could not get account ID: {e}")

        response = ec2_client.describe_route_tables()
        live_resources: Dict[str, LiveResourceData] = {}

        # Extract the route table ID we're looking for from attributes
        target_route_table_id = attributes.get("id") or attributes.get("route_table_id")

        if not target_route_table_id:
            logger.warning(f"No route table ID found in attributes for {resource_key}")
            return live_resources

        logger.debug(f"Looking for route table ID: {target_route_table_id}")

        # Find the matching route table and construct proper ARN key
        for rt in response.get("RouteTables", []):
            rt_id = rt.get("RouteTableId")
            if rt_id == target_route_table_id:
                # Construct ARN key that matches core.py logic
                if region != "unknown" and account_id != "unknown" and not account_id.startswith("error:"):
                    arn_key = f"arn:aws:ec2:{region}:{account_id}:route-table/{rt_id}"
                    logger.debug(f"Using ARN key for route table: {arn_key}")
                else:
                    # Fallback to route table ID if region/account unavailable
                    arn_key = rt_id
                    logger.debug(f"Using route table ID as key (missing region/account): {arn_key}")
                
                live_resources[arn_key] = rt
                logger.debug(f"Successfully matched route table {rt_id} with key {arn_key}")
                return live_resources

        logger.debug(f"Route table {target_route_table_id} not found in AWS response")
        return live_resources
    except Exception as e:
        logger.error(f"Error fetching route tables: {e}")
        return {}


def _fetch_route_table_associations(
    ec2_client: EC2Client,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    print("DEBUG: DEFINED _fetch_route_table_associations")
    import sys

    print("DEBUG: ec2_fetchers.py __file__:", __file__)
    print("DEBUG: sys.path:", sys.path)
    import traceback
    import boto3

    try:
        print("DEBUG: Entered _fetch_route_table_associations")
        try:
            logger.debug("Entered _fetch_route_table_associations")
        except Exception:
            pass
        live_resources: Dict[str, LiveResourceData] = {}
        region = getattr(ec2_client.meta, "region_name", "unknown")
        try:
            sts = boto3.client("sts", region_name=region)
            account_id = sts.get_caller_identity().get("Account", "unknown")
        except Exception as e:
            account_id = f"error: {e}"
        print(f"DEBUG: Using region: {region}, account: {account_id}")
        try:
            logger.debug(f"DEBUG: Using region: {region}, account: {account_id}")
        except Exception:
            pass
        response = ec2_client.describe_route_tables()
        print(f"DEBUG: Raw describe_route_tables response: {response}")
        try:
            logger.debug(f"DEBUG: Raw describe_route_tables response: {response}")
        except Exception:
            pass
        route_tables = response.get("RouteTables", [])
        print(f"DEBUG: Found {len(route_tables)} route tables in AWS response")
        try:
            logger.debug(f"DEBUG: Found {len(route_tables)} route tables in AWS response")
        except Exception:
            pass
        for rt in route_tables:
            rt_id = rt.get("RouteTableId", "unknown")
            associations = rt.get("Associations", [])
            print(f"DEBUG: RouteTableId: {rt_id}, Associations: {associations}")
            try:
                logger.debug(f"DEBUG: RouteTableId: {rt_id}, Associations: {associations}")
            except Exception:
                pass
            for assoc in associations:
                assoc_id = assoc.get("RouteTableAssociationId")
                if assoc_id:
                    live_resources[assoc_id] = assoc
        print(f"DEBUG: All RouteTableAssociationIds found in AWS: {list(live_resources.keys())}")
        try:
            logger.debug(f"DEBUG: All RouteTableAssociationIds found in AWS: {list(live_resources.keys())}")
        except Exception:
            pass
        if resource_key in live_resources:
            return {resource_key: live_resources[resource_key]}
        return {}
    except Exception as e:
        print(f"ERROR: Exception in _fetch_route_table_associations: {e}")
        traceback.print_exc()
        try:
            logger.error(f"ERROR: Exception in _fetch_route_table_associations: {e}")
            logger.error(traceback.format_exc())
        except Exception:
            pass
        return {}
