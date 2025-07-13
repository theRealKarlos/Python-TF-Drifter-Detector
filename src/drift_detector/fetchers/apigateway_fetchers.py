"""
API Gateway Resource Fetchers Module.

This module contains functions for fetching API Gateway-related AWS resources.
"""

from typing import Any, Dict
from ...utils import setup_logging

logger = setup_logging()


def fetch_apigateway_resources(
    apigateway_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch API Gateway resources from AWS.

    Args:
        apigateway_client: Boto3 API Gateway client
        resource_key: Resource key for mapping
        attributes: Resource attributes from Terraform state

    Returns:
        Dictionary mapping resource keys to live AWS resource data
    """
    return _fetch_api_gateway_apis(apigateway_client, resource_key, attributes)


def _fetch_api_gateway_apis(
    apigateway_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch API Gateway REST APIs from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to API Gateway data.
    """
    try:
        response = apigateway_client.get_rest_apis()
        live_resources = {}
        api_name = attributes.get("name") or attributes.get("id")

        for api in response["items"]:
            if api_name and api["name"] == api_name:
                live_resources[resource_key] = api
                return live_resources

        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        logger.error(f"Error fetching API Gateway REST APIs: {e}")
        return {}
