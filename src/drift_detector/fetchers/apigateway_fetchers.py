"""
API Gateway Resource Fetchers Module.

This module contains functions for fetching API Gateway-related AWS resources.
"""

from typing import Dict, Any
import re

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
    # Log every call to this fetcher for traceability
    logger.debug(f"[API Gateway] fetch_apigateway_resources CALLED: resource_key={resource_key}, attributes={attributes}")

    # Check for composite keys first (these contain resource type info)
    if resource_key.startswith("apigw_integration:") or resource_key.startswith("agi-"):
        return _fetch_apigw_integrations(apigateway_client, resource_key, attributes)
    elif resource_key.startswith("apigw_method:") or resource_key.startswith("agm-"):
        return _fetch_apigateway_methods(apigateway_client, resource_key, attributes)
    elif resource_key.startswith("apigw_resource:"):
        return _fetch_apigateway_resources_internal(apigateway_client, resource_key, attributes)
    elif resource_key.startswith("apigw_deployment:"):
        return _fetch_apigateway_deployments(apigateway_client, resource_key, attributes)
    elif resource_key.startswith("apigw_stage:"):
        return _fetch_apigateway_stages(apigateway_client, resource_key, attributes)
    elif resource_key.startswith("apigw_rest_api:"):
        return _fetch_apigateway_rest_apis(apigateway_client, resource_key, attributes)
    elif resource_key.startswith("arn:aws:apigateway:") and "/stages/" in resource_key:  # API Gateway Stage ARN
        return _fetch_apigateway_stages(apigateway_client, resource_key, attributes)
    elif (
        resource_key.startswith("arn:aws:apigateway:") and "/restapis/" in resource_key and "/stages/" not in resource_key
    ):  # API Gateway REST API ARN
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


def get_attr(attrs: dict, *keys: str) -> Any:
    """
    Try to get an attribute from a dict using multiple possible keys (snake_case, camelCase, etc).
    """
    for k in keys:
        if k in attrs:
            return attrs[k]
    return None


def _empty_apigw_resource_dict(key: str) -> Dict[str, LiveResourceData]:
    """
    Return a dict with the given key mapped to an empty LiveResourceData (all fields None).
    This satisfies the type checker and mirrors the EventBridge fallback approach.
    """
    return {key: {"id": None, "rest_api_id": None, "resource_id": None, "http_method": None, "stage_name": None}}


