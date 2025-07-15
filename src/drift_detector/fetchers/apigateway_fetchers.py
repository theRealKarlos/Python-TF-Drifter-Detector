"""
API Gateway Resource Fetchers Module.

This module contains functions for fetching API Gateway-related AWS resources.
"""

from typing import Dict

from ...utils import fetcher_error_handler, setup_logging
from ..types import APIGatewayClient, LiveResourceData, ResourceAttributes

logger = setup_logging()


def extract_hybrid_key_from_apigateway(
    resource: dict, resource_type: str, resource_id: str = ""
) -> str:
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
        return _fetch_apigateway_resources_internal(
            apigateway_client, resource_key, attributes
        )
    elif "aws_api_gateway_method" in resource_key:
        return _fetch_apigateway_methods(apigateway_client, resource_key, attributes)
    elif "aws_api_gateway_deployment" in resource_key:
        return _fetch_apigateway_deployments(
            apigateway_client, resource_key, attributes
        )
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
    Fetch API Gateway REST APIs from AWS and map them by hybrid key for drift comparison.
    Returns a dictionary of hybrid keys to API data for all API Gateway REST APIs.
    """
    try:
        response = apigateway_client.get_rest_apis()
        live_resources: Dict[str, LiveResourceData] = {}

        for api in response.get("items", []):
            api_id = api.get("id")
            if api_id:
                # Use the API ID as the key (matches state file format)
                key = extract_hybrid_key_from_apigateway(
                    api, "aws_api_gateway_rest_api", api_id
                )
                logger.debug(f"[API Gateway] Using key for REST API: {key}")
                live_resources[key] = api

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
                        key = extract_hybrid_key_from_apigateway(
                            resource, "aws_api_gateway_resource", resource_id
                        )
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
    Fetch API Gateway methods from AWS and map them by hybrid key for drift comparison.
    Returns a dictionary of hybrid keys to method data for all API Gateway methods.
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
                    if not resource_id:
                        continue

                    # Get all methods for this resource
                    methods_response = apigateway_client.get_resource_methods(
                        restApiId=api_id, resourceId=resource_id
                    )
                    for method_name in methods_response.get("methods", []):
                        try:
                            method_response = apigateway_client.get_method(
                                restApiId=api_id,
                                resourceId=resource_id,
                                httpMethod=method_name,
                            )
                            # Use the method ID as the key (matches state file format)
                            method_id = f"agm-{api_id}-{resource_id}-{method_name}"
                            key = extract_hybrid_key_from_apigateway(
                                method_response, "aws_api_gateway_method", method_id
                            )
                            logger.debug(f"[API Gateway] Using key for method: {key}")
                            live_resources[key] = method_response
                        except Exception as e:
                            logger.debug(
                                (
                                    f"Could not get method {method_name} for resource "
                                    f"{resource_id}: {e}"
                                )
                            )
                            continue
            except Exception as e:
                logger.debug(f"Could not get resources for API {api_id}: {e}")
                continue

        return live_resources
    except Exception as e:
        logger.error(f"Error fetching API Gateway methods: {e}")
        return {}


def _fetch_apigw_integrations(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
    resource_type: str = ""
) -> Dict[str, LiveResourceData]:
    """
    Fetch API Gateway integrations from AWS and map them by composite key for drift comparison.
    Returns a dictionary of composite keys to integration data for all integrations.
    """
    from src.utils import setup_logging

    logger = setup_logging()
    try:
        rest_api_id = attributes.get("rest_api_id")
        resource_id = attributes.get("resource_id")
        http_method = attributes.get("http_method")
        if not rest_api_id or not resource_id or not http_method:
            return {}
        response = apigateway_client.get_integration(
            restApiId=rest_api_id, resourceId=resource_id, httpMethod=http_method
        )
        composite_key = f"apigw_integration:{rest_api_id}:{resource_id}:{http_method}"
        # Log composite key for integration, ensuring no line exceeds 100 characters
        logger.debug("[APIGW] Using composite key for integration:")
        logger.debug(composite_key)
        return {composite_key: response}
    except Exception as e:
        logger.error(f"[APIGW] Error fetching API Gateway integration: {e}")
        return {}


def _fetch_apigw_methods(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
    resource_type: str = ""
) -> Dict[str, LiveResourceData]:
    """
    Fetch API Gateway methods from AWS and map them by composite key for drift comparison.
    Returns a dictionary of composite keys to method data for all methods.
    """
    from src.utils import setup_logging

    logger = setup_logging()
    try:
        rest_api_id = attributes.get("rest_api_id")
        resource_id = attributes.get("resource_id")
        http_method = attributes.get("http_method")
        if not rest_api_id or not resource_id or not http_method:
            return {}
        response = apigateway_client.get_method(
            restApiId=rest_api_id, resourceId=resource_id, httpMethod=http_method
        )
        composite_key = f"apigw_method:{rest_api_id}:{resource_id}:{http_method}"
        logger.debug(
            (
                f"[APIGW] Using composite key for method: "
                f"{composite_key}"
            )
        )
        return {composite_key: response}
    except Exception as e:
        logger.error(f"[APIGW] Error fetching API Gateway method: {e}")
        return {}


def _fetch_apigw_resources(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
    resource_type: str = ""
) -> Dict[str, LiveResourceData]:
    """
    Fetch API Gateway resources from AWS and map them by composite key for drift comparison.
    Returns a dictionary of composite keys to resource data for all resources.
    """
    from src.utils import setup_logging

    logger = setup_logging()
    try:
        rest_api_id = attributes.get("rest_api_id")
        resource_id = attributes.get("resource_id")
        if not rest_api_id or not resource_id:
            return {}
        response = apigateway_client.get_resource(
            restApiId=rest_api_id, resourceId=resource_id
        )
        composite_key = f"apigw_resource:{rest_api_id}:{resource_id}"
        logger.debug(
            f"[APIGW] Using composite key for resource: {composite_key}"
        )
        return {composite_key: response}
    except Exception as e:
        logger.error(f"[APIGW] Error fetching API Gateway resource: {e}")
        return {}


def _fetch_apigw_rest_apis(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
    resource_type: str = ""
) -> Dict[str, LiveResourceData]:
    """
    Fetch API Gateway REST APIs from AWS and map them by composite key for drift comparison.
    Returns a dictionary of composite keys to REST API data for all REST APIs.
    """
    from src.utils import setup_logging

    logger = setup_logging()
    try:
        rest_api_id = attributes.get("id")
        if not rest_api_id:
            return {}
        response = apigateway_client.get_rest_api(restApiId=rest_api_id)
        composite_key = f"apigw_rest_api:{rest_api_id}"
        logger.debug(
            f"[APIGW] Using composite key for rest_api: {composite_key}"
        )
        return {composite_key: response}
    except Exception as e:
        logger.error(f"[APIGW] Error fetching API Gateway rest_api: {e}")
        return {}


def _fetch_apigateway_deployments(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch API Gateway deployments from AWS and map them by composite key for drift comparison.
    Returns a dictionary of composite keys to deployment data for all deployments.
    """
    try:
        rest_api_id = attributes.get("rest_api_id")
        deployment_id = attributes.get("id")
        if not rest_api_id or not deployment_id:
            return {}
        response = apigateway_client.get_deployment(
            restApiId=rest_api_id, deploymentId=deployment_id
        )
        composite_key = f"apigw_deployment:{rest_api_id}:{deployment_id}"
        logger.debug(
            f"[APIGW] Using composite key for deployment: {composite_key}"
        )
        return {composite_key: response}
    except Exception as e:
        logger.error(f"[APIGW] Error fetching API Gateway deployment: {e}")
        return {}


