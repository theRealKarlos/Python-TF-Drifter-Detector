"""
DynamoDB Resource Fetchers Module.

This module contains functions for fetching DynamoDB-related AWS resources.
"""

from typing import Dict

from src.utils import fetcher_error_handler

from ...utils import setup_logging
from ..types import DynamoDBClient, LiveResourceData, ResourceAttributes

logger = setup_logging()


def fetch_dynamodb_resources(
    dynamodb_client: DynamoDBClient, resource_key: str, attributes: ResourceAttributes
) -> Dict[str, LiveResourceData]:
    """
    Fetch DynamoDB resources from AWS.

    Args:
        dynamodb_client: Boto3 DynamoDB client
        resource_key: Resource key for mapping
        attributes: Resource attributes from Terraform state

    Returns:
        Dictionary mapping resource keys to live AWS resource data
    """
    return _fetch_dynamodb_tables(dynamodb_client, resource_key, attributes)


@fetcher_error_handler
def _fetch_dynamodb_tables(
    dynamodb_client: DynamoDBClient, resource_key: str, attributes: ResourceAttributes
) -> Dict[str, LiveResourceData]:
    """
    Fetch DynamoDB tables from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to table data.
    """
    try:
        response = dynamodb_client.list_tables()
        live_resources = {}
        table_name = attributes.get("name") or attributes.get("id")

        for table_name_from_aws in response["TableNames"]:
            if table_name and table_name_from_aws == table_name:
                table_info = dynamodb_client.describe_table(
                    TableName=table_name_from_aws
                )
                live_resources[resource_key] = table_info["Table"]
                return live_resources

        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        logger.error(f"Error fetching DynamoDB tables: {e}")
        return {}
