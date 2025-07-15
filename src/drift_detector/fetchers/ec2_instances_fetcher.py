"""
EC2 Instance Resource Fetchers Module.

This module contains functions for fetching EC2 instance-related AWS resources.
"""

from typing import Dict

from ...utils import fetcher_error_handler, setup_logging
from ..types import EC2Client, LiveResourceData, ResourceAttributes

logger = setup_logging()


def extract_hybrid_key_from_attributes(
    attributes: ResourceAttributes,
    resource_type: str,
    resource_name: str,
    instance_idx: int = 0,
) -> str:
    """
    Extract the best available key from resource attributes using hybrid logic.

    This function implements the same key extraction logic as the core drift detection:
    1. Try ARN first (if available)
    2. Try ID second (for resources without ARNs)
    3. Fall back to resource_type.resource_name[_idx]

    Args:
        attributes: Resource attributes from Terraform state
        resource_type: Type of AWS resource
        resource_name: Name of the resource in Terraform
        instance_idx: Index of the resource instance (for multiple instances)

    Returns:
        String key for the resource
    """
    # 1. Try ARN
    for arn_key in ("arn", "Arn", "ARN"):
        if arn_key in attributes and attributes[arn_key]:
            return str(attributes[arn_key])

    # 2. Try ID (for resources without ARNs)
    for id_key in (
        "id",
        "Id",
        "ID",
        "instance_id",
        "InstanceId",
        "resource_id",
        "ResourceId",
    ):
        if id_key in attributes and attributes[id_key]:
            return str(attributes[id_key])

    # 3. Fallback to resource_type.resource_name[_idx]
    return f"{resource_type}.{resource_name}_{instance_idx}"


@fetcher_error_handler
def fetch_ec2_instance_resources(
    ec2_client: EC2Client, resource_key: str, attributes: ResourceAttributes
) -> Dict[str, LiveResourceData]:
    """
    Fetch EC2 instances from AWS and map them by resource key for drift comparison.

    This function uses hybrid key extraction to match resources:
    - If the resource has an ARN, uses ARN-based matching
    - If the resource has an ID but no ARN, uses ID-based matching
    - Falls back to resource name matching if neither is available

    Args:
        ec2_client: Boto3 EC2 client
        resource_key: The key used to identify this resource (from state)
        attributes: Resource attributes from Terraform state

    Returns:
        Dictionary mapping resource keys to instance data
    """
    try:
        response = ec2_client.describe_instances()
        live_resources = {}

        # Debug: Log all instances found in AWS
        all_instances = []
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                all_instances.append(instance.get("InstanceId"))
        logger.info(
            f"[EC2] Found {len(all_instances)} instances in AWS: {all_instances}"
        )

        # Extract the key used for this resource (should match state key)
        # For EC2 instances, we'll use the instance ID if available, otherwise the resource key
        instance_id = attributes.get("id")

        if instance_id:
            logger.info(f"[EC2] Looking for instance ID: {instance_id}")
            # Look for the specific instance by ID
            for reservation in response["Reservations"]:
                for instance in reservation["Instances"]:
                    if instance.get("InstanceId") == instance_id:
                        # Key by the same format as the state (instance ID)
                        live_resources[instance_id] = instance
                        logger.info(
                            f"[EC2] Found EC2 instance {instance_id} in live AWS"
                        )
                        return live_resources

            # If we didn't find the instance, it might not exist in AWS
            logger.warning(f"[EC2] EC2 instance {instance_id} not found in live AWS")
            return live_resources
        else:
            # Fallback: if no instance ID, use the resource key as provided
            # This is less reliable but handles edge cases
            logger.warning(
                f"[EC2] No instance ID found for EC2 resource, using resource key: {resource_key}"
            )
            return live_resources

    except Exception as e:
        logger.error(f"[EC2] Error fetching EC2 instances: {e}")
        return {}
