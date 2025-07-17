"""
API Gateway Resource Fetchers Module.

This module contains functions for fetching API Gateway-related AWS resources.
"""

from typing import Dict

from ...utils import fetcher_error_handler, setup_logging
from ..types import APIGatewayClient, LiveResourceData, ResourceAttributes

logger = setup_logging()


def extract_hybrid_key_from_apigateway(resource: dict, resource_type: str, resource_id: str = "") -> str:
    """
    Extract the best available key for an API Gateway resource using hybrid logic.
    1. Try ARN
    2. Try ID
    3. Fallback to resource_type.<id>
    """
    # For API Gateway resources, we'll use the ID as the primary key since ARNs are complex
    if resource_id:
        return str(resource_id)

    # Try to extract ID from the resource
    for id_key in (
        "id",
        "Id",
        "ID",
        "restApiId",
        "resourceId",
        "deploymentId",
        "stageName",
    ):
        if id_key in resource and resource[id_key]:
            return str(resource[id_key])

    return f"{resource_type}.unknown"


def extract_arn_for_apigateway(resource: dict, resource_type: str, region: str = "eu-west-2") -> str:
    """
    Construct the ARN for an API Gateway resource if not present.
    """
    # Only supports the resource types in use; extend as needed
    if resource_type == "aws_api_gateway_rest_api":
        api_id = resource.get("id")
        if api_id:
            return f"arn:aws:apigateway:{region}::/restapis/{api_id}"
    elif resource_type == "aws_api_gateway_stage":
        api_id = resource.get("restApiId") or resource.get("rest_api_id")
        stage_name = resource.get("stageName") or resource.get("stage_name")
        if api_id and stage_name:
            return f"arn:aws:apigateway:{region}::/restapis/{api_id}/stages/{stage_name}"
    # For other types, fallback to ID or composite key
    return resource.get("arn") or resource.get("id") or "unknown"


