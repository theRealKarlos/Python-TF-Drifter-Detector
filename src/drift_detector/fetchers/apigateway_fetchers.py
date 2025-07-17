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
    Dispatch to the correct fetcher for API Gateway resources based on resource_key.
    """
    logger.debug(f"[API Gateway] fetch_apigateway_resources called with resource_key={resource_key}")
    
    # Check for composite keys first (these contain resource type info)
    if "agi-" in resource_key:  # API Gateway Integration
        return _fetch_apigw_integrations(apigateway_client, resource_key, attributes)
    elif "agm-" in resource_key:  # API Gateway Method
        return _fetch_apigateway_methods(apigateway_client, resource_key, attributes)
    elif resource_key.startswith("arn:aws:apigateway:") and "/stages/" in resource_key:  # API Gateway Stage ARN
        return _fetch_apigateway_stages(apigateway_client, resource_key, attributes)
    elif resource_key.startswith("arn:aws:apigateway:") and "/restapis/" in resource_key and "/stages/" not in resource_key:  # API Gateway REST API ARN
        return _fetch_apigateway_rest_apis(apigateway_client, resource_key, attributes)
    elif resource_key.isdigit() or len(resource_key) < 20:  # Simple ID (deployment or resource)
        # Check attributes to determine if it's a deployment or resource
        if attributes.get("rest_api_id"):
            return _fetch_apigateway_deployments(apigateway_client, resource_key, attributes)
        else:
            return _fetch_apigateway_resources_internal(apigateway_client, resource_key, attributes)
    else:
        logger.debug(f"[API Gateway] No matching fetcher for resource_key={resource_key}")
        return {}


def get_attr(attrs, *keys):
    """
    Try to get an attribute from a dict using multiple possible keys (snake_case, camelCase, etc).
    """
    for k in keys:
        if k in attrs:
            return attrs[k]
    return None


def _fetch_apigateway_rest_apis(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch API Gateway REST APIs from AWS and map them by ARN-based resource key for drift comparison.
    Uses the resource_key directly since it's already constructed in core.py for consistent resource matching.
    Returns a dictionary of ARN keys to API data.
    """
    try:
        logger.debug(f"[API Gateway] _fetch_apigateway_rest_apis called with resource_key={resource_key}, attributes={attributes}")
        
        # Extract the REST API ID we're looking for from attributes
        target_api_id = get_attr(attributes, "id", "rest_api_id", "restApiId")
        
        if not target_api_id:
            logger.warning(f"No REST API ID found in attributes for {resource_key}")
            return {}

        response = apigateway_client.get_rest_apis()
        logger.debug(f"[API Gateway] get_rest_apis AWS response: {response}")
        live_resources: Dict[str, LiveResourceData] = {}

        # Find the matching REST API
        for api in response.get("items", []):
            api_id = api.get("id")
            if api_id == target_api_id:
                # Use the resource_key directly since it's already constructed in core.py
                # This ensures we're using the exact same key format
                logger.debug(f"Using resource_key for REST API: {resource_key}")
                live_resources[resource_key] = api
                logger.debug(f"Successfully matched REST API {api_id} with key {resource_key}")
                return live_resources

        logger.debug(f"REST API {target_api_id} not found in AWS response. Available IDs: {[api.get('id') for api in response.get('items', [])]}")
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
    Uses the resource_key directly since it's already constructed in core.py for consistent resource matching.
    Returns a dictionary of resource keys to resource data.
    """
    try:
        logger.debug(f"[API Gateway] _fetch_apigateway_resources_internal called with resource_key={resource_key}, attributes={attributes}")
        
        rest_api_id = get_attr(attributes, "rest_api_id", "restApiId")
        target_resource_id = get_attr(attributes, "id", "resource_id", "resourceId")
        
        if not rest_api_id or not target_resource_id:
            logger.warning(f"Missing rest_api_id or resource_id in attributes for {resource_key}")
            return {}

        try:
            # Get all resources for this specific API
            resources_response = apigateway_client.get_resources(restApiId=rest_api_id)
            logger.debug(f"[API Gateway] get_resources AWS response: {resources_response}")
            for resource in resources_response.get("items", []):
                resource_id = resource.get("id")
                if resource_id == target_resource_id:
                    # Use the resource_key directly since it's already constructed in core.py
                    # This ensures we're using the exact same key format
                    logger.debug(f"Using resource_key for resource: {resource_key}")
                    return {resource_key: resource}
            
            logger.debug(f"Resource {target_resource_id} not found in API {rest_api_id}. Available IDs: {[r.get('id') for r in resources_response.get('items', [])]}")
            return {}
        except Exception as e:
            logger.error(f"Could not get resources for API {rest_api_id}: {e}")
            return {}
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
    Uses the resource_key directly since it's already constructed in core.py for consistent resource matching.
    Returns a dictionary of composite keys to method data.
    """
    try:
        logger.debug(f"[API Gateway] _fetch_apigateway_methods called with resource_key={resource_key}, attributes={attributes}")
        
        rest_api_id = get_attr(attributes, "rest_api_id", "restApiId")
        resource_id = get_attr(attributes, "resource_id", "resourceId", "id")
        http_method = get_attr(attributes, "http_method", "httpMethod")
        if not rest_api_id or not resource_id or not http_method:
            logger.warning(f"Missing required attributes for method {resource_key}")
            return {}
        
        try:
            response = apigateway_client.get_method(restApiId=rest_api_id, resourceId=resource_id, httpMethod=http_method)
            logger.debug(f"[API Gateway] get_method AWS response: {response}")
            # Use the resource_key directly since it's already constructed in core.py
            # This ensures we're using the exact same key format
            logger.debug(f"Using resource_key for method: {resource_key}")
            return {resource_key: response}
        except Exception as e:
            logger.error(f"[APIGW] Error fetching API Gateway method: {e}")
            return {}
    except Exception as e:
        logger.error(f"[APIGW] Error in _fetch_apigateway_methods: {e}")
        return {}