def _fetch_apigateway_stages(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch API Gateway stages from AWS and map them by hybrid key for drift comparison.
    Returns a dictionary of hybrid keys to stage data.
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
        stage_name = attributes.get("stage_name")
        if stage_name:
            for stage in response.get("item", []):
                if stage.get("stageName") == stage_name:
                    # Use the stage ARN as the key (matches state file format)
                    stage_arn = (
                        f"arn:aws:apigateway:eu-west-2::/restapis/{rest_api_id}/stages/"
                        f"{stage_name}"
                    )
                    key = extract_hybrid_key_from_apigateway(
                        stage, "aws_api_gateway_stage", str(stage_arn)
                    )
                    logger.debug(f"[API Gateway] Using key for stage: {key}")
                    live_resources[key] = stage
                    return live_resources

        return live_resources
    except Exception as e:
        logger.error(f"Error fetching API Gateway stages: {e}")
        return {}


def _fetch_apigw_stages(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
    resource_type: str = ""
) -> Dict[str, LiveResourceData]:
    """
    Fetch API Gateway stages from AWS and map them by composite key for drift comparison.
    Returns a dictionary of composite keys to stage data for all stages.
    """
    from src.utils import setup_logging

    logger = setup_logging()
    try:
        rest_api_id = attributes.get("rest_api_id")
        stage_name = attributes.get("stage_name")
        if not rest_api_id or not stage_name:
            return {}
        response = apigateway_client.get_stage(
            restApiId=rest_api_id, stageName=stage_name
        )
        composite_key = f"apigw_stage:{rest_api_id}:{stage_name}"
        logger.debug("[APIGW] Using composite key for stage:")
        logger.debug(composite_key)
        return {composite_key: response}
    except Exception as e:
        logger.error(f"[APIGW] Error fetching API Gateway stage: {e}")
        return {}
