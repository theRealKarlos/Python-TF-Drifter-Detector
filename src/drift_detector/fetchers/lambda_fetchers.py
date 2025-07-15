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


def extract_hybrid_key_from_lambda(function: dict) -> str:
    """
    Extract the best available key for a Lambda function using hybrid logic.
    1. Try ARN
    2. Try function name (ID)
    3. Fallback to 'aws_lambda_function.<name>'
    """
    if "FunctionArn" in function and function["FunctionArn"]:
        return str(function["FunctionArn"])
    if "FunctionName" in function and function["FunctionName"]:
        return str(function["FunctionName"])
    return f"aws_lambda_function.unknown"


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
    Fetch Lambda function resources from AWS and map them by hybrid key for drift comparison.
    Returns a dictionary of hybrid keys to function data for all Lambda functions.
    """
    try:
        response = lambda_client.list_functions()
        live_resources = {}
        
        # Return all Lambda functions keyed by hybrid key
        for function in response["Functions"]:
            key = extract_hybrid_key_from_lambda(function)
            logger.debug(f"[Lambda] Using key for function: {key}")
            live_resources[key] = function

        return live_resources
    except Exception as e:
        logger.error(f"[Lambda] Error fetching Lambda functions: {e}")
        return {}


@fetcher_error_handler
def _fetch_lambda_permissions(
    lambda_client: LambdaClient, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch Lambda permissions from AWS and map them by hybrid key for drift comparison.
    Returns a dictionary of hybrid keys to permission data for all Lambda permissions.
    """
    try:
        function_name = attributes.get("function_name")
        statement_id = attributes.get("statement_id")

        if not function_name or not statement_id:
            # No function name or statement ID specified in state, do not search
            logger.debug(f"[Lambda] No function_name or statement_id in attributes: {attributes}")
            return {}

        # Extract function name from ARN if it's a full ARN
        if function_name.startswith("arn:aws:lambda:"):
            function_name = function_name.split(":")[-1]

        response = lambda_client.get_policy(FunctionName=function_name)
        live_resources = {}

        # Parse the policy document
        policy_doc = json.loads(response["Policy"])

        for statement in policy_doc.get("Statement", []):
            sid = statement.get("Sid")
            key = f"{function_name}:{sid}"
            logger.debug(f"[Lambda] Using key for permission: {key}")
            # Store all relevant attributes for comparison
            live_resources[key] = {
                "Sid": sid,
                "Action": statement.get("Action"),
                "Effect": statement.get("Effect"),
                "Principal": statement.get("Principal"),
                "Resource": statement.get("Resource"),
                "Condition": statement.get("Condition"),
            }
        return live_resources
    except Exception as e:
        logger.error(f"[Lambda] Error fetching Lambda permissions: {e}")
        return {}