def _fetch_apigw_integrations(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
    resource_type: str = "",
) -> Dict[str, LiveResourceData]:
    """
    Fetch API Gateway integrations from AWS and map them by composite key for drift comparison.
    Uses the resource_key directly since it's already constructed in core.py for consistent resource matching.
    Returns a dictionary of composite keys to integration data.
    """
    try:
        logger.debug(f"[API Gateway] _fetch_apigw_integrations called with resource_key={resource_key}, attributes={attributes}")
        
        rest_api_id = get_attr(attributes, "rest_api_id", "restApiId")
        resource_id = get_attr(attributes, "resource_id", "resourceId", "id")
        http_method = get_attr(attributes, "http_method", "httpMethod")
        if not rest_api_id or not resource_id or not http_method:
            logger.warning(f"Missing required attributes for integration {resource_key}")
            return {}
        
        try:
            response = apigateway_client.get_integration(restApiId=rest_api_id, resourceId=resource_id, httpMethod=http_method)
            logger.debug(f"[API Gateway] get_integration AWS response: {response}")
            # Use the resource_key directly since it's already constructed in core.py
            # This ensures we're using the exact same key format
            logger.debug(f"Using resource_key for integration: {resource_key}")
            return {resource_key: response}
        except Exception as e:
            logger.error(f"[APIGW] Error fetching API Gateway integration: {e}")
            return {}
    except Exception as e:
        logger.error(f"[APIGW] Error in _fetch_apigw_integrations: {e}")
        return {}





def _fetch_apigateway_deployments(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch API Gateway deployments from AWS and map them by deployment ID for drift comparison.
    Uses the resource_key directly since it's already constructed in core.py for consistent resource matching.
    Returns a dictionary of deployment IDs to deployment data.
    """
    try:
        logger.debug(f"[API Gateway] _fetch_apigateway_deployments called with resource_key={resource_key}, attributes={attributes}")
        
        rest_api_id = get_attr(attributes, "rest_api_id", "restApiId")
        deployment_id = get_attr(attributes, "id", "deployment_id", "deploymentId")
        if not rest_api_id or not deployment_id:
            logger.warning(f"Missing rest_api_id or deployment_id in attributes for {resource_key}")
            return {}
        
        try:
            response = apigateway_client.get_deployment(restApiId=rest_api_id, deploymentId=deployment_id)
            logger.debug(f"[API Gateway] get_deployment AWS response: {response}")
            # Use the resource_key directly since it's already constructed in core.py
            # This ensures we're using the exact same key format
            logger.debug(f"Using resource_key for deployment: {resource_key}")
            return {resource_key: response}
        except Exception as e:
            logger.error(f"[APIGW] Error fetching API Gateway deployment: {e}")
            return {}
    except Exception as e:
        logger.error(f"[APIGW] Error in _fetch_apigateway_deployments: {e}")
        return {}


def _fetch_apigateway_stages(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch API Gateway stages from AWS and map them by ARN for drift comparison.
    Uses the resource_key directly since it's already constructed in core.py for consistent resource matching.
    Returns a dictionary of ARNs to stage data.
    """
    try:
        logger.debug(f"[API Gateway] _fetch_apigateway_stages called with resource_key={resource_key}, attributes={attributes}")
        rest_api_id = get_attr(attributes, "rest_api_id", "restApiId")
        stage_name = get_attr(attributes, "stage_name", "stageName")
        
        if not rest_api_id or not stage_name:
            logger.warning(f"Missing rest_api_id or stage_name in attributes for {resource_key}")
            return {}
            
        try:
            response = apigateway_client.get_stage(restApiId=rest_api_id, stageName=stage_name)
            logger.debug(f"[API Gateway] get_stage AWS response: {response}")
            # Use the resource_key directly since it's already constructed in core.py
            # This ensures we're using the exact same key format
            logger.debug(f"Using resource_key for stage: {resource_key}")
            
            return {resource_key: response}
        except Exception as e:
            logger.error(f"Error fetching API Gateway stages: {e}")
            return {}
    except Exception as e:
        logger.error(f"Error in _fetch_apigateway_stages: {e}")
        return {}



