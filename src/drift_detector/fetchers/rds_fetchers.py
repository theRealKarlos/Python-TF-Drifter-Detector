"""
RDS Resource Fetchers Module.

This module contains functions for fetching RDS-related AWS resources.
"""

from typing import Dict

from ...utils import fetcher_error_handler, setup_logging
from ..types import LiveResourceData, RDSClient, ResourceAttributes

logger = setup_logging()


@fetcher_error_handler
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
    Fetch RDS database instances from AWS and map them by resource key for drift
    comparison. Returns a dictionary of resource keys to instance data.
    """
    try:
        response = rds_client.describe_db_instances()
        live_resources = {}
        db_instance_id = attributes.get("id")
        for db_instance in response["DBInstances"]:
            if db_instance_id and db_instance["DBInstanceIdentifier"] == db_instance_id:
                live_resources[resource_key] = db_instance
                return live_resources
        return live_resources
    except Exception as e:
        logger.error(f"[RDS] Error fetching RDS instances: {e}")
        return {}
