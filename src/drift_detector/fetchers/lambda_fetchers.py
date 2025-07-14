"""
Lambda Resource Fetchers Module.

This module contains functions for fetching Lambda-related AWS resources.
"""

import json
from typing import Any, Dict

from ...utils import fetcher_error_handler, setup_logging
from ..types import LambdaClient
from .base import extract_arn_from_attributes

logger = setup_logging()


@fetcher_error_handler
def fetch_lambda_resources(
    lambda_client: LambdaClient,
    resource_key: str,
    attributes: Dict,
    resource_type: str = "",
) -> Dict[str, Any]:
    """
    Fetch Lambda resources from AWS based on resource type.

    Args:
        lambda_client: Boto3 Lambda client
        resource_key: Resource key for mapping
        attributes: Resource attributes from Terraform state
        resource_type: Type of Lambda resource (optional, for routing)

    Returns:
        Dictionary mapping resource keys to live AWS resource data
    """
    if resource_type and resource_type.startswith("aws_lambda_permission"):
        return _fetch_lambda_permissions(lambda_client, resource_key, attributes)
    else:
        return _fetch_lambda_functions(lambda_client, resource_key, attributes)


@fetcher_error_handler
def _fetch_lambda_functions(
    lambda_client: LambdaClient, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch Lambda function resources from AWS and map them by resource key for drift
    comparison. Uses ARN-based matching exclusively as ARNs are always present
    in Terraform state files for AWS managed resources.
    Returns a dictionary of resource keys to function data.
    """
    try:
        response = lambda_client.list_functions()
        live_resources = {}
        
        # Use ARN-based matching exclusively
        arn = extract_arn_from_attributes(attributes, "aws_lambda_function")
        
        for function in response["Functions"]:
            if function.get("FunctionArn") == arn:
                live_resources[resource_key] = function
                return live_resources

        # If no exact match, return empty dict
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        logger.error(f"[Lambda] Error fetching Lambda functions: {e}")
        return {}


@fetcher_error_handler
def _fetch_lambda_permissions(
    lambda_client: LambdaClient, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch Lambda permissions from AWS and map them by resource key for drift comparison.
    Only searches the specific function given in the Terraform state. If no function_name is
    present, does not search or return any permissions. This strictness avoids false positives.
    Returns a dictionary of resource keys to permission data.
    """
    try:
        function_name = attributes.get("function_name")
        statement_id = attributes.get("statement_id")

        if not function_name:
            # No function name specified in state, do not search (strict, avoids false positives)
            return {}

        # Extract function name from ARN if it's a full ARN
        if function_name.startswith("arn:aws:lambda:"):
            # Extract function name from ARN: arn:aws:lambda:region:account:function:name
            function_name = function_name.split(":")[-1]

        response = lambda_client.get_policy(FunctionName=function_name)
        live_resources = {}

        # Parse the policy document
        policy_doc = json.loads(response["Policy"])

        for statement in policy_doc.get("Statement", []):
            if statement_id and statement.get("Sid") == statement_id:
                live_resources[resource_key] = statement
                return live_resources

        # No match found, return empty dict (no fallback)
        return live_resources
    except Exception as e:
        logger.error(f"[Lambda] Error fetching Lambda permissions: {e}")
        return {}
