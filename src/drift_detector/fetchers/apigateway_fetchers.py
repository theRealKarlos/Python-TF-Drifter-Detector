"""
API Gateway Resource Fetchers Module.

This module contains functions for fetching API Gateway-related AWS resources.
"""

from typing import Dict

from ...utils import fetcher_error_handler, setup_logging
from ..types import APIGatewayClient, LiveResourceData, ResourceAttributes
from .base import extract_arn_from_attributes

logger = setup_logging()


@fetcher_error_handler
def fetch_apigateway_resources(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch API Gateway resources from AWS based on resource type.

    Args:
        apigateway_client: Boto3 API Gateway client
        resource_key: Resource key for mapping
        attributes: Resource attributes from Terraform state

    Returns:
        Dictionary mapping resource keys to live AWS resource data
    """
    # Extract the resource type from the resource key
    if "aws_api_gateway_rest_api" in resource_key:
        return _fetch_apigateway_rest_apis(apigateway_client, resource_key, attributes)
    elif "aws_api_gateway_resource" in resource_key:
        return _fetch_apigateway_resources_internal(apigateway_client, resource_key, attributes)
    elif "aws_api_gateway_method" in resource_key:
        return _fetch_apigateway_methods(apigateway_client, resource_key, attributes)
    elif "aws_api_gateway_integration" in resource_key:
        return _fetch_apigateway_integrations(apigateway_client, resource_key, attributes)
    elif "aws_api_gateway_deployment" in resource_key:
        return _fetch_apigateway_deployments(apigateway_client, resource_key, attributes)
    elif "aws_api_gateway_stage" in resource_key:
        return _fetch_apigateway_stages(apigateway_client, resource_key, attributes)
    else:
        return {}


def _fetch_apigateway_rest_apis(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch API Gateway REST APIs from AWS and map them by resource key for drift comparison.
    Uses ARN-based matching exclusively as ARNs are always present in Terraform
    state files for AWS managed resources.
    Returns a dictionary of resource keys to API data.
    """
    try:
        response = apigateway_client.get_rest_apis()
        live_resources: Dict[str, LiveResourceData] = {}
        
        # Use ARN-based matching exclusively
        arn = extract_arn_from_attributes(attributes, "aws_api_gateway_rest_api")
        
        for api in response.get("items", []):
            # API Gateway ARN format: arn:aws:apigateway:region::/restapis/api-id
            api_id = api.get("id")
            if api_id and arn.endswith(f"/restapis/{api_id}"):
                live_resources[resource_key] = api
                return live_resources

        # If no exact match, return empty dict
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        logger.error(f"Error fetching API Gateway REST APIs: {e}")
        return {}


def _fetch_apigateway_resources_internal(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch API Gateway resources from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to resource data.
    """
    try:
        live_resources: Dict[str, LiveResourceData] = {}
        
        # Get the REST API ID first
        rest_api_id = attributes.get("rest_api_id")
        if not rest_api_id:
            return live_resources
        
        # Get the resource ID
        resource_id = attributes.get("id")
        if not resource_id:
            return live_resources
        
        try:
            response = apigateway_client.get_resource(
                restApiId=rest_api_id, resourceId=resource_id
            )
            live_resources[resource_key] = response
            return live_resources
        except apigateway_client.exceptions.NotFoundException:
            return live_resources
        
    except Exception as e:
        logger.error(f"Error fetching API Gateway resources: {e}")
        return {}


def _fetch_apigateway_methods(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch API Gateway methods from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to method data.
    """
    try:
        live_resources: Dict[str, LiveResourceData] = {}
        
        # Get the REST API ID and resource ID
        rest_api_id = attributes.get("rest_api_id")
        resource_id = attributes.get("resource_id")
        http_method = attributes.get("http_method")
        
        if not all([rest_api_id, resource_id, http_method]):
            return live_resources
        
        try:
            response = apigateway_client.get_method(
                restApiId=rest_api_id,
                resourceId=resource_id,
                httpMethod=http_method
            )
            live_resources[resource_key] = response
            return live_resources
        except apigateway_client.exceptions.NotFoundException:
            return live_resources
        
    except Exception as e:
        logger.error(f"Error fetching API Gateway methods: {e}")
        return {}


def _fetch_apigateway_integrations(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch API Gateway integrations from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to integration data.
    """
    try:
        live_resources: Dict[str, LiveResourceData] = {}
        
        # Get the REST API ID and resource ID
        rest_api_id = attributes.get("rest_api_id")
        resource_id = attributes.get("resource_id")
        http_method = attributes.get("http_method")
        
        if not all([rest_api_id, resource_id, http_method]):
            return live_resources
        
        try:
            response = apigateway_client.get_integration(
                restApiId=rest_api_id,
                resourceId=resource_id,
                httpMethod=http_method
            )
            live_resources[resource_key] = response
            return live_resources
        except apigateway_client.exceptions.NotFoundException:
            return live_resources
        
    except Exception as e:
        logger.error(f"Error fetching API Gateway integrations: {e}")
        return {}


def _fetch_apigateway_deployments(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch API Gateway deployments from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to deployment data.
    """
    try:
        live_resources: Dict[str, LiveResourceData] = {}
        
        # Get the REST API ID
        rest_api_id = attributes.get("rest_api_id")
        if not rest_api_id:
            return live_resources
        
        # Get deployments for the API
        response = apigateway_client.get_deployments(restApiId=rest_api_id)
        
        # Try to match by deployment ID
        deployment_id = attributes.get("id")
        if deployment_id:
            for deployment in response.get("items", []):
                if deployment.get("id") == deployment_id:
                    live_resources[resource_key] = deployment
                    return live_resources
        
        # If no specific deployment ID, try to match by description or other attributes
        description = attributes.get("description")
        if description:
            for deployment in response.get("items", []):
                if deployment.get("description") == description:
                    live_resources[resource_key] = deployment
                    return live_resources

        return live_resources
    except Exception as e:
        logger.error(f"Error fetching API Gateway deployments: {e}")
        return {}


def _fetch_apigateway_stages(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch API Gateway stages from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to stage data.
    """
    try:
        live_resources: Dict[str, LiveResourceData] = {}
        
        # Get the REST API ID
        rest_api_id = attributes.get("rest_api_id")
        if not rest_api_id:
            return live_resources
        
        # Get stages for the API
        response = apigateway_client.get_stages(restApiId=rest_api_id)
        
        # Try to match by stage name
        stage_name = attributes.get("stage_name") or attributes.get("name")
        if stage_name:
            for stage in response.get("item", []):
                if stage.get("stageName") == stage_name:
                    live_resources[resource_key] = stage
                    return live_resources

        return live_resources
    except Exception as e:
        logger.error(f"Error fetching API Gateway stages: {e}")
        return {}