@fetcher_error_handler
def fetch_apigateway_resources(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Dispatch to the correct fetcher for API Gateway resources based on resource_type.
    """
    if "aws_api_gateway_integration" in resource_key:
        return _fetch_apigw_integrations(apigateway_client, resource_key, attributes)
    elif "aws_api_gateway_rest_api" in resource_key:
        return _fetch_apigateway_rest_apis(apigateway_client, resource_key, attributes)
    elif "aws_api_gateway_resource" in resource_key:
        return _fetch_apigateway_resources_internal(apigateway_client, resource_key, attributes)
    elif "aws_api_gateway_method" in resource_key:
        return _fetch_apigateway_methods(apigateway_client, resource_key, attributes)
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
    Fetch API Gateway REST APIs from AWS and map them by ARN-based resource key for drift comparison.
    Constructs ARN keys that match the format used in core.py for consistent resource matching.
    Returns a dictionary of ARN keys to API data.
    """
    try:
        # Extract the REST API ID we're looking for from attributes
        target_api_id = attributes.get("id") or attributes.get("rest_api_id")
        
        if not target_api_id:
            logger.warning(f"No REST API ID found in attributes for {resource_key}")
            return {}

        response = apigateway_client.get_rest_apis()
        live_resources: Dict[str, LiveResourceData] = {}

        # Find the matching REST API and construct proper ARN key
        for api in response.get("items", []):
            api_id = api.get("id")
            if api_id == target_api_id:
                # Construct ARN key that matches core.py logic
                region = "eu-west-2"  # Default region, could be made configurable
                arn_key = f"arn:aws:apigateway:{region}::/restapis/{api_id}"
                logger.debug(f"Using ARN key for REST API: {arn_key}")
                
                live_resources[arn_key] = api
                logger.debug(f"Successfully matched REST API {api_id} with key {arn_key}")
                return live_resources

        logger.debug(f"REST API {target_api_id} not found in AWS response")
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
    Fetch API Gateway resources from AWS and map them by hybrid key for drift comparison.
    Returns a dictionary of hybrid keys to resource data for all API Gateway resources.
    """
    try:
        live_resources: Dict[str, LiveResourceData] = {}

        # Get all REST APIs first
        apis_response = apigateway_client.get_rest_apis()

        for api in apis_response.get("items", []):
            api_id = api.get("id")
            if not api_id:
                continue

            try:
                # Get all resources for this API
                resources_response = apigateway_client.get_resources(restApiId=api_id)
                for resource in resources_response.get("items", []):
                    resource_id = resource.get("id")
                    if resource_id:
                        # Use the resource ID as the key (matches state file format)
                        key = extract_hybrid_key_from_apigateway(resource, "aws_api_gateway_resource", resource_id)
                        logger.debug(f"[API Gateway] Using key for resource: {key}")
                        live_resources[key] = resource
            except Exception as e:
                logger.debug(f"Could not get resources for API {api_id}: {e}")
                continue

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
    Fetch API Gateway methods from AWS and map them by composite key for drift comparison.
    Uses the same key format as core.py: agm-{rest_api_id}-{resource_id}-{http_method}
    Returns a dictionary of composite keys to method data.
    """
    try:
        rest_api_id = attributes.get("rest_api_id")
        resource_id = attributes.get("resource_id")
        http_method = attributes.get("http_method")
        if not rest_api_id or not resource_id or not http_method:
            return {}
        
        response = apigateway_client.get_method(restApiId=rest_api_id, resourceId=resource_id, httpMethod=http_method)
        
        # Use the same composite key format as core.py
        composite_key = f"agm-{rest_api_id}-{resource_id}-{http_method}"
        logger.debug(f"[API Gateway] Using composite key for method: {composite_key}")
        return {composite_key: response}
    except Exception as e:
        logger.error(f"[APIGW] Error fetching API Gateway method: {e}")
        return {}


def _fetch_apigw_integrations(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
    resource_type: str = "",
) -> Dict[str, LiveResourceData]:
    """
    Fetch API Gateway integrations from AWS and map them by composite key for drift comparison.
    Uses the same key format as core.py: agi-{rest_api_id}-{resource_id}-{http_method}
    Returns a dictionary of composite keys to integration data.
    """
    try:
        rest_api_id = attributes.get("rest_api_id")
        resource_id = attributes.get("resource_id")
        http_method = attributes.get("http_method")
        if not rest_api_id or not resource_id or not http_method:
            return {}
        
        response = apigateway_client.get_integration(restApiId=rest_api_id, resourceId=resource_id, httpMethod=http_method)
        
        # Use the same composite key format as core.py
        composite_key = f"agi-{rest_api_id}-{resource_id}-{http_method}"
        logger.debug(f"[API Gateway] Using composite key for integration: {composite_key}")
        return {composite_key: response}
    except Exception as e:
        logger.error(f"[APIGW] Error fetching API Gateway integration: {e}")
        return {}





def _fetch_apigateway_deployments(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch API Gateway deployments from AWS and map them by deployment ID for drift comparison.
    Uses the same key format as core.py: just the deployment ID.
    Returns a dictionary of deployment IDs to deployment data.
    """
    try:
        rest_api_id = attributes.get("rest_api_id")
        deployment_id = attributes.get("id")
        if not rest_api_id or not deployment_id:
            return {}
        
        response = apigateway_client.get_deployment(restApiId=rest_api_id, deploymentId=deployment_id)
        
        # Use the deployment ID as key to match core.py logic
        logger.debug(f"[API Gateway] Using deployment ID as key: {deployment_id}")
        return {deployment_id: response}
    except Exception as e:
        logger.error(f"[APIGW] Error fetching API Gateway deployment: {e}")
        return {}


def _fetch_apigateway_stages(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch API Gateway stages from AWS and map them by ARN for drift comparison.
    Uses the same ARN format as core.py for consistent resource matching.
    Returns a dictionary of ARNs to stage data.
    """
    try:
        rest_api_id = attributes.get("rest_api_id")
        stage_name = attributes.get("stage_name")
        
        if not rest_api_id or not stage_name:
            logger.warning(f"Missing rest_api_id or stage_name in attributes for {resource_key}")
            return {}
            
        response = apigateway_client.get_stage(restApiId=rest_api_id, stageName=stage_name)
        
        # Construct ARN key that matches core.py logic
        arn_key = f"arn:aws:apigateway:eu-west-2::/restapis/{rest_api_id}/stages/{stage_name}"
        logger.debug(f"[API Gateway] Using ARN key for stage: {arn_key}")
        
        return {arn_key: response}
    except Exception as e:
        logger.error(f"Error fetching API Gateway stages: {e}")
        return {}