def _fetch_apigateway_rest_apis(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    try:
        logger.debug(
            f"[API Gateway] _fetch_apigateway_rest_apis called with resource_key={resource_key}, attributes={attributes}"
        )
        # If the resource_key is an ARN, extract the rest_api_id from it
        target_api_id = get_attr(attributes, "id", "rest_api_id", "restApiId")
        if resource_key.startswith("arn:aws:apigateway:") and "/restapis/" in resource_key:
            m = re.search(r"/restapis/([^/]+)", resource_key)
            if m:
                target_api_id = m.group(1)
        if not target_api_id:
            logger.warning(f"No REST API ID found in attributes or ARN for {resource_key}")
            return {}
        response = apigateway_client.get_rest_apis()
        logger.debug(f"[API Gateway] get_rest_apis AWS response: {response}")
        for api in response.get("items", []):
            api_id = api.get("id")
            if api_id == target_api_id:
                composite_key = f"arn:aws:apigateway:eu-west-2::/restapis/{api_id}"
                legacy_key = api_id
                logger.debug(f"Returning REST API under keys: {composite_key}, {legacy_key}")
                return {composite_key: api, legacy_key: api}
        logger.debug(
            f"REST API {target_api_id} not found in AWS response. Available IDs: "
            f"{[api.get('id') for api in response.get('items', [])]}"
        )
        return {}
    except Exception as e:
        logger.error(f"Error fetching API Gateway REST APIs: {e}")
        return {}


def _fetch_apigateway_resources_internal(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    try:
        logger.debug(
            f"[API Gateway] _fetch_apigateway_resources_internal called with resource_key={resource_key}, "
            f"attributes={attributes}"
        )
        rest_api_id = get_attr(attributes, "rest_api_id", "restApiId") or ""
        target_resource_id = get_attr(attributes, "id", "resource_id", "resourceId") or ""
        legacy_id = get_attr(attributes, "id")
        logger.debug(f"[API Gateway] Normalised rest_api_id={rest_api_id}, target_resource_id={target_resource_id}")
        if not rest_api_id or not target_resource_id:
            composite_key = f"apigw_resource:{rest_api_id}:{target_resource_id}"
            logger.warning(
                f"Missing rest_api_id or resource_id in attributes for {resource_key}, "
                f"returning None resource for {composite_key}"
            )
            return _empty_apigw_resource_dict(composite_key)
        try:
            resources_response = apigateway_client.get_resources(restApiId=rest_api_id)
            logger.debug(f"[API Gateway] get_resources AWS response: {resources_response}")
            for resource in resources_response.get("items", []):
                resource_id = resource.get("id")
                if resource_id == target_resource_id:
                    composite_key = f"apigw_resource:{rest_api_id}:{resource_id}"
                    legacy_key = legacy_id if legacy_id else resource_id
                    logger.debug(f"Returning resource under keys: {composite_key}, {legacy_key}")
                    return {composite_key: resource, legacy_key: resource}
            logger.debug(
                f"[API Gateway] Resource {target_resource_id} not found in API {rest_api_id}. "
                f"Available IDs: {[r.get('id') for r in resources_response.get('items', [])]}"
            )
            composite_key = f"apigw_resource:{rest_api_id}:{target_resource_id}"
            logger.warning(
                f"Resource {target_resource_id} not found, returning None resource for {composite_key}"
            )
            return _empty_apigw_resource_dict(composite_key)
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
    try:
        logger.debug(
            f"[API Gateway] _fetch_apigateway_methods called with resource_key={resource_key}, attributes={attributes}"
        )
        rest_api_id = get_attr(attributes, "rest_api_id", "restApiId") or ""
        resource_id = get_attr(attributes, "resource_id", "resourceId", "id") or ""
        http_method = get_attr(attributes, "http_method", "httpMethod") or ""
        legacy_id = get_attr(attributes, "id")
        if not rest_api_id or not resource_id or not http_method:
            composite_key = f"apigw_method:{rest_api_id}:{resource_id}:{http_method}"
            logger.warning(
                f"Missing required attributes for method {resource_key}, "
                f"returning None resource for {composite_key}"
            )
            return _empty_apigw_resource_dict(composite_key)
        try:
            response = apigateway_client.get_method(restApiId=rest_api_id, resourceId=resource_id, httpMethod=http_method)
            logger.debug(f"[API Gateway] get_method AWS response: {response}")
            composite_key = f"apigw_method:{rest_api_id}:{resource_id}:{http_method}"
            legacy_key = legacy_id if legacy_id else f"agm-{rest_api_id}-{resource_id}-{http_method}"
            logger.debug(f"Returning method under keys: {composite_key}, {legacy_key}")
            return {composite_key: response, legacy_key: response}
        except Exception as e:
            logger.error(f"[APIGW] Error fetching API Gateway method: {e}")
            composite_key = f"apigw_method:{rest_api_id}:{resource_id}:{http_method}"
            logger.warning(
                f"Error fetching method, returning None resource for {composite_key}"
            )
            return _empty_apigw_resource_dict(composite_key)
    except Exception as e:
        logger.error(f"[APIGW] Error in _fetch_apigateway_methods: {e}")
        return {}


def _fetch_apigw_integrations(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
    resource_type: str = "",
) -> Dict[str, LiveResourceData]:
    try:
        logger.debug(
            f"[API Gateway] _fetch_apigw_integrations called with resource_key={resource_key}, attributes={attributes}"
        )
        rest_api_id = get_attr(attributes, "rest_api_id", "restApiId") or ""
        resource_id = get_attr(attributes, "resource_id", "resourceId", "id") or ""
        http_method = get_attr(attributes, "http_method", "httpMethod") or ""
        legacy_id = get_attr(attributes, "id")
        if not rest_api_id or not resource_id or not http_method:
            composite_key = f"apigw_integration:{rest_api_id}:{resource_id}:{http_method}"
            logger.warning(
                f"Missing required attributes for integration {resource_key}, "
                f"returning None resource for {composite_key}"
            )
            return _empty_apigw_resource_dict(composite_key)
        try:
            response = apigateway_client.get_integration(
                restApiId=rest_api_id, resourceId=resource_id, httpMethod=http_method
            )
            logger.debug(f"[API Gateway] get_integration AWS response: {response}")
            composite_key = f"apigw_integration:{rest_api_id}:{resource_id}:{http_method}"
            legacy_key = legacy_id if legacy_id else f"agi-{rest_api_id}-{resource_id}-{http_method}"
            logger.debug(f"Returning integration under keys: {composite_key}, {legacy_key}")
            return {composite_key: response, legacy_key: response}
        except Exception as e:
            logger.error(f"[APIGW] Error fetching API Gateway integration: {e}")
            composite_key = f"apigw_integration:{rest_api_id}:{resource_id}:{http_method}"
            logger.warning(
                f"Error fetching integration, returning None resource for {composite_key}"
            )
            return _empty_apigw_resource_dict(composite_key)
    except Exception as e:
        logger.error(f"[APIGW] Error in _fetch_apigw_integrations: {e}")
        return {}


def _fetch_apigateway_deployments(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    try:
        logger.debug(
            f"[API Gateway] _fetch_apigateway_deployments called with resource_key={resource_key}, attributes={attributes}"
        )
        rest_api_id = get_attr(attributes, "rest_api_id", "restApiId") or ""
        deployment_id = get_attr(attributes, "id", "deployment_id", "deploymentId") or ""
        legacy_id = get_attr(attributes, "id")
        if not rest_api_id or not deployment_id:
            composite_key = f"apigw_deployment:{rest_api_id}:{deployment_id}"
            logger.warning(
                f"Missing rest_api_id or deployment_id in attributes for {resource_key}, "
                f"returning None resource for {composite_key}"
            )
            return _empty_apigw_resource_dict(composite_key)
        try:
            response = apigateway_client.get_deployment(restApiId=rest_api_id, deploymentId=deployment_id)
            logger.debug(f"[API Gateway] get_deployment AWS response: {response}")
            canonical_key = str(f"apigw_deployment:{rest_api_id}:{deployment_id}")
            short_id_key = str(deployment_id)
            legacy_key = legacy_id if legacy_id else deployment_id
            logger.debug(f"[API Gateway] Returning deployment under keys: {canonical_key}, {short_id_key}, {legacy_key}")
            return {canonical_key: response, short_id_key: response, legacy_key: response}
        except Exception as e:
            logger.error(f"[APIGW] Error fetching API Gateway deployment: {e}")
            canonical_key = str(f"apigw_deployment:{rest_api_id}:{deployment_id}")
            logger.warning(
                f"Error fetching deployment, returning None resource for {canonical_key}"
            )
            return _empty_apigw_resource_dict(canonical_key)
    except Exception as e:
        logger.error(f"[APIGW] Error in _fetch_apigateway_deployments: {e}")
        return {}


def _fetch_apigateway_stages(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    try:
        logger.debug(
            f"[API Gateway] _fetch_apigateway_stages called with resource_key={resource_key}, attributes={attributes}"
        )
        # If the resource_key is an ARN, extract rest_api_id and stage_name from it
        rest_api_id = get_attr(attributes, "rest_api_id", "restApiId")
        stage_name = get_attr(attributes, "stage_name", "stageName")
        if resource_key.startswith("arn:aws:apigateway:") and "/restapis/" in resource_key and "/stages/" in resource_key:
            m = re.search(r"/restapis/([^/]+)/stages/([^/]+)", resource_key)
            if m:
                rest_api_id = m.group(1)
                stage_name = m.group(2)
        if not rest_api_id or not stage_name:
            logger.warning(f"No rest_api_id or stage_name found in attributes or ARN for {resource_key}")
            return {}
        try:
            response = apigateway_client.get_stage(restApiId=rest_api_id, stageName=stage_name)
            logger.debug(f"[API Gateway] get_stage AWS response: {response}")
            composite_key = f"arn:aws:apigateway:eu-west-2::/restapis/{rest_api_id}/stages/{stage_name}"
            legacy_key = f"ags-{rest_api_id}-{stage_name}"
            logger.debug(f"Returning stage under keys: {composite_key}, {legacy_key}")
            return {composite_key: response, legacy_key: response}
        except Exception as e:
            logger.error(f"Error fetching API Gateway stages: {e}")
            return {}
    except Exception as e:
        logger.error(f"Error in _fetch_apigateway_stages: {e}")
        return {}


def fetch_apigateway_resource(
    apigateway_client: APIGatewayClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch all resources for a given API Gateway REST API and return a dict keyed by resource id.
    This approach uses the rest_api_id from the state attributes to enumerate all resources,
    then matches by resource id (and optionally by path/path_part as a fallback).
    """
    from ...utils import setup_logging

    logger = setup_logging()

    # Extract the rest_api_id from the state attributes
    rest_api_id = attributes.get("rest_api_id")
    if not rest_api_id:
        logger.warning(
            f"[API Gateway] No rest_api_id found in attributes for resource_key={resource_key}. Cannot fetch resources."
        )
        return {}

    logger.debug(f"[API Gateway] Fetching all resources for rest_api_id={rest_api_id} (resource_key={resource_key})")
    try:
        # List all resources for the given REST API
        paginator = apigateway_client.get_paginator("get_resources")
        page_iterator = paginator.paginate(restApiId=rest_api_id)
        all_resources = []
        for page in page_iterator:
            all_resources.extend(page.get("items", []))
        logger.debug(f"[API Gateway] Found {len(all_resources)} resources for rest_api_id={rest_api_id}")
        # Log all resource ids and paths for debugging
        for res in all_resources:
            logger.debug(
                f"[API Gateway] Resource: id={res.get('id')}, path={res.get('path')}, pathPart={res.get('pathPart')}"
            )
        # Build a dict keyed by resource id
        resource_dict = {res["id"]: res for res in all_resources if "id" in res}
        # Return the main dict (by id) for drift comparison
        return resource_dict
    except Exception as e:
        logger.error(f"[API Gateway] Error fetching resources for rest_api_id={rest_api_id}: {e}")
        return {}
