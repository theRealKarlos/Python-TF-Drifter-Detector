"""
DynamoDB Resource Fetchers Module.

This module contains functions for fetching DynamoDB-related AWS resources.
"""

from typing import Any, Dict


def fetch_dynamodb_resources(
    dynamodb_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
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


def _fetch_dynamodb_tables(
    dynamodb_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
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
        print(f"Error fetching DynamoDB tables: {e}")
        return {} 