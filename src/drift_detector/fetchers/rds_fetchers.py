"""
RDS Resource Fetchers Module.

This module contains functions for fetching RDS-related AWS resources.
"""

from typing import Dict

from ..types import RDSClient, ResourceAttributes, LiveResourceData


def fetch_rds_resources(
    rds_client: RDSClient, resource_key: str, attributes: ResourceAttributes
) -> Dict[str, LiveResourceData]:
    """
    Fetch RDS resources from AWS.

    Args:
        rds_client: Boto3 RDS client
        resource_key: Resource key for mapping
        attributes: Resource attributes from Terraform state

    Returns:
        Dictionary mapping resource keys to live AWS resource data
    """
    return _fetch_rds_instances(rds_client, resource_key, attributes)


def _fetch_rds_instances(
    rds_client: RDSClient, resource_key: str, attributes: ResourceAttributes
) -> Dict[str, LiveResourceData]:
    """
    Fetch RDS database instances from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to database instance data.
    """
    try:
        response = rds_client.describe_db_instances()
        live_resources = {}
        db_identifier = attributes.get("db_instance_identifier") or attributes.get("id")

        for db_instance in response["DBInstances"]:
            if db_identifier and db_instance["DBInstanceIdentifier"] == db_identifier:
                live_resources[resource_key] = db_instance
                return live_resources

        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        print(f"Error fetching RDS instances: {e}")
        return {}
